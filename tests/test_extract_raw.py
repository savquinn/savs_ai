import unittest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime
import pandas as pd
from data.scripts.extract_raw import (
    get_chat_mapping,
    setup_raw_db,
    get_last_processed_id,
    decode_attributed_body,
    extract_new_messages
)

class TestExtractRaw(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test databases
        self.test_dir = tempfile.mkdtemp()
        self.source_db = os.path.join(self.test_dir, "source.db")
        self.target_db = os.path.join(self.test_dir, "target.db")
        
        # Create test source database
        self.create_test_source_db()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_source_db(self):
        """Create a test source database with sample data"""
        conn = sqlite3.connect(self.source_db)
        cursor = conn.cursor()
        
        # Create necessary tables
        cursor.execute("""
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY,
            guid TEXT UNIQUE NOT NULL,
            room_name TEXT,
            display_name TEXT,
            chat_identifier TEXT,
            service_name TEXT,
            is_archived INTEGER DEFAULT 0
        )
        """)
        
        cursor.execute("""
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY,
            guid TEXT UNIQUE NOT NULL,
            text TEXT,
            replace INTEGER DEFAULT 0,
            service_center TEXT,
            handle_id INTEGER DEFAULT 0,
            subject TEXT,
            country TEXT,
            attributedBody BLOB,
            version INTEGER DEFAULT 0,
            type INTEGER DEFAULT 0,
            service TEXT,
            account TEXT,
            account_guid TEXT,
            error INTEGER DEFAULT 0,
            date INTEGER,
            date_read INTEGER,
            date_delivered INTEGER,
            is_delivered INTEGER DEFAULT 0,
            is_finished INTEGER DEFAULT 0,
            is_emote INTEGER DEFAULT 0,
            is_from_me INTEGER DEFAULT 0,
            is_empty INTEGER DEFAULT 0,
            is_delayed INTEGER DEFAULT 0,
            is_auto_reply INTEGER DEFAULT 0,
            is_prepared INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            is_system_message INTEGER DEFAULT 0,
            is_sent INTEGER DEFAULT 0,
            has_dd_results INTEGER DEFAULT 0,
            is_service_message INTEGER DEFAULT 0,
            is_forward INTEGER DEFAULT 0,
            was_downgraded INTEGER DEFAULT 0,
            is_archive INTEGER DEFAULT 0,
            cache_has_attachments INTEGER DEFAULT 0,
            cache_roomnames TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY,
            id TEXT NOT NULL,
            country TEXT,
            service TEXT NOT NULL,
            uncanonicalized_id TEXT,
            person_centric_id TEXT,
            UNIQUE(id, service)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE chat_message_join (
            chat_id INTEGER,
            message_id INTEGER
        )
        """)
        
        # Insert test data
        # Add chats
        cursor.execute(
            "INSERT INTO chat (ROWID, guid, room_name, display_name, chat_identifier, service_name) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "chat1", "Test Room", "Test Chat", "+1234567890", "iMessage")
        )
        cursor.execute(
            "INSERT INTO chat (ROWID, guid, room_name, display_name, chat_identifier, service_name) VALUES (?, ?, ?, ?, ?, ?)",
            (2, "chat2", "Group Room", "Group Chat", "group.chat", "iMessage")
        )
        
        # Add handles
        cursor.execute(
            "INSERT INTO handle (ROWID, id, service) VALUES (?, ?, ?)",
            (1, "+1234567890", "iMessage")
        )
        cursor.execute(
            "INSERT INTO handle (ROWID, id, service) VALUES (?, ?, ?)",
            (2, "+9876543210", "iMessage")
        )
        
        # Add messages with proper attributedBody format
        test_messages = [
            # Regular message - should be included
            (1, "msg1", "Hello", None, 978307200000000000, 0, 1, 0, "Test Room", "iMessage", "user@example.com", 0, 0),
            
            # Attributed body message - should be included
            (2, "msg2", None, b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\x08ZNSString$V"Test Message"', 978307200000000000, 1, 1, 0, "Test Room", "iMessage", "user@example.com", 0, 0),
            
            # Reaction message - should be excluded
            (3, "msg3", "Liked a message", None, 978307200000000000, 0, 1, 0, "Test Room", "iMessage", "user@example.com", 1, 0),
            
            # Media message with attributed body - should be excluded
            (4, "msg4", None, b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\x08ZNSString$V"Media only message"', 978307200000000000, 0, 1, 1, "Test Room", "iMessage", "user@example.com", 0, 0),
            
            # Media only message - should be excluded
            (5, "msg5", None, None, 978307200000000000, 0, 1, 1, "Test Room", "iMessage", "user@example.com", 0, 0),
            
            # Group message - should be included
            (6, "msg6", "Group message", None, 978307200000000000, 0, 2, 0, "Group Room", "iMessage", "user@example.com", 0, 0),
            
            # Group attributed message - should be excluded
            (7, "msg7", None, b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\x08ZNSString$V"Group attributed message"', 978307200000000000, 0, 2, 0, "Group Room", "iMessage", "user@example.com", 0, 1)
        ]
        
        for msg in test_messages:
            cursor.execute(
                """INSERT INTO message (
                    ROWID, guid, text, attributedBody, date, is_from_me, 
                    handle_id, cache_has_attachments, cache_roomnames, service, 
                    account, is_emote, is_system_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                msg
            )
        
        # Link messages to chats
        for msg_id in range(1, 6):  # First 5 messages to Test Chat
            cursor.execute(
                "INSERT INTO chat_message_join (chat_id, message_id) VALUES (?, ?)",
                (1, msg_id)
            )
        
        for msg_id in range(6, 8):  # Last 2 messages to Group Chat
            cursor.execute(
                "INSERT INTO chat_message_join (chat_id, message_id) VALUES (?, ?)",
                (2, msg_id)
            )
        
        conn.commit()
        conn.close()
    
    def test_get_chat_mapping(self):
        """Test chat mapping function"""
        conn = sqlite3.connect(self.source_db)
        mapping = get_chat_mapping(conn)
        conn.close()
        
        self.assertEqual(len(mapping), 2)
        self.assertEqual(mapping[1]["room_name"], "Test Room")
        self.assertEqual(mapping[1]["display_name"], "Test Chat")
        self.assertEqual(mapping[2]["room_name"], "Group Room")
        self.assertEqual(mapping[2]["display_name"], "Group Chat")
    
    def test_setup_raw_db(self):
        """Test database setup"""
        setup_raw_db(self.target_db)
        
        conn = sqlite3.connect(self.target_db)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        self.assertIn("messages", tables)
        self.assertIn("processing_status", tables)
        
        # Check messages table schema
        cursor.execute("PRAGMA table_info(messages)")
        columns = {row[1] for row in cursor.fetchall()}
        
        expected_columns = {
            "message_id", "chat_id", "text", "timestamp", "is_from_me",
            "contact_id", "has_media", "processed_at", "chat_name", "room_name"
        }
        self.assertEqual(columns, expected_columns)
        
        conn.close()
    
    def test_get_last_processed_id(self):
        """Test getting last processed ID"""
        # Setup target database
        setup_raw_db(self.target_db)
        
        conn = sqlite3.connect(self.target_db)
        cursor = conn.cursor()
        
        # Insert test processing status
        cursor.execute(
            "INSERT INTO processing_status (last_processed_id, last_updated) VALUES (?, ?)",
            (100, datetime.now())
        )
        conn.commit()
        
        last_id = get_last_processed_id(conn)
        self.assertEqual(last_id, 100)
        
        conn.close()
    
    def test_decode_attributed_body(self):
        """Test attributed body decoding"""
        # Test valid attributed body
        test_body = b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\x08ZNSString$V"Test Message"'
        result = decode_attributed_body(test_body)
        self.assertEqual(result, "Test Message")
        
        # Test None input
        self.assertIsNone(decode_attributed_body(None))
        
        # Test invalid input
        self.assertIsNone(decode_attributed_body(b"Invalid"))
    
    def test_extract_new_messages(self):
        """Test message extraction"""
        # Setup target database
        setup_raw_db(self.target_db)
        
        # Extract messages
        num_processed = extract_new_messages(self.source_db, self.target_db)
        
        # Check results
        self.assertEqual(num_processed, 3)  # Should process 3 valid messages (excluding reaction and media-only)
        
        # Verify extracted data
        conn = sqlite3.connect(self.target_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 3)
        
        # Check message content and types
        cursor.execute("""
            SELECT text, chat_name, room_name, has_media, is_from_me 
            FROM messages 
            ORDER BY message_id
        """)
        messages = cursor.fetchall()
        
        # Regular message
        self.assertEqual(messages[0][0], "Hello")
        self.assertEqual(messages[0][1], "Test Chat")
        self.assertEqual(messages[0][2], "Test Room")
        self.assertEqual(messages[0][3], 0)  # has_media
        self.assertEqual(messages[0][4], 0)  # is_from_me
        
        # Attributed body message
        self.assertEqual(messages[1][0], "Test Message")
        self.assertEqual(messages[1][1], "Test Chat")
        self.assertEqual(messages[1][2], "Test Room")
        self.assertEqual(messages[1][3], 0)  # has_media
        self.assertEqual(messages[1][4], 1)  # is_from_me
        
        # Group message
        self.assertEqual(messages[2][0], "Group message")
        self.assertEqual(messages[2][1], "Group Chat")
        self.assertEqual(messages[2][2], "Group Room")
        self.assertEqual(messages[2][3], 0)  # has_media
        self.assertEqual(messages[2][4], 0)  # is_from_me
        
        conn.close()
    
    def test_incremental_extraction(self):
        """Test incremental message extraction"""
        # Setup target database
        setup_raw_db(self.target_db)
        
        # First extraction
        num_processed = extract_new_messages(self.source_db, self.target_db)
        self.assertEqual(num_processed, 3)  # Should process 3 valid messages
        
        # Second extraction (should process no new messages)
        num_processed = extract_new_messages(self.source_db, self.target_db)
        self.assertEqual(num_processed, 0)
        
        # Add new message to source
        conn = sqlite3.connect(self.source_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO message (ROWID, guid, text, date, is_from_me, cache_has_attachments, cache_roomnames, handle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (8, "msg8", "New message", 978307200000000000, 0, 0, "Test Room", 1)
        )
        cursor.execute(
            "INSERT INTO chat_message_join (chat_id, message_id) VALUES (?, ?)",
            (1, 8)
        )
        conn.commit()
        conn.close()
        
        # Third extraction (should process one new message)
        num_processed = extract_new_messages(self.source_db, self.target_db)
        self.assertEqual(num_processed, 1)

if __name__ == '__main__':
    unittest.main() 