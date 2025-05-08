import sqlite3
import os
from datetime import datetime
import pandas as pd
import re
from typing import Optional, List, Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_cleaned_db(db_path: str) -> None:
    """Create the cleaned database with necessary tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create cleaned messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cleaned_messages (
        message_id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        text TEXT,
        timestamp DATETIME,
        is_from_me INTEGER,
        contact_id TEXT,
        has_media INTEGER,
        cleaned_at DATETIME,
        conversation_id TEXT,
        message_index INTEGER,
        FOREIGN KEY (message_id) REFERENCES messages(message_id)
    )
    """)
    
    # Create cleaning status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cleaning_status (
        last_cleaned_id INTEGER,
        last_updated DATETIME
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Set up cleaned database at {db_path}")

def get_last_cleaned_id(conn: sqlite3.Connection) -> int:
    """Get the last cleaned message ID from the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT last_cleaned_id FROM cleaning_status ORDER BY last_updated DESC LIMIT 1")
    result = cursor.fetchone()
    return result[0] if result else 0

def clean_text(text: str) -> str:
    """Clean the message text"""
    if not text:
        return ""
    
    # Remove reaction messages
    if re.search(r'^(Liked|Loved|Laughed at|Emphasized|Disliked|Questioned|Reacted)', text):
        return ""
    
    # Remove system messages
    if re.search(r'(emphasized|reacted with)', text.lower()):
        return ""
    
    # Remove media placeholders
    text = text.replace("\ufffc", "").strip()
    
    return text

def group_conversations(messages: pd.DataFrame) -> List[Dict[str, Any]]:
    """Group messages into conversations"""
    conversations = []
    current_convo = None
    
    for _, msg in messages.iterrows():
        if current_convo is None or msg['chat_id'] != current_convo['chat_id']:
            if current_convo is not None:
                conversations.append(current_convo)
            current_convo = {
                'chat_id': msg['chat_id'],
                'messages': []
            }
        
        current_convo['messages'].append(msg)
    
    if current_convo is not None:
        conversations.append(current_convo)
    
    return conversations

def clean_messages(raw_db_path: str, cleaned_db_path: str) -> Optional[int]:
    """
    Clean messages from raw database and store in cleaned database
    
    Returns:
        int: Number of messages cleaned, or None if there was an error
    """
    try:
        # Connect to both databases
        raw_conn = sqlite3.connect(raw_db_path)
        cleaned_conn = sqlite3.connect(cleaned_db_path)
        
        # Get last cleaned ID
        last_cleaned_id = get_last_cleaned_id(cleaned_conn)
        logger.info(f"Last cleaned message ID: {last_cleaned_id}")
        
        # Get new messages
        query = """
        SELECT *
        FROM messages
        WHERE message_id > ?
        ORDER BY chat_id, timestamp
        """
        
        logger.info("Fetching new messages to clean...")
        new_messages = pd.read_sql_query(query, raw_conn, params=(last_cleaned_id,))
        
        if not new_messages.empty:
            # Clean messages
            new_messages['text'] = new_messages['text'].apply(clean_text)
            new_messages = new_messages[new_messages['text'] != ""]
            
            # Group into conversations
            conversations = group_conversations(new_messages)
            
            # Process each conversation
            cleaned_messages = []
            for convo in conversations:
                for i, msg in enumerate(convo['messages']):
                    cleaned_messages.append({
                        'message_id': msg['message_id'],
                        'chat_id': msg['chat_id'],
                        'text': msg['text'],
                        'timestamp': msg['timestamp'],
                        'is_from_me': msg['is_from_me'],
                        'contact_id': msg['contact_id'],
                        'has_media': msg['has_media'],
                        'cleaned_at': datetime.now(),
                        'conversation_id': f"convo_{msg['chat_id']}",
                        'message_index': i
                    })
            
            # Insert cleaned messages
            if cleaned_messages:
                cleaned_df = pd.DataFrame(cleaned_messages)
                cleaned_df.to_sql('cleaned_messages', cleaned_conn, if_exists='append', index=False)
                
                # Update cleaning status
                last_id = new_messages['message_id'].max()
                cursor = cleaned_conn.cursor()
                cursor.execute(
                    "INSERT INTO cleaning_status (last_cleaned_id, last_updated) VALUES (?, ?)",
                    (last_id, datetime.now())
                )
                cleaned_conn.commit()
                
                logger.info(f"Cleaned {len(cleaned_messages)} messages")
                return len(cleaned_messages)
            else:
                logger.info("No messages to clean after filtering")
                return 0
        else:
            logger.info("No new messages to clean")
            return 0
            
    except Exception as e:
        logger.error(f"Error cleaning messages: {e}")
        return None
    finally:
        raw_conn.close()
        cleaned_conn.close()

def main():
    """Main function to run the cleaning process"""
    raw_db = "data/raw/raw_messages.db"
    cleaned_db = "data/processed/cleaned_messages.db"
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(cleaned_db), exist_ok=True)
    
    # Setup database if it doesn't exist
    if not os.path.exists(cleaned_db):
        setup_cleaned_db(cleaned_db)
    
    # Clean messages
    num_cleaned = clean_messages(raw_db, cleaned_db)
    
    if num_cleaned is not None:
        logger.info(f"Successfully cleaned {num_cleaned} messages")
    else:
        logger.error("Failed to clean messages")

if __name__ == "__main__":
    main() 