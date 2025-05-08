import unittest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime
import pandas as pd
from data.scripts.clean_data import (
    setup_cleaned_db,
    get_last_cleaned_id,
    clean_text,
    group_conversations,
    clean_messages
)

class TestCleanData(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test databases
        self.test_dir = tempfile.mkdtemp()
        self.raw_db = os.path.join(self.test_dir, "raw.db")
        self.cleaned_db = os.path.join(self.test_dir, "cleaned.db")
        
        # Create test raw database
        self.create_test_raw_db()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_test_raw_db(self):
        """Create a test raw database with sample data"""
        conn = sqlite3.connect(self.raw_db)
        cursor = conn.cursor()
        
        # Create messages table
        cursor.execute("""
        CREATE TABLE messages (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            text TEXT,
            timestamp DATETIME,
            is_from_me INTEGER,
            contact_id TEXT,
            has_media INTEGER,
            processed_at DATETIME,
            chat_name TEXT,
            room_name TEXT
        )
        """)
        
        # Create processing status table
        cursor.execute("""
        CREATE TABLE processing_status (
            last_processed_id INTEGER,
            last_updated DATETIME
        )
        """)
        
        # Insert test messages
        test_messages = [
            # Regular conversation with user messages
            (1, 1, "Hello", "2024-01-01 12:00:00", 0, "+1234567890", 0, datetime.now(), "Test Chat", "Test Room"),
            (2, 1, "Liked a message", "2024-01-01 12:01:00", 1, "me", 0, datetime.now(), "Test Chat", "Test Room"),
            (3, 1, "How are you?", "2024-01-01 12:02:00", 0, "+1234567890", 0, datetime.now(), "Test Chat", "Test Room"),
            (4, 1, "I'm good!", "2024-01-01 12:03:00", 1, "me", 0, datetime.now(), "Test Chat", "Test Room"),
            
            # Media-only messages
            (5, 2, None, "2024-01-01 12:04:00", 0, "+9876543210", 1, datetime.now(), "Media Chat", "Media Room"),
            (6, 2, None, "2024-01-01 12:05:00", 1, "me", 1, datetime.now(), "Media Chat", "Media Room"),
            
            # Conversation without user messages
            (7, 3, "First message", "2024-01-01 12:06:00", 0, "+1111111111", 0, datetime.now(), "No User Chat", "No User Room"),
            (8, 3, "Second message", "2024-01-01 12:07:00", 0, "+2222222222", 0, datetime.now(), "No User Chat", "No User Room"),
            (9, 3, "Third message", "2024-01-01 12:08:00", 0, "+3333333333", 0, datetime.now(), "No User Chat", "No User Room"),
        ]
        
        for msg in test_messages:
            cursor.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                msg
            )
        
        conn.commit()
        conn.close()
    
    def test_setup_cleaned_db(self):
        """Test cleaned database setup"""
        setup_cleaned_db(self.cleaned_db)
        
        conn = sqlite3.connect(self.cleaned_db)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        self.assertIn("cleaned_messages", tables)
        self.assertIn("cleaning_status", tables)
        
        # Check cleaned_messages table schema
        cursor.execute("PRAGMA table_info(cleaned_messages)")
        columns = {row[1] for row in cursor.fetchall()}
        
        expected_columns = {
            "message_id", "chat_id", "text", "timestamp", "is_from_me",
            "contact_id", "has_media", "cleaned_at", "conversation_id", "message_index"
        }
        self.assertEqual(columns, expected_columns)
        
        conn.close()
    
    def test_get_last_cleaned_id(self):
        """Test getting last cleaned ID"""
        setup_cleaned_db(self.cleaned_db)
        conn = sqlite3.connect(self.cleaned_db)
        cursor = conn.cursor()
        
        # Insert test cleaning status
        cursor.execute(
            "INSERT INTO cleaning_status (last_cleaned_id, last_updated) VALUES (?, ?)",
            (100, datetime.now())
        )
        conn.commit()
        
        last_id = get_last_cleaned_id(conn)
        self.assertEqual(last_id, 100)
        
        conn.close()
    
    def test_clean_text(self):
        """Test text cleaning function"""
        # Test regular message
        self.assertEqual(clean_text("Hello"), "Hello")
        
        # Test reaction message
        self.assertEqual(clean_text("Liked a message"), "")
        
        # Test system message
        self.assertEqual(clean_text("emphasized a message"), "")
        
        # Test media placeholder
        self.assertEqual(clean_text("Hello\ufffc"), "Hello")
        
        # Test empty message
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")
    
    def test_group_conversations(self):
        """Test conversation grouping"""
        # Create test messages DataFrame
        messages = pd.DataFrame([
            {"chat_id": 1, "text": "Hello", "timestamp": "2024-01-01 12:00:00"},
            {"chat_id": 1, "text": "Hi", "timestamp": "2024-01-01 12:01:00"},
            {"chat_id": 2, "text": "New chat", "timestamp": "2024-01-01 12:02:00"},
        ])
        
        conversations = group_conversations(messages)
        
        self.assertEqual(len(conversations), 2)
        self.assertEqual(len(conversations[0]["messages"]), 2)
        self.assertEqual(len(conversations[1]["messages"]), 1)
    
    def test_clean_messages(self):
        """Test message cleaning process"""
        # Setup cleaned database
        setup_cleaned_db(self.cleaned_db)
        
        # Clean messages
        num_cleaned = clean_messages(self.raw_db, self.cleaned_db)
        
        # Check results
        self.assertEqual(num_cleaned, 6)  # Should clean 6 valid messages (excluding reactions)
        
        # Verify cleaned data
        conn = sqlite3.connect(self.cleaned_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM cleaned_messages")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 6)
        
        # Check conversation grouping and content
        cursor.execute("""
            SELECT conversation_id, COUNT(*) as msg_count, 
                   SUM(CASE WHEN is_from_me = 1 THEN 1 ELSE 0 END) as user_msg_count,
                   SUM(CASE WHEN has_media = 1 THEN 1 ELSE 0 END) as media_count
            FROM cleaned_messages 
            GROUP BY conversation_id
            ORDER BY conversation_id
        """)
        conv_stats = cursor.fetchall()
        
        # First conversation (regular chat)
        self.assertEqual(conv_stats[0][1], 3)  # Total messages
        self.assertEqual(conv_stats[0][2], 1)  # User messages
        self.assertEqual(conv_stats[0][3], 0)  # Media messages
        
        # Second conversation (media chat)
        self.assertEqual(conv_stats[1][1], 2)  # Total messages
        self.assertEqual(conv_stats[1][2], 1)  # User messages
        self.assertEqual(conv_stats[1][3], 2)  # Media messages
        
        # Third conversation (no user messages)
        self.assertEqual(conv_stats[2][1], 1)  # Total messages
        self.assertEqual(conv_stats[2][2], 0)  # User messages
        self.assertEqual(conv_stats[2][3], 0)  # Media messages
        
        conn.close()
    
    def test_incremental_cleaning(self):
        """Test incremental message cleaning"""
        # Setup cleaned database
        setup_cleaned_db(self.cleaned_db)
        
        # First cleaning
        num_cleaned = clean_messages(self.raw_db, self.cleaned_db)
        self.assertEqual(num_cleaned, 6)
        
        # Second cleaning (should process no new messages)
        num_cleaned = clean_messages(self.raw_db, self.cleaned_db)
        self.assertEqual(num_cleaned, 0)
        
        # Add new message to raw database
        conn = sqlite3.connect(self.raw_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (10, 1, "New message", "2024-01-01 12:05:00", 0, "+1234567890", 0, datetime.now(), "Test Chat", "Test Room")
        )
        conn.commit()
        conn.close()
        
        # Third cleaning (should process one new message)
        num_cleaned = clean_messages(self.raw_db, self.cleaned_db)
        self.assertEqual(num_cleaned, 1)

if __name__ == '__main__':
    unittest.main() 