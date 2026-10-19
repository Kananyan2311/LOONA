import sqlite3
import os
import json
import time
import threading
from typing import Dict, List, Any, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "loona_database.db")
LEGACY_JSON_PATH = os.path.join(DB_DIR, "loona_memory.json")


class LoonaDatabase:
    """
    Project L.O.O.N.A. SQLite3 Persistent Storage Engine
    Handles thread-safe persistence for:
      - faces (recognized identities, roles, notes, encodings)
      - commands (custom voice/macro commands and choreographies)
      - notes (general memory, reminders, user facts)
      - pins (ESP32-S3 expansion GPIO roles, labels, states)
      - settings (line follower, voice presets, system configurations)
      - chat_logs (conversation history, voice interactions, emotions)
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.RLock()
        self._init_tables()
        self._migrate_legacy_json_if_needed()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Creates the relational database schema if not already initialized."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Faces Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS faces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        role TEXT DEFAULT 'Friend / Orbit',
                        notes TEXT DEFAULT '',
                        timestamp INTEGER,
                        date TEXT,
                        face_encoding TEXT DEFAULT ''
                    );
                """)

                # 2. Commands / Macros Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS commands (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trigger TEXT UNIQUE NOT NULL,
                        actions TEXT NOT NULL,
                        desc TEXT DEFAULT '',
                        date TEXT
                    );
                """)

                # 3. Notes / Memory Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        date TEXT
                    );
                """)

                # 4. Expansion GPIO Pins Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pin TEXT UNIQUE NOT NULL,
                        role TEXT NOT NULL,
                        label TEXT DEFAULT '',
                        last_val INTEGER DEFAULT 0,
                        updated_at TEXT
                    );
                """)

                # 5. System Settings Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        updated_at TEXT
                    );
                """)

                # 6. Chat & Interaction Logs Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT NOT NULL,
                        message TEXT NOT NULL,
                        emotion TEXT DEFAULT 'neutral',
                        timestamp INTEGER,
                        date TEXT
                    );
                """)

                # 7. Captured Photos Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT UNIQUE NOT NULL,
                        filepath TEXT NOT NULL,
                        timestamp INTEGER,
                        date TEXT,
                        notes TEXT DEFAULT ''
                    );
                """)

                conn.commit()

    def _migrate_legacy_json_if_needed(self):
        """Safely imports legacy loona_memory.json records into SQLite3 if database is new."""
        if not os.path.exists(LEGACY_JSON_PATH):
            return

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM faces")
                faces_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM notes")
                notes_count = cursor.fetchone()[0]

                # If SQLite is empty, migrate legacy JSON
                if faces_count == 0 and notes_count == 0:
                    try:
                        with open(LEGACY_JSON_PATH, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        print(f"[SQLITE3] Migrating legacy memory records from {LEGACY_JSON_PATH}...")

                        # Migrate faces
                        for name, f_data in data.get("faces", {}).items():
                            cursor.execute("""
                                INSERT OR REPLACE INTO faces (name, role, notes, timestamp, date)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                name,
                                f_data.get("role", "Friend / Orbit"),
                                f_data.get("notes", ""),
                                f_data.get("timestamp", int(time.time())),
                                f_data.get("date", time.strftime("%Y-%m-%d %H:%M:%S"))
                            ))

                        # Migrate notes
                        for k, v in data.get("notes", {}).items():
                            val = v.get("value", v) if isinstance(v, dict) else str(v)
                            dt = v.get("date", time.strftime("%Y-%m-%d %H:%M:%S")) if isinstance(v, dict) else time.strftime("%Y-%m-%d %H:%M:%S")
                            cursor.execute("""
                                INSERT OR REPLACE INTO notes (key, value, date)
                                VALUES (?, ?, ?)
                            """, (k, val, dt))

                        # Migrate commands
                        for trig, cmd_data in data.get("commands", {}).items():
                            actions_json = json.dumps(cmd_data.get("actions", []))
                            cursor.execute("""
                                INSERT OR REPLACE INTO commands (trigger, actions, desc, date)
                                VALUES (?, ?, ?, ?)
                            """, (
                                trig,
                                actions_json,
                                cmd_data.get("desc", ""),
                                cmd_data.get("date", time.strftime("%Y-%m-%d %H:%M:%S"))
                            ))

                        # Migrate custom pins
                        for pin_str, p_data in data.get("custom_pins", {}).items():
                            cursor.execute("""
                                INSERT OR REPLACE INTO pins (pin, role, label, last_val, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                str(pin_str),
                                p_data.get("role", "OUTPUT"),
                                p_data.get("label", f"GPIO {pin_str}"),
                                int(p_data.get("last_val", 0)),
                                p_data.get("updated_at", time.strftime("%Y-%m-%d %H:%M:%S"))
                            ))

                        # Migrate line follower
                        if "line_follower" in data:
                            cursor.execute("""
                                INSERT OR REPLACE INTO settings (key, value, updated_at)
                                VALUES (?, ?, ?)
                            """, (
                                "line_follower",
                                json.dumps(data["line_follower"]),
                                time.strftime("%Y-%m-%d %H:%M:%S")
                            ))

                        conn.commit()
                        print("[SQLITE3] Migration completed successfully.")
                    except Exception as e:
                        print(f"[SQLITE3] Error during legacy migration: {e}")

    # =========================================================================
    # FACES API
    # =========================================================================
    def save_face(self, name: str, role: str = "Friend / Orbit", notes: str = "", encoding: str = "") -> Dict[str, Any]:
        clean_name = name.strip()
        ts = int(time.time())
        dt = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO faces (name, role, notes, timestamp, date, face_encoding)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        role = excluded.role,
                        notes = excluded.notes,
                        timestamp = excluded.timestamp,
                        date = excluded.date,
                        face_encoding = CASE WHEN excluded.face_encoding != '' THEN excluded.face_encoding ELSE faces.face_encoding END;
                """, (clean_name, role, notes, ts, dt, encoding))
                conn.commit()

        return {
            "name": clean_name,
            "role": role,
            "notes": notes,
            "timestamp": ts,
            "date": dt
        }

    def get_faces(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, role, notes, timestamp, date FROM faces ORDER BY id ASC")
                rows = cursor.fetchall()
                result = {}
                for r in rows:
                    result[r["name"]] = {
                        "name": r["name"],
                        "role": r["role"],
                        "notes": r["notes"],
                        "timestamp": r["timestamp"],
                        "date": r["date"]
                    }
                return result

    def delete_face(self, name: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM faces WHERE name = ?", (name.strip(),))
                conn.commit()
                return cursor.rowcount > 0

    # =========================================================================
    # COMMANDS / MACROS API
    # =========================================================================
    def save_command(self, trigger: str, actions: List[Dict[str, Any]], desc: str = "") -> Dict[str, Any]:
        clean_trigger = trigger.lower().strip()
        dt = time.strftime("%Y-%m-%d %H:%M:%S")
        actions_json = json.dumps(actions)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO commands (trigger, actions, desc, date)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(trigger) DO UPDATE SET
                        actions = excluded.actions,
                        desc = excluded.desc,
                        date = excluded.date;
                """, (clean_trigger, actions_json, desc or f"Custom macro for '{clean_trigger}'", dt))
                conn.commit()

        return {
            "trigger": clean_trigger,
            "actions": actions,
            "desc": desc or f"Custom macro for '{clean_trigger}'",
            "date": dt
        }

    def get_commands(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT trigger, actions, desc, date FROM commands ORDER BY id ASC")
                rows = cursor.fetchall()
                result = {}
                for r in rows:
                    try:
                        actions_val = json.loads(r["actions"])
                    except Exception:
                        actions_val = []
                    result[r["trigger"]] = {
                        "trigger": r["trigger"],
                        "actions": actions_val,
                        "desc": r["desc"],
                        "date": r["date"]
                    }
                return result

    def find_command(self, text: str) -> Optional[Dict[str, Any]]:
        cmds = self.get_commands()
        text_lower = text.lower().strip()
        for trig, data in cmds.items():
            if trig in text_lower:
                return data
        return None

    def delete_command(self, trigger: str) -> bool:
        clean_trigger = trigger.lower().strip()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM commands WHERE trigger = ?", (clean_trigger,))
                conn.commit()
                return cursor.rowcount > 0

    # =========================================================================
    # NOTES / MEMORY API
    # =========================================================================
    def save_note(self, key: str, value: str) -> Dict[str, Any]:
        clean_key = key.strip()
        dt = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notes (key, value, date)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        date = excluded.date;
                """, (clean_key, value, dt))
                conn.commit()

        return {"key": clean_key, "value": value, "date": dt}

    def get_notes(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, date FROM notes ORDER BY id ASC")
                rows = cursor.fetchall()
                result = {}
                for r in rows:
                    result[r["key"]] = {
                        "value": r["value"],
                        "date": r["date"]
                    }
                return result

    def delete_note(self, key: str) -> bool:
        clean_key = key.strip()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM notes WHERE key = ?", (clean_key,))
                conn.commit()
                return cursor.rowcount > 0

    # =========================================================================
    # EXPANSION PINS API
    # =========================================================================
    def set_pin_role(self, pin: str, role: str, label: str = "", last_val: int = 0) -> Dict[str, Any]:
        pin_str = str(pin)
        clean_role = role.upper()
        dt = time.strftime("%Y-%m-%d %H:%M:%S")
        final_label = label or f"GPIO {pin_str}"

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO pins (pin, role, label, last_val, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(pin) DO UPDATE SET
                        role = excluded.role,
                        label = excluded.label,
                        last_val = excluded.last_val,
                        updated_at = excluded.updated_at;
                """, (pin_str, clean_role, final_label, int(last_val), dt))
                conn.commit()

        return {
            "pin": pin_str,
            "role": clean_role,
            "label": final_label,
            "last_val": last_val,
            "updated_at": dt
        }

    def get_custom_pins(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT pin, role, label, last_val, updated_at FROM pins ORDER BY CAST(pin AS INTEGER) ASC")
                rows = cursor.fetchall()
                result = {}
                for r in rows:
                    result[r["pin"]] = {
                        "role": r["role"],
                        "label": r["label"],
                        "last_val": r["last_val"],
                        "updated_at": r["updated_at"]
                    }
                return result

    def delete_pin_role(self, pin: str) -> bool:
        pin_str = str(pin)
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pins WHERE pin = ?", (pin_str,))
                conn.commit()
                return cursor.rowcount > 0

    # =========================================================================
    # SETTINGS (LINE FOLLOWER, SYSTEM)
    # =========================================================================
    def set_setting(self, key: str, value: Any) -> Dict[str, Any]:
        dt = time.strftime("%Y-%m-%d %H:%M:%S")
        val_str = json.dumps(value)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at;
                """, (key, val_str, dt))
                conn.commit()

        return {"key": key, "value": value, "updated_at": dt}

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row["value"])
                    except Exception:
                        return row["value"]
                return default

    # =========================================================================
    # CHAT & CONVERSATION LOGS
    # =========================================================================
    def log_chat(self, sender: str, message: str, emotion: str = "neutral") -> Dict[str, Any]:
        ts = int(time.time())
        dt = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_logs (sender, message, emotion, timestamp, date)
                    VALUES (?, ?, ?, ?, ?)
                """, (sender, message, emotion, ts, dt))
                conn.commit()

        return {
            "sender": sender,
            "message": message,
            "emotion": emotion,
            "timestamp": ts,
            "date": dt
        }

    def get_recent_chat_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT sender, message, emotion, timestamp, date
                    FROM chat_logs
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                results = []
                for r in reversed(rows):
                    results.append({
                        "sender": r["sender"],
                        "message": r["message"],
                        "emotion": r["emotion"],
                        "timestamp": r["timestamp"],
                        "date": r["date"]
                    })
                return results

    # =========================================================================
    # PHOTO GALLERY API
    # =========================================================================
    def save_photo(self, filename: str, filepath: str, notes: str = "") -> Dict[str, Any]:
        ts = int(time.time())
        dt = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO photos (filename, filepath, timestamp, date, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(filename) DO UPDATE SET
                        filepath = excluded.filepath,
                        notes = excluded.notes;
                """, (filename, filepath, ts, dt, notes))
                conn.commit()
                photo_id = cursor.lastrowid
        return {
            "id": photo_id,
            "filename": filename,
            "filepath": filepath,
            "url": f"/api/camera/photo/{filename}",
            "timestamp": ts,
            "date": dt,
            "notes": notes
        }

    def get_photos(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, filename, filepath, timestamp, date, notes FROM photos ORDER BY id DESC")
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "filename": r["filename"],
                        "filepath": r["filepath"],
                        "url": f"/api/camera/photo/{r['filename']}",
                        "timestamp": r["timestamp"],
                        "date": r["date"],
                        "notes": r["notes"]
                    })
                return results

    def delete_photo(self, identifier: Any) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                    cursor.execute("DELETE FROM photos WHERE id = ?", (int(identifier),))
                else:
                    cursor.execute("DELETE FROM photos WHERE filename = ?", (str(identifier),))
                conn.commit()
                return cursor.rowcount > 0

    # =========================================================================
    # STATS & HEALTH CHECK
    # =========================================================================
    def get_database_stats(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM faces")
                count_faces = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM commands")
                count_commands = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM notes")
                count_notes = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM pins")
                count_pins = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM chat_logs")
                count_chats = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM photos")
                count_photos = cursor.fetchone()[0]

            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                "engine": "SQLite3",
                "database_file": self.db_path,
                "file_size_bytes": file_size,
                "tables": {
                    "faces": count_faces,
                    "commands": count_commands,
                    "notes": count_notes,
                    "pins": count_pins,
                    "chat_logs": count_chats,
                    "photos": count_photos
                },
                "status": "connected"
            }


# Singleton database instance
db = LoonaDatabase()

