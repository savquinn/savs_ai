import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def explore_chat_db(db_path):
    """
    Perform basic exploratory analysis on an iMessage chat.db file

    Parameters:
    db_path (str): Path to the chat.db SQLite database
    """
    # Expand the tilde in the path
    db_path = os.path.expanduser(db_path)
    print(f"Analyzing chat database at: {db_path}")

    # Create a temporary copy of the database
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "chat.db")
    try:
        shutil.copy2(db_path, temp_db_path)
        print(f"Created temporary copy at: {temp_db_path}")

        # Connect to the temporary database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n=== Database contains {len(tables)} tables ===")
        for table in tables:
            print(f"- {table[0]}")

        # Get basic counts
        print("\n=== Basic Counts ===")
        count_queries = {
            "Total messages": "SELECT COUNT(*) FROM message",
            "Total conversations": "SELECT COUNT(*) FROM chat",
            "Total contacts": "SELECT COUNT(*) FROM handle",
            "Messages with attachments": "SELECT COUNT(*) FROM message WHERE cache_has_attachments = 1",
            "Empty messages": "SELECT COUNT(*) FROM message WHERE text IS NULL OR text = ''",
        }

        for label, query in count_queries.items():
            try:
                cursor.execute(query)
                count = cursor.fetchone()[0]
                print(f"{label}: {count:,}")
            except sqlite3.Error as e:
                print(f"{label}: Error - {e}")

        # Message types breakdown
        print("\n=== Message Types ===")
        try:
            cursor.execute(
                "SELECT service, COUNT(*) as count FROM message GROUP BY service"
            )
            for row in cursor.fetchall():
                print(f"{row[0] or 'Unknown'}: {row[1]:,}")
        except sqlite3.Error as e:
            print(f"Error getting message types: {e}")

        # Get time range
        print("\n=== Time Range ===")
        try:
            cursor.execute(
                """
                SELECT
                    datetime(MIN(date)/1000000000 + 978307200, 'unixepoch') as first_message,
                    datetime(MAX(date)/1000000000 + 978307200, 'unixepoch') as last_message
                FROM message
                WHERE date > 0
            """
            )
            time_range = cursor.fetchone()
            print(f"First message: {time_range[0]}")
            print(f"Last message: {time_range[1]}")
        except sqlite3.Error as e:
            print(f"Error getting time range: {e}")

        # Message length statistics
        print("\n=== Message Length Statistics ===")
        try:
            cursor.execute(
                """
                SELECT
                    AVG(LENGTH(text)) as avg_length,
                    MIN(LENGTH(text)) as min_length,
                    MAX(LENGTH(text)) as max_length,
                    COUNT(*) as count_with_text
                FROM message
                WHERE text IS NOT NULL AND LENGTH(text) > 0
            """
            )
            length_stats = cursor.fetchone()
            print(f"Average message length: {length_stats[0]:.1f} characters")
            print(f"Minimum message length: {length_stats[1]} characters")
            print(f"Maximum message length: {length_stats[2]} characters")
            print(f"Messages with text: {length_stats[3]:,}")
        except sqlite3.Error as e:
            print(f"Error getting message length stats: {e}")

        # Create a directory for visualizations
        os.makedirs("chat_db_analysis", exist_ok=True)

        # Messages over time
        try:
            # Get messages by month
            query = """
                SELECT
                    strftime('%Y-%m', datetime(date/1000000000 + 978307200, 'unixepoch')) as month,
                    COUNT(*) as count
                FROM message
                WHERE date > 0
                GROUP BY month
                ORDER BY month
            """
            messages_by_month = pd.read_sql_query(query, conn)

            if not messages_by_month.empty:
                plt.figure(figsize=(12, 6))
                plt.bar(messages_by_month["month"], messages_by_month["count"])
                plt.title("Messages by Month")
                plt.xlabel("Month")
                plt.ylabel("Number of Messages")
                plt.xticks(rotation=90)
                plt.tight_layout()
                plt.savefig("chat_db_analysis/messages_by_month.png")
                print("\nCreated visualization: chat_db_analysis/messages_by_month.png")
        except Exception as e:
            print(f"Error creating messages by month chart: {e}")

        # Messages by sender (top 10)
        try:
            query = """
                SELECT
                    CASE
                        WHEN message.is_from_me = 1 THEN 'Me'
                        ELSE COALESCE(handle.id, 'Unknown')
                    END as sender,
                    COUNT(*) as count
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                GROUP BY sender
                ORDER BY count DESC
                LIMIT 10
            """
            messages_by_sender = pd.read_sql_query(query, conn)

            if not messages_by_sender.empty:
                plt.figure(figsize=(10, 6))
                sns.barplot(x="count", y="sender", data=messages_by_sender)
                plt.title("Top 10 Message Senders")
                plt.xlabel("Number of Messages")
                plt.ylabel("Sender")
                plt.tight_layout()
                plt.savefig("chat_db_analysis/messages_by_sender.png")
                print("Created visualization: chat_db_analysis/messages_by_sender.png")
        except Exception as e:
            print(f"Error creating messages by sender chart: {e}")

        # Top conversations
        print("\n=== Top 10 Conversations by Message Count ===")
        try:
            query = """
                SELECT
                    c.display_name,
                    COUNT(cmj.message_id) as message_count
                FROM chat c
                JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
                GROUP BY c.ROWID
                ORDER BY message_count DESC
                LIMIT 10
            """
            top_chats = pd.read_sql_query(query, conn)

            if not top_chats.empty:
                for _, row in top_chats.iterrows():
                    print(
                        f"{row['display_name'] or 'Unnamed Chat'}: {row['message_count']:,} messages"
                    )

                # Create visualization
                plt.figure(figsize=(10, 6))
                sns.barplot(x="message_count", y="display_name", data=top_chats)
                plt.title("Top 10 Conversations by Message Count")
                plt.xlabel("Number of Messages")
                plt.ylabel("Conversation")
                plt.tight_layout()
                plt.savefig("chat_db_analysis/top_conversations.png")
                print("Created visualization: chat_db_analysis/top_conversations.png")
        except Exception as e:
            print(f"Error analyzing top conversations: {e}")

        # Oldest conversation
        print("\n=== Oldest Conversation ===")
        try:
            query = """
                SELECT
                    c.display_name,
                    datetime(MIN(m.date)/1000000000 + 978307200, 'unixepoch') as first_message_date,
                    COUNT(cmj.message_id) as message_count
                FROM chat c
                JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
                JOIN message m ON cmj.message_id = m.ROWID
                GROUP BY c.ROWID
                ORDER BY first_message_date ASC
                LIMIT 1
            """
            oldest_chat = pd.read_sql_query(query, conn)

            if not oldest_chat.empty:
                print(f"Conversation: {oldest_chat['display_name'].iloc[0] or 'Unnamed Chat'}")
                print(f"First message date: {oldest_chat['first_message_date'].iloc[0]}")
                print(f"Total messages: {oldest_chat['message_count'].iloc[0]:,}")
        except Exception as e:
            print(f"Error analyzing oldest conversation: {e}")

        # Sample messages (just to see format)
        print("\n=== Sample Messages (5 most recent) ===")
        try:
            query = """
                SELECT
                    datetime(message.date/1000000000 + 978307200, 'unixepoch') as date,
                    CASE
                        WHEN message.is_from_me = 1 THEN 'Me'
                        ELSE COALESCE(handle.id, 'Unknown')
                    END as sender,
                    SUBSTR(message.text, 1, 50) as text_sample
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                WHERE message.text IS NOT NULL
                ORDER BY message.date DESC
                LIMIT 5
            """
            sample_messages = pd.read_sql_query(query, conn)

            if not sample_messages.empty:
                for _, row in sample_messages.iterrows():
                    print(
                        f"[{row['date']}] {row['sender']}: {row['text_sample']}{'...' if len(row['text_sample']) == 50 else ''}"
                    )
        except Exception as e:
            print(f"Error showing sample messages: {e}")

        # Distribution of message lengths
        try:
            query = """
                SELECT LENGTH(text) as message_length
                FROM message
                WHERE text IS NOT NULL AND LENGTH(text) > 0 AND LENGTH(text) < 1000
            """
            message_lengths = pd.read_sql_query(query, conn)

            if not message_lengths.empty:
                plt.figure(figsize=(10, 6))
                sns.histplot(message_lengths["message_length"], bins=30)
                plt.title("Distribution of Message Lengths")
                plt.xlabel("Message Length (characters)")
                plt.ylabel("Frequency")
                plt.tight_layout()
                plt.savefig("chat_db_analysis/message_length_distribution.png")
                print(
                    "Created visualization: chat_db_analysis/message_length_distribution.png"
                )
        except Exception as e:
            print(f"Error creating message length distribution: {e}")

        # Daily activity patterns (hour of day)
        try:
            query = """
                SELECT
                    strftime('%H', datetime(date/1000000000 + 978307200, 'unixepoch')) as hour,
                    COUNT(*) as count
                FROM message
                WHERE date > 0
                GROUP BY hour
                ORDER BY hour
            """
            messages_by_hour = pd.read_sql_query(query, conn)

            if not messages_by_hour.empty:
                plt.figure(figsize=(10, 6))
                sns.barplot(x="hour", y="count", data=messages_by_hour)
                plt.title("Message Activity by Hour of Day")
                plt.xlabel("Hour of Day")
                plt.ylabel("Number of Messages")
                plt.tight_layout()
                plt.savefig("chat_db_analysis/messages_by_hour.png")
                print("Created visualization: chat_db_analysis/messages_by_hour.png")
        except Exception as e:
            print(f"Error creating messages by hour chart: {e}")

        print(
            "\nData exploration complete. Visualizations saved to 'chat_db_analysis' folder."
        )
    finally:
        # Clean up the temporary copy
        try:
            shutil.rmtree(temp_dir)
            print("Cleaned up temporary files")
        except Exception as e:
            print(f"Warning: Could not clean up temporary files: {e}")


if __name__ == "__main__":
    # Update this path to your chat.db location
    db_path = "~/Library/Messages/chat.db"
    explore_chat_db(db_path)
