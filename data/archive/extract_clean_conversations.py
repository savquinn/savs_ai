import os
import sqlite3
import json
import shutil
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from tqdm import tqdm
import re

def extract_clean_conversations(original_db_path: str, project_dir: str) -> None:
    """
    Extract and clean conversations from iMessage chat.db for LLM fine-tuning
    tailored to create a personal chatbot that imitates Savs's style.
    
    Parameters:
    original_db_path (str): Path to the original chat.db SQLite database
    project_dir (str): Root directory of the project
    """
    # Expand the tilde in the path
    original_db_path = os.path.expanduser(original_db_path)
    
    # Setup paths
    raw_dir = os.path.join(project_dir, "data", "raw")
    processed_dir = os.path.join(project_dir, "data", "processed", "fine_tuning")
    
    # Create directories if they don't exist
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    # Copy the database to the raw directory
    raw_db_path = os.path.join(raw_dir, "chat.db")
    print(f"Copying chat.db to {raw_db_path}...")
    
    # Create a temporary copy first
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "chat.db")
    try:
        shutil.copy2(original_db_path, temp_db_path)
        # Then move to our project directory
        shutil.copy2(temp_db_path, raw_db_path)
        print(f"Successfully copied database to raw directory")
    except Exception as e:
        print(f"Error copying database: {e}")
        return
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temporary files: {e}")
    
    print(f"Connecting to copied database at: {raw_db_path}")
    conn = sqlite3.connect(raw_db_path)
    
    # Get conversations with message counts
    print("Fetching conversations...")
    query = """
    SELECT
        c.ROWID as chat_id,
        c.display_name,
        COUNT(cmj.message_id) as message_count
    FROM chat c
    JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
    GROUP BY c.ROWID
    HAVING message_count > 3  -- Minimum messages for a meaningful conversation
    ORDER BY message_count DESC
    """
    
    conversations = pd.read_sql_query(query, conn)
    print(f"Found {len(conversations)} conversations with more than 3 messages")
    
    # Process each conversation
    all_processed_conversations = []
    
    for _, chat in tqdm(conversations.iterrows(), total=len(conversations), desc="Processing conversations"):
        chat_id = chat['chat_id']
        display_name = chat['display_name'] or f"Conversation-{chat_id}"
        
        # Get messages for this conversation
        query = """
        SELECT
            m.ROWID as message_id,
            m.text,
            datetime(m.date/1000000000 + 978307200, 'unixepoch') as timestamp,
            m.is_from_me,
            h.id as contact_id
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE cmj.chat_id = ?
        AND m.text IS NOT NULL 
        AND m.text != ''
        ORDER BY m.date ASC
        """
        
        messages = pd.read_sql_query(query, conn, params=(chat_id,))
        
        # Skip if no messages with text
        if len(messages) == 0:
            continue
        
        # Clean and process messages
        processed_messages = []
        
        for _, msg in messages.iterrows():
            # Skip messages that are just reactions (these start with "Liked" or similar)
            if msg['text'] and re.search(r'^(Liked|Loved|Laughed at|Emphasized|Disliked|Questioned|Reacted)', msg['text']):
                continue
                
            # Skip auto-reply and system messages
            if re.search(r'(emphasized|reacted with)', msg['text'].lower()):
                continue
            
            # Detect if message contains "\ufffc" (indicating embedded media)
            has_media = "\ufffc" in msg['text']
            cleaned_text = msg['text'].replace("\ufffc", "").strip()
            
            # Skip if text is now empty after cleaning
            if not cleaned_text:
                continue
                
            processed_messages.append({
                'role': 'friend' if msg['is_from_me'] == 0 else 'savs',
                'content': cleaned_text,
                'timestamp': msg['timestamp'],
                'contact_id': msg['contact_id'] if msg['is_from_me'] == 0 else 'me',
                'has_media': has_media
            })
        
        # Skip if we don't have enough messages after filtering
        if len(processed_messages) < 5:
            continue
            
        # Create conversation object
        conversation = {
            'id': f"conversation_{chat_id}",
            'title': display_name,
            'messages': processed_messages,
            'message_count': len(processed_messages)
        }
        
        all_processed_conversations.append(conversation)
    
    # Close the database connection
    conn.close()
    
    # Save all conversations to a single file
    with open(os.path.join(processed_dir, 'all_conversations.json'), 'w') as f:
        json.dump(all_processed_conversations, f, indent=2)
    
    # Create fine-tuning dataset in JSONL format
    create_fine_tuning_dataset(all_processed_conversations, processed_dir)
    
    print(f"Processed {len(all_processed_conversations)} conversations")
    print(f"Data saved to: {processed_dir}")

