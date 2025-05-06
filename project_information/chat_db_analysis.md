Analyzing chat database at: /Users/sfrisk/Library/Messages/chat.db
Created temporary copy at: /var/folders/vp/k040qhz57h7fwqm3cfgjzf1c0000gn/T/tmpv4fi_34m/chat.db

=== Database contains 19 tables ===
- _SqliteDatabaseProperties
- chat_message_join
- deleted_messages
- sqlite_sequence
- chat_recoverable_message_join
- handle
- sync_deleted_chats
- kvtable
- sync_deleted_attachments
- sync_deleted_messages
- unsynced_removed_recoverable_messages
- recoverable_message_part
- chat_handle_join
- message_attachment_join
- message_processing_task
- message
- chat
- attachment
- sqlite_stat1

=== Basic Counts ===
Total messages: 5,720
Total conversations: 478
Total contacts: 362
Messages with attachments: 478
Empty messages: 500

=== Message Types ===
iMessage: 5,720

=== Time Range ===
First message: 2023-12-13 22:55:26
Last message: 2025-05-06 06:09:36

=== Message Length Statistics ===
Average message length: 62.0 characters
Minimum message length: 1 characters
Maximum message length: 3176 characters
Messages with text: 5,220

Created visualization: chat_db_analysis/messages_by_month.png
Created visualization: chat_db_analysis/messages_by_sender.png

=== Top 10 Conversations by Message Count ===
Unnamed Chat: 968 messages
Extended Frisks: 475 messages
Unnamed Chat: 432 messages
Montichella: 298 messages
Miss Idioms School for Troubled Girls: 255 messages
Aquatic Avian Kids: 176 messages
Unnamed Chat: 172 messages
Unnamed Chat: 167 messages
Unnamed Chat: 139 messages
Unnamed Chat: 132 messages
Created visualization: chat_db_analysis/top_conversations.png

=== Sample Messages (5 most recent) ===
[2025-05-06 06:08:21] +13105933524: Yesss cambria 
[2025-05-06 06:08:12] +13105933524: Reacted 🔥 to “Booked a moro bay campsite and one n...
[2025-05-06 05:47:28] +13173138053: i want what they’re having
[2025-05-06 05:46:17] +13173138053: they look very content
[2025-05-06 05:45:05] +13173138053: Le dio risa una 
Created visualization: chat_db_analysis/message_length_distribution.png
Created visualization: chat_db_analysis/messages_by_hour.png

Data exploration complete. Visualizations saved to 'chat_db_analysis' folder.