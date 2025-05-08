import sqlite3
import os
import json
import random
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_conversations(cleaned_db_path: str) -> List[Dict[str, Any]]:
    """Get all conversations from the cleaned database"""
    conn = sqlite3.connect(cleaned_db_path)
    
    # Get all messages ordered by conversation and timestamp
    query = """
    SELECT *
    FROM cleaned_messages
    ORDER BY conversation_id, message_index
    """
    
    messages = pd.read_sql_query(query, conn)
    conn.close()
    
    # Group into conversations
    conversations = []
    current_convo = None
    
    for _, msg in messages.iterrows():
        if current_convo is None or msg['conversation_id'] != current_convo['id']:
            if current_convo is not None:
                conversations.append(current_convo)
            current_convo = {
                'id': msg['conversation_id'],
                'messages': []
            }
        
        current_convo['messages'].append({
            'role': 'assistant' if msg['is_from_me'] == 1 else 'user',
            'content': msg['text']
        })
    
    if current_convo is not None:
        conversations.append(current_convo)
    
    return conversations

def create_training_examples(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create training examples from conversations"""
    examples = []
    
    for convo in conversations:
        # Skip conversations with too few messages
        if len(convo['messages']) < 3:
            continue
            
        # Create system prompt
        system_prompt = {
            'role': 'system',
            'content': """You are Savs, responding to messages from friends. 
Reply naturally using Savs's communication style with these characteristics:
- Casual, friendly tone with frequent use of lowercase letters
- Brief, concise responses
- Often discusses music, events, and socializing
- Uses "haha" and "lol" to express amusement
- Frequently shares links to music/content
- Sometimes refers to shared experiences
- Responds enthusiastically to plans and music suggestions

Your goal is to sound exactly like Savs would in a text conversation with friends."""
        }
        
        # Add system prompt to conversation
        convo['messages'].insert(0, system_prompt)
        
        examples.append(convo)
    
    return examples

def split_train_val(examples: List[Dict[str, Any]], val_ratio: float = 0.1) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split examples into training and validation sets"""
    random.shuffle(examples)
    split_idx = int(len(examples) * (1 - val_ratio))
    return examples[:split_idx], examples[split_idx:]

def save_jsonl(data: List[Dict[str, Any]], filepath: str) -> None:
    """Save data to a JSONL file"""
    with open(filepath, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def prepare_training_data(cleaned_db_path: str, output_dir: str) -> None:
    """Prepare training and validation datasets"""
    try:
        # Get conversations
        logger.info("Getting conversations from cleaned database...")
        conversations = get_conversations(cleaned_db_path)
        logger.info(f"Found {len(conversations)} conversations")
        
        # Create training examples
        logger.info("Creating training examples...")
        examples = create_training_examples(conversations)
        logger.info(f"Created {len(examples)} training examples")
        
        # Split into train/val
        logger.info("Splitting into train/validation sets...")
        train_examples, val_examples = split_train_val(examples)
        logger.info(f"Split into {len(train_examples)} training and {len(val_examples)} validation examples")
        
        # Save to files
        os.makedirs(output_dir, exist_ok=True)
        
        train_path = os.path.join(output_dir, 'train.jsonl')
        val_path = os.path.join(output_dir, 'validation.jsonl')
        
        logger.info(f"Saving training data to {train_path}")
        save_jsonl(train_examples, train_path)
        
        logger.info(f"Saving validation data to {val_path}")
        save_jsonl(val_examples, val_path)
        
        # Save metadata
        metadata = {
            'created_at': datetime.now().isoformat(),
            'num_conversations': len(conversations),
            'num_training_examples': len(train_examples),
            'num_validation_examples': len(val_examples)
        }
        
        metadata_path = os.path.join(output_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("Successfully prepared training data")
        
    except Exception as e:
        logger.error(f"Error preparing training data: {e}")

def main():
    """Main function to run the training data preparation"""
    cleaned_db = "data/processed/cleaned_messages.db"
    output_dir = "data/training"
    
    prepare_training_data(cleaned_db, output_dir)

if __name__ == "__main__":
    main() 