def create_fine_tuning_dataset(conversations: List[Dict[str, Any]], output_dir: str) -> None:
    """
    Create a JSONL fine-tuning dataset from the processed conversations,
    formatted for a personal chatbot that imitates Savs's specific style.
    
    Parameters:
    conversations (List[Dict]): List of processed conversation objects
    output_dir (str): Directory to save the fine-tuning dataset
    """
    # Extract Savs's messaging patterns
    savs_message_count = 0
    savs_emoji_count = 0
    savs_emoji_pattern = re.compile(r'[\U0001F000-\U0001F9FF]|[\u2600-\u26FF]|[\u2700-\u27BF]')
    savs_message_lengths = []
    
    for convo in conversations:
        for msg in convo['messages']:
            if msg['role'] == 'savs':
                savs_message_count += 1
                savs_message_lengths.append(len(msg['content']))
                savs_emoji_count += len(re.findall(savs_emoji_pattern, msg['content']))
    
    # Calculate stats
    avg_message_length = sum(savs_message_lengths) / max(1, len(savs_message_lengths))
    emoji_frequency = savs_emoji_count / max(1, savs_message_count)
    
    print(f"Savs's messaging stats:")
    print(f"  Average message length: {avg_message_length:.1f} characters")
    print(f"  Emoji frequency: {emoji_frequency:.2f} per message")
    
    # Create system prompt based on observed patterns
    system_prompt = f"""You are Savs, responding to messages from friends. 
Reply naturally using Savs's communication style with these characteristics:
- Casual, friendly tone with frequent use of lowercase letters
- Occasional use of emojis (about {emoji_frequency:.2f} per message)
- Brief, concise responses (typically {avg_message_length:.0f} characters)
- Often discusses music, events, and socializing
- Uses "haha" and "lol" to express amusement
- Frequently shares links to music/content
- Sometimes refers to shared experiences
- Responds enthusiastically to plans and music suggestions

Your goal is to sound exactly like Savs would in a text conversation with friends."""

    # Format 1: Full conversations
    full_conversations = []
    
    for convo in conversations:
        # Create a conversation with customized system prompt
        fine_tuning_convo = {
            'id': convo['id'],
            'messages': [
                {
                    'role': 'system',
                    'content': system_prompt
                }
            ] + [{'role': 'user' if msg['role'] == 'friend' else 'assistant', 
                  'content': msg['content']} 
                 for msg in convo['messages']]
        }
        
        full_conversations.append(fine_tuning_convo)
    
    # Format 2: Individual message pairs
    message_pairs = []
    
    for convo in conversations:
        messages = convo['messages']
        # Find sequences of friend->savs exchanges
        for i in range(len(messages) - 1):
            if messages[i]['role'] == 'friend' and messages[i+1]['role'] == 'savs':
                # Determine if we should include context (from previous messages)
                context_window = []
                
                # Check if this is a direct reply or part of an ongoing conversation
                if i >= 2 and messages[i-1]['role'] == 'savs' and messages[i-2]['role'] == 'friend':
                    # Add previous exchange for context
                    context_window = [
                        {
                            'role': 'user',
                            'content': messages[i-2]['content']
                        },
                        {
                            'role': 'assistant',
                            'content': messages[i-1]['content']
                        }
                    ]
                
                message_pair = {
                    'messages': [
                        {
                            'role': 'system',
                            'content': system_prompt
                        }
                    ] + context_window + [
                        {
                            'role': 'user',
                            'content': messages[i]['content']
                        },
                        {
                            'role': 'assistant',
                            'content': messages[i+1]['content']
                        }
                    ]
                }
                message_pairs.append(message_pair)
    
    # Save in JSONL format
    with open(os.path.join(output_dir, 'full_conversations.jsonl'), 'w') as f:
        for convo in full_conversations:
            f.write(json.dumps(convo) + '\n')
            
    with open(os.path.join(output_dir, 'message_pairs.jsonl'), 'w') as f:
        for pair in message_pairs:
            f.write(json.dumps(pair) + '\n')
    
    # Save system prompt separately for easy editing
    with open(os.path.join(output_dir, 'system_prompt.txt'), 'w') as f:
        f.write(system_prompt)
        
    # Save sample system prompts variants for experimentation
    system_prompt_variants = [
        # Variant 1: More emphasis on music sharing
        system_prompt + "\n\nYou're particularly enthusiastic about sharing music, especially electronic and dance tracks, and often reply with links to songs or playlists.",
        
        # Variant 2: More emphasis on casual style
        system_prompt + "\n\nYour texts are very casual - you often use abbreviations, lowercase everything, and don't worry about perfect grammar or punctuation.",
        
        # Variant 3: More emphasis on conversational rhythm
        system_prompt + "\n\nYou tend to ask follow-up questions about your friends' experiences and maintain an engaging back-and-forth conversation."
    ]
    
    with open(os.path.join(output_dir, 'system_prompt_variants.txt'), 'w') as f:
        for i, variant in enumerate(system_prompt_variants, 1):
            f.write(f"=== VARIANT {i} ===\n{variant}\n\n")
    
    print(f"Created {len(full_conversations)} full conversations for fine-tuning")
    print(f"Created {len(message_pairs)} individual message pairs for fine-tuning")
    print(f"Saved system prompt and variants for easy customization")

if __name__ == "__main__":
    # Update this path to your chat.db location
    original_db_path = "~/Library/Messages/chat.db"
    
    # Get the project root directory - this assumes the script is in data/scripts/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    
    extract_clean_conversations(original_db_path, project_dir)