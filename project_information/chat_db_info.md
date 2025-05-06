sqlite> .tables
_SqliteDatabaseProperties              message
attachment                             message_attachment_join
chat                                   message_processing_task
chat_handle_join                       recoverable_message_part
chat_message_join                      sync_deleted_attachments
chat_recoverable_message_join          sync_deleted_chats
deleted_messages                       sync_deleted_messages
handle                                 unsynced_removed_recoverable_messages
kvtable
sqlite> .schema message
CREATE TABLE message (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, guid TEXT UNIQUE NOT NULL, text TEXT, replace INTEGER DEFAULT 0, service_center TEXT, handle_id INTEGER DEFAULT 0, subject TEXT, country TEXT, attributedBody BLOB, version INTEGER DEFAULT 0, type INTEGER DEFAULT 0, service TEXT, account TEXT, account_guid TEXT, error INTEGER DEFAULT 0, date INTEGER, date_read INTEGER, date_delivered INTEGER, is_delivered INTEGER DEFAULT 0, is_finished INTEGER DEFAULT 0, is_emote INTEGER DEFAULT 0, is_from_me INTEGER DEFAULT 0, is_empty INTEGER DEFAULT 0, is_delayed INTEGER DEFAULT 0, is_auto_reply INTEGER DEFAULT 0, is_prepared INTEGER DEFAULT 0, is_read INTEGER DEFAULT 0, is_system_message INTEGER DEFAULT 0, is_sent INTEGER DEFAULT 0, has_dd_results INTEGER DEFAULT 0, is_service_message INTEGER DEFAULT 0, is_forward INTEGER DEFAULT 0, was_downgraded INTEGER DEFAULT 0, is_archive INTEGER DEFAULT 0, cache_has_attachments INTEGER DEFAULT 0, cache_roomnames TEXT, was_data_detected INTEGER DEFAULT 0, was_deduplicated INTEGER DEFAULT 0, is_audio_message INTEGER DEFAULT 0, is_played INTEGER DEFAULT 0, date_played INTEGER, item_type INTEGER DEFAULT 0, other_handle INTEGER DEFAULT 0, group_title TEXT, group_action_type INTEGER DEFAULT 0, share_status INTEGER DEFAULT 0, share_direction INTEGER DEFAULT 0, is_expirable INTEGER DEFAULT 0, expire_state INTEGER DEFAULT 0, message_action_type INTEGER DEFAULT 0, message_source INTEGER DEFAULT 0, associated_message_guid TEXT, associated_message_type INTEGER DEFAULT 0, balloon_bundle_id TEXT, payload_data BLOB, expressive_send_style_id TEXT, associated_message_range_location INTEGER DEFAULT 0, associated_message_range_length INTEGER DEFAULT 0, time_expressive_send_played INTEGER, message_summary_info BLOB, ck_sync_state INTEGER DEFAULT 0, ck_record_id TEXT, ck_record_change_tag TEXT, destination_caller_id TEXT, is_corrupt INTEGER DEFAULT 0, reply_to_guid TEXT, sort_id INTEGER, is_spam INTEGER DEFAULT 0, has_unseen_mention INTEGER DEFAULT 0, thread_originator_guid TEXT, thread_originator_part TEXT, syndication_ranges TEXT, synced_syndication_ranges TEXT, was_delivered_quietly INTEGER DEFAULT 0, did_notify_recipient INTEGER DEFAULT 0, date_retracted INTEGER, date_edited INTEGER, was_detonated INTEGER DEFAULT 0, part_count INTEGER, is_stewie INTEGER DEFAULT 0, is_sos INTEGER DEFAULT 0, is_critical INTEGER DEFAULT 0, bia_reference_id TEXT, is_kt_verified INTEGER DEFAULT 0, fallback_hash TEXT);
CREATE INDEX message_idx_date ON message(date);
CREATE INDEX message_idx_thread_originator_guid ON message(thread_originator_guid);
CREATE INDEX message_idx_handle ON message(handle_id, date);
CREATE INDEX message_idx_handle_id ON message(handle_id);
CREATE INDEX message_idx_is_sent_is_from_me_error ON message(is_sent, is_from_me, error);
CREATE INDEX message_idx_associated_message ON message(associated_message_guid);
CREATE INDEX message_idx_undelivered_one_to_one_imessage ON message(cache_roomnames,service,is_sent,is_delivered,was_downgraded,item_type) where cache_roomnames IS NULL AND service = 'iMessage' AND is_sent = 1 AND is_delivered = 0 AND was_downgraded = 0 AND item_type == 0;
CREATE INDEX message_idx_cache_has_attachments ON message(cache_has_attachments);
CREATE INDEX message_idx_other_handle ON message(other_handle);
CREATE INDEX message_idx_was_downgraded ON message(was_downgraded);
CREATE INDEX message_idx_expire_state ON message(expire_state);
CREATE INDEX message_idx_is_read ON message(is_read, is_from_me, is_finished);
CREATE INDEX message_idx_isRead_isFromMe_itemType ON message(is_read, is_from_me, item_type);
CREATE INDEX message_idx_failed ON message(is_finished, is_from_me, error);
CREATE TRIGGER after_delete_on_message AFTER DELETE ON message BEGIN     DELETE FROM handle         WHERE handle.ROWID = OLD.handle_id     AND         (SELECT 1 from chat_handle_join WHERE handle_id = OLD.handle_id LIMIT 1) IS NULL     AND         (SELECT 1 from message WHERE handle_id = OLD.handle_id LIMIT 1) IS NULL     AND         (SELECT 1 from message WHERE other_handle = OLD.handle_id LIMIT 1) IS NULL; END;
CREATE TRIGGER update_message_date_after_update_on_message AFTER UPDATE OF date ON message BEGIN UPDATE chat_message_join SET message_date = NEW.date WHERE message_id = NEW.ROWID AND message_date != NEW.date; END;
CREATE TRIGGER after_delete_on_message_plugin AFTER DELETE ON message WHEN OLD.balloon_bundle_id IS NOT NULL BEGIN   SELECT after_delete_message_plugin(OLD.ROWID, OLD.guid); END;
CREATE TRIGGER add_to_sync_deleted_messages AFTER DELETE ON message BEGIN     INSERT INTO sync_deleted_messages (guid, recordID) VALUES (OLD.guid, OLD.ck_record_id); END;
CREATE TRIGGER delete_associated_messages_after_delete_on_message AFTER DELETE ON message BEGIN DELETE FROM message WHERE (OLD.associated_message_guid IS NULL AND associated_message_guid IS NOT NULL AND guid = OLD.associated_message_guid); END;
CREATE TRIGGER add_to_deleted_messages AFTER DELETE ON message BEGIN     INSERT INTO deleted_messages (guid) VALUES (OLD.guid); END;
CREATE TRIGGER update_last_failed_message_date AFTER UPDATE OF error ON message WHEN   NEW.error != 0 AND NEW.date > COALESCE((SELECT value FROM kvtable WHERE key = 'lastFailedMessageDate'), 0) BEGIN   INSERT OR REPLACE INTO kvtable (key, value) VALUES ('lastFailedMessageDate', NEW.date);   INSERT OR REPLACE INTO kvtable (key, value) VALUES ('lastFailedMessageRowID', NEW.rowID); END;
sqlite> .schsqlite> .schema chat
CREATE TABLE chat (ROWID INTEGER PRIMARY KEY AUTOINCREMENT, guid TEXT UNIQUE NOT NULL, style INTEGER, state INTEGER, account_id TEXT, properties BLOB, chat_identifier TEXT, service_name TEXT, room_name TEXT, account_login TEXT, is_archived INTEGER DEFAULT 0, last_addressed_handle TEXT, display_name TEXT, group_id TEXT, is_filtered INTEGER DEFAULT 0, successful_query INTEGER, engram_id TEXT, server_change_token TEXT, ck_sync_state INTEGER DEFAULT 0, original_group_id TEXT, last_read_message_timestamp INTEGER DEFAULT 0, cloudkit_record_id TEXT, last_addressed_sim_id TEXT, is_blackholed INTEGER DEFAULT 0, syndication_date INTEGER DEFAULT 0, syndication_type INTEGER DEFAULT 0, is_recovered INTEGER DEFAULT 0, is_deleting_incoming_messages INTEGER DEFAULT 0);
CREATE INDEX chat_idx_chat_identifier_service_name ON chat(chat_identifier, service_name);
CREATE INDEX chat_idx_chat_identifier ON chat(chat_identifier);
CREATE INDEX chat_idx_chat_room_name_service_name ON chat(room_name, service_name);
CREATE INDEX chat_idx_is_archived ON chat(is_archived);
CREATE INDEX chat_idx_group_id ON chat(group_id);
CREATE TRIGGER after_delete_on_chat AFTER DELETE ON chat BEGIN DELETE FROM chat_message_join WHERE chat_id = OLD.ROWID; END;
sqlite> .schema handle
CREATE TABLE handle (ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE, id TEXT NOT NULL, country TEXT, service TEXT NOT NULL, uncanonicalized_id TEXT, person_centric_id TEXT, UNIQUE (id, service) );
sqlite>