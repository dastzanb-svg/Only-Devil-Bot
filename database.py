# database.py

import sqlite3
from datetime import datetime
from config import DATABASE_PATH


class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    # =========================================================
    # CONNECTION
    # =========================================================

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # =========================================================
    # INITIALIZE DATABASE
    # =========================================================

    def init_db(self):
        conn = self.connect()
        cursor = conn.cursor()

        # -----------------------------------------------------
        # USERS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                first_name TEXT,
                username TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # -----------------------------------------------------
        # ADMINS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # -----------------------------------------------------
        # VIDEOS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                telegram_file_id TEXT NOT NULL,
                unique_code TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                downloads INTEGER DEFAULT 0
            )
        """)

        # -----------------------------------------------------
        # TOPICS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                unique_code TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                downloads INTEGER DEFAULT 0
            )
        """)

        # -----------------------------------------------------
        # TOPIC VIDEOS
        #
        # هر موضوع می‌تواند چند ویدیو داشته باشد.
        # position ترتیب ویدیوها را مشخص می‌کند.
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                created_at TEXT NOT NULL,

                UNIQUE(topic_id, video_id),

                FOREIGN KEY(topic_id)
                    REFERENCES topics(id)
                    ON DELETE CASCADE,

                FOREIGN KEY(video_id)
                    REFERENCES videos(id)
                    ON DELETE CASCADE
            )
        """)

        # -----------------------------------------------------
        # ADVERTISING CHANNELS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advertising_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                channel_username TEXT,
                channel_name TEXT,
                channel_link TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # -----------------------------------------------------
        # SETTINGS
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # -----------------------------------------------------
        # VIDEO DELIVERIES
        #
        # برای ثبت اینکه چه ویدیویی برای چه کاربری ارسال شده.
        # -----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                telegram_message_id INTEGER,
                delivered_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY(video_id)
                    REFERENCES videos(id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()
        conn.close()

    # =========================================================
    # USERS
    # =========================================================

    def add_user(self, user_id, first_name=None, username=None):
        conn = self.connect()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO users (
                user_id,
                first_name,
                username,
                created_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username,
                created_at = excluded.created_at
        """, (
            user_id,
            first_name,
            username,
            now
        ))

        conn.commit()
        conn.close()

    def get_user(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_all_users(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()

        conn.close()

        return results

    def count_users(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM users
        """)

        count = cursor.fetchone()[0]

        conn.close()

        return count

    # =========================================================
    # ADMINS
    # =========================================================

    def add_admin(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO admins (
                user_id,
                created_at
            )
            VALUES (?, ?)
        """, (
            user_id,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def remove_admin(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM admins
            WHERE user_id = ?
        """, (user_id,))

        conn.commit()
        conn.close()

    def is_admin(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1
            FROM admins
            WHERE user_id = ?
            LIMIT 1
        """, (user_id,))

        result = cursor.fetchone()

        conn.close()

        return result is not None

    def get_admins(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM admins
            ORDER BY created_at ASC
        """)

        results = cursor.fetchall()

        conn.close()

        return results

    # =========================================================
    # VIDEOS
    # =========================================================

    def add_video(
        self,
        title,
        description,
        telegram_file_id,
        unique_code
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO videos (
                title,
                description,
                telegram_file_id,
                unique_code,
                is_active,
                created_at,
                downloads
            )
            VALUES (?, ?, ?, ?, 1, ?, 0)
        """, (
            title,
            description,
            telegram_file_id,
            unique_code,
            datetime.now().isoformat()
        ))

        video_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return video_id

    def get_video_by_id(self, video_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM videos
            WHERE id = ?
        """, (video_id,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_video_by_code(self, unique_code):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM videos
            WHERE unique_code = ?
              AND is_active = 1
        """, (unique_code,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_all_videos(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM videos
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()

        conn.close()

        return results

    def count_videos(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM videos
            WHERE is_active = 1
        """)

        count = cursor.fetchone()[0]

        conn.close()

        return count

    def increment_video_downloads(self, video_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE videos
            SET downloads = downloads + 1
            WHERE id = ?
        """, (video_id,))

        conn.commit()
        conn.close()

    def deactivate_video(self, video_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE videos
            SET is_active = 0
            WHERE id = ?
        """, (video_id,))

        conn.commit()
        conn.close()

    # =========================================================
    # TOPICS
    # =========================================================

    def add_topic(
        self,
        title,
        description,
        unique_code
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO topics (
                title,
                description,
                unique_code,
                is_active,
                created_at,
                downloads
            )
            VALUES (?, ?, ?, 1, ?, 0)
        """, (
            title,
            description,
            unique_code,
            datetime.now().isoformat()
        ))

        topic_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return topic_id

    def get_topic_by_id(self, topic_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM topics
            WHERE id = ?
        """, (topic_id,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_topic_by_code(self, unique_code):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM topics
            WHERE unique_code = ?
              AND is_active = 1
        """, (unique_code,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_all_topics(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM topics
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()

        conn.close()

        return results

    def count_topics(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM topics
            WHERE is_active = 1
        """)

        count = cursor.fetchone()[0]

        conn.close()

        return count

    def increment_topic_downloads(self, topic_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE topics
            SET downloads = downloads + 1
            WHERE id = ?
        """, (topic_id,))

        conn.commit()
        conn.close()

    def deactivate_topic(self, topic_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE topics
            SET is_active = 0
            WHERE id = ?
        """, (topic_id,))

        conn.commit()
        conn.close()

    # =========================================================
    # TOPIC ↔ VIDEO
    # =========================================================

    def add_video_to_topic(
        self,
        topic_id,
        video_id,
        position
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO topic_videos (
                topic_id,
                video_id,
                position,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            topic_id,
            video_id,
            position,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_topic_videos(self, topic_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                v.*,
                tv.position AS topic_position
            FROM topic_videos tv

            INNER JOIN videos v
                ON v.id = tv.video_id

            WHERE tv.topic_id = ?
              AND v.is_active = 1

            ORDER BY tv.position ASC
        """, (topic_id,))

        results = cursor.fetchall()

        conn.close()

        return results

    def get_topic_video_count(self, topic_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM topic_videos tv

            INNER JOIN videos v
                ON v.id = tv.video_id

            WHERE tv.topic_id = ?
              AND v.is_active = 1
        """, (topic_id,))

        count = cursor.fetchone()[0]

        conn.close()

        return count

    def remove_video_from_topic(
        self,
        topic_id,
        video_id
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM topic_videos
            WHERE topic_id = ?
              AND video_id = ?
        """, (
            topic_id,
            video_id
        ))

        conn.commit()
        conn.close()

    # =========================================================
    # ADVERTISING CHANNELS
    # =========================================================

    def add_advertising_channel(
        self,
        channel_id,
        channel_username=None,
        channel_name=None,
        channel_link=None
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO advertising_channels (
                channel_id,
                channel_username,
                channel_name,
                channel_link,
                is_active,
                created_at
            )
            VALUES (?, ?, ?, ?, 1, ?)
        """, (
            str(channel_id),
            channel_username,
            channel_name,
            channel_link,
            datetime.now().isoformat()
        ))

        channel_id_db = cursor.lastrowid

        conn.commit()
        conn.close()

        return channel_id_db

    def get_advertising_channels(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM advertising_channels
            WHERE is_active = 1
            ORDER BY created_at ASC
        """)

        results = cursor.fetchall()

        conn.close()

        return results

    def get_advertising_channel(self, channel_db_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM advertising_channels
            WHERE id = ?
        """, (channel_db_id,))

        result = cursor.fetchone()

        conn.close()

        return result

    def deactivate_advertising_channel(
        self,
        channel_db_id
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE advertising_channels
            SET is_active = 0
            WHERE id = ?
        """, (channel_db_id,))

        conn.commit()
        conn.close()

    # =========================================================
    # SETTINGS
    # =========================================================

    def set_setting(self, key, value):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO settings (
                key,
                value
            )
            VALUES (?, ?)

            ON CONFLICT(key)
            DO UPDATE SET
                value = excluded.value
        """, (
            key,
            str(value)
        ))

        conn.commit()
        conn.close()

    def get_setting(self, key, default=None):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value
            FROM settings
            WHERE key = ?
        """, (key,))

        result = cursor.fetchone()

        conn.close()

        if result is None:
            return default

        return result["value"]

    def delete_setting(self, key):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM settings
            WHERE key = ?
        """, (key,))

        conn.commit()
        conn.close()

    # =========================================================
    # VIDEO DELIVERY LOG
    # =========================================================

    def add_delivery(
        self,
        user_id,
        video_id,
        telegram_message_id
    ):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO video_deliveries (
                user_id,
                video_id,
                telegram_message_id,
                delivered_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            video_id,
            telegram_message_id,
            datetime.now().isoformat()
        ))

        delivery_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return delivery_id

    def mark_delivery_deleted(self, delivery_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE video_deliveries
            SET deleted_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            delivery_id
        ))

        conn.commit()
        conn.close()

    def get_delivery(self, delivery_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM video_deliveries
            WHERE id = ?
        """, (delivery_id,))

        result = cursor.fetchone()

        conn.close()

        return result

    def get_user_deliveries(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM video_deliveries
            WHERE user_id = ?
            ORDER BY delivered_at DESC
        """, (user_id,))

        results = cursor.fetchall()

        conn.close()

        return results

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_statistics(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM users
        """)
        users = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM videos
            WHERE is_active = 1
        """)
        videos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM topics
            WHERE is_active = 1
        """)
        topics = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(downloads), 0)
            FROM videos
        """)
        video_downloads = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(downloads), 0)
            FROM topics
        """)
        topic_downloads = cursor.fetchone()[0]

        conn.close()

        return {
            "users": users,
            "videos": videos,
            "topics": topics,
            "video_downloads": video_downloads,
            "topic_downloads": topic_downloads
        }


# =============================================================
# GLOBAL DATABASE INSTANCE
# =============================================================

db = Database()