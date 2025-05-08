import sqlite3
import os
from datetime import datetime
import shutil
import tempfile
import pandas as pd
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chat_mapping(conn: sqlite3.Connection) -> Dict[int, Dict[str, str]]:
    """Get mapping of chat IDs to their display names and room names"""
    cursor = conn.cursor()
    cursor.execute("SELECT ROWID, room_name, display_name FROM chat")
    result_set = cursor.fetchall()
    return {row[0]: {"room_name": row[1], "display_name": row[2]} for row in result_set}

def setup_raw_db(db_path: str) -> None:
    """Create the raw database with necessary tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        text TEXT,
        timestamp DATETIME,
        is_from_me INTEGER,
        contact_id TEXT,
        has_media INTEGER,
        processed_at DATETIME,
        chat_name TEXT,
        room_name TEXT,
        UNIQUE(message_id)
    )
    """)
    
    # Create processing status table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processing_status (
        last_processed_id INTEGER,
        last_updated DATETIME
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"Set up raw database at {db_path}")

def get_last_processed_id(conn: sqlite3.Connection) -> int:
    """Get the last processed message ID from the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT last_processed_id FROM processing_status ORDER BY last_updated DESC LIMIT 1")
    result = cursor.fetchone()
    
    if result is None:
        return 0
    
    # Handle bytes or integer result
    last_id = result[0]
    if isinstance(last_id, bytes):
        # Convert bytes to integer
        return int.from_bytes(last_id, byteorder='little')
    return last_id

def decode_attributed_body(attributed_body: bytes) -> Optional[str]:
    """Decode the attributed body to extract text content"""
    if attributed_body is None:
        return None
        
    try:
        # Decode the attributed body
        attributed_body = attributed_body.decode('utf-8', errors='replace')
        
        # Handle different formats
        if "NSString" in attributed_body:
            # Extract text between NSString$V" and the next quote
            start = attributed_body.find('NSString$V"') + 11
            end = attributed_body.find('"', start)
            if end > start:
                return attributed_body[start:end]
    except Exception as e:
        logger.warning(f"Error decoding attributed body: {e}")
    
    return None

def extract_new_messages(source_db_path: str, target_db_path: str) -> Optional[int]:
    """
    Extract new messages from chat.db to raw_messages.db
    
    Returns:
        int: Number of new messages processed, or None if there was an error
    """
    # Create temporary copy of source db
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "chat.db")
    
    try:
        logger.info(f"Creating temporary copy of {source_db_path}")
        shutil.copy2(source_db_path, temp_db_path)
        
        # Connect to both databases
        source_conn = sqlite3.connect(temp_db_path)
        target_conn = sqlite3.connect(target_db_path)
        
        # Get last processed ID
        last_processed_id = get_last_processed_id(target_conn)
        logger.info(f"Last processed message ID: {last_processed_id}")
        
        # Get chat mapping
        chat_mapping = get_chat_mapping(source_conn)
        
        # Get new messages
        query = """
        SELECT 
            m.ROWID as message_id,
            cmj.chat_id,
            m.text,
            m.attributedBody,
            datetime(m.date/1000000000 + 978307200, 'unixepoch') as timestamp,
            m.is_from_me,
            h.id as contact_id,
            m.cache_has_attachments as has_media,
            m.cache_roomnames,
            c.room_name as chat_room_name,
            m.is_emote,
            m.is_system_message
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        JOIN chat c ON cmj.chat_id = c.ROWID
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.ROWID > ?
        AND (
            m.text IS NOT NULL 
            OR (m.attributedBody IS NOT NULL AND m.cache_has_attachments = 0)
        )
        AND m.is_system_message = 0
        AND m.is_emote = 0
        ORDER BY m.ROWID
        """
        
        logger.info("Fetching new messages...")
        new_messages = pd.read_sql_query(query, source_conn, params=(last_processed_id,))
        
        if not new_messages.empty:
            # Process messages
            processed_messages = []
            
            for _, msg in new_messages.iterrows():
                # Get text content from either text or attributedBody
                text = msg['text']
                if text is None and msg['attributedBody'] is not None:
                    text = decode_attributed_body(msg['attributedBody'])
                
                # Skip if no text content
                if text is None:
                    continue
                    
                # Skip reaction messages and system notifications
                if text.startswith(('Liked', 'Loved', 'Laughed at', 'Emphasized', 'Disliked', 'Questioned', 'Reacted')):
                    continue
                
                # Get chat information
                chat_info = chat_mapping.get(msg['chat_id'], {})
                chat_name = chat_info.get('display_name')
                room_name = chat_info.get('room_name') or msg['cache_roomnames']
                
                processed_messages.append({
                    'message_id': msg['message_id'],
                    'chat_id': msg['chat_id'],
                    'text': text,
                    'timestamp': msg['timestamp'],
                    'is_from_me': msg['is_from_me'],
                    'contact_id': msg['contact_id'],
                    'has_media': msg['has_media'],
                    'processed_at': datetime.now(),
                    'chat_name': chat_name,
                    'room_name': room_name
                })
            
            if processed_messages:
                # Insert processed messages
                processed_df = pd.DataFrame(processed_messages)
                processed_df.to_sql('messages', target_conn, if_exists='append', index=False)
                
                # Update processing status
                last_id = new_messages['message_id'].max()
                cursor = target_conn.cursor()
                cursor.execute(
                    "INSERT INTO processing_status (last_processed_id, last_updated) VALUES (?, ?)",
                    (last_id, datetime.now())
                )
                target_conn.commit()
                
                logger.info(f"Processed {len(processed_messages)} new messages")
                return len(processed_messages)
            else:
                logger.info("No valid messages to process after filtering")
                return 0
        else:
            logger.info("No new messages to process")
            return 0
            
    except Exception as e:
        logger.error(f"Error processing messages: {e}")
        return None
    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
            source_conn.close()
            target_conn.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main function to run the extraction process"""
    source_db = os.path.expanduser("~/Library/Messages/chat.db")
    target_db = "data/raw/raw_messages.db"
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    
    # Setup database if it doesn't exist
    if not os.path.exists(target_db):
        setup_raw_db(target_db)
    
    # Extract new messages
    num_processed = extract_new_messages(source_db, target_db)
    
    if num_processed is not None:
        logger.info(f"Successfully processed {num_processed} messages")
    else:
        logger.error("Failed to process messages")

if __name__ == "__main__":
    main() 