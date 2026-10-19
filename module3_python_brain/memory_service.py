import os
import json
import time
from typing import Dict, List, Any, Optional
from database import db, DB_PATH, LEGACY_JSON_PATH

MEMORY_DIR = os.path.dirname(DB_PATH)
MEMORY_FILE = LEGACY_JSON_PATH


class MemoryService:
    """
    Project L.O.O.N.A. Memory & Operative Vault (Powered by SQLite3)
    Stores and persists:
      1. Saved Face Identities (Names & visual notes)
      2. Saved Custom Commands & Macro Choreographies
      3. Saved Memories, Notes, and User Preferences
      4. ESP32-S3 Expansion GPIO Pin Roles & Line Follower Configuration
      5. Chat History & Conversation Auditing
    """

    def __init__(self):
        self.db = db
        self._default_pin_labels = {
            "2": "Auxiliary LED / Headlight",
            "3": "Buzzer / Beeper",
            "6": "Relay / Gripper",
            "21": "Laser / Targeting Marker",
            "38": "Aux Sensor Power"
        }
        self.sync_from_db()

    @property
    def memory(self) -> Dict[str, Any]:
        """Provides dynamic dictionary representation matching legacy memory format for WebApp."""
        faces = self.db.get_faces()
        commands = self.db.get_commands()
        notes = self.db.get_notes()
        custom_pins = self.db.get_custom_pins()
        line_follower = self.get_line_follower_config()

        # Combine default pin labels with custom pin labels
        labels = dict(self._default_pin_labels)
        for p, d in custom_pins.items():
            if d.get("label"):
                labels[p] = d["label"]

        return {
            "project": "Project L.O.O.N.A. (Locomotive Optical Operative for Navigation and Assistance)",
            "database": "SQLite3 (loona_database.db)",
            "faces": faces,
            "commands": commands,
            "notes": notes,
            "custom_pins": custom_pins,
            "pin_labels": labels,
            "line_follower": line_follower
        }

    def sync_from_db(self):
        """Creates a JSON snapshot backup on disk for export and inspection."""
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MEMORY] Error writing JSON backup snapshot: {e}")

    def save(self):
        """Legacy helper: triggers JSON snapshot backup from SQLite3."""
        self.sync_from_db()

    def load(self):
        """Legacy helper: syncs state."""
        self.sync_from_db()

    # --- Face Memories (SQLite3) ---
    def save_face(self, name: str, role: str = "Friend / Orbit", notes: str = "") -> Dict[str, Any]:
        clean_name = name.strip()
        entry = self.db.save_face(clean_name, role=role, notes=notes)
        self.sync_from_db()
        print(f"[MEMORY-SQLITE3] Saved face profile: '{clean_name}' (Role: {role})")
        return entry

    def get_faces(self) -> Dict[str, Any]:
        return self.db.get_faces()

    def delete_face(self, name: str) -> bool:
        res = self.db.delete_face(name)
        if res:
            self.sync_from_db()
            print(f"[MEMORY-SQLITE3] Deleted face profile: '{name}'")
        return res

    # --- Custom Commands & Macros (SQLite3) ---
    def save_command(self, trigger: str, actions: List[Dict[str, Any]], desc: str = "") -> Dict[str, Any]:
        clean_trigger = trigger.lower().strip()
        entry = self.db.save_command(clean_trigger, actions, desc)
        self.sync_from_db()
        print(f"[MEMORY-SQLITE3] Saved custom command in SQLite: '{clean_trigger}'")
        return entry

    def get_commands(self) -> Dict[str, Any]:
        return self.db.get_commands()

    def find_command(self, text: str) -> Optional[Dict[str, Any]]:
        return self.db.find_command(text)

    def delete_command(self, trigger: str) -> bool:
        res = self.db.delete_command(trigger)
        if res:
            self.sync_from_db()
            print(f"[MEMORY-SQLITE3] Deleted command: '{trigger}'")
        return res

    # --- General Notes & Knowledge (SQLite3) ---
    def save_note(self, key: str, value: str) -> Dict[str, Any]:
        clean_key = key.strip()
        entry = self.db.save_note(clean_key, value)
        self.sync_from_db()
        print(f"[MEMORY-SQLITE3] Saved note in SQLite: '{clean_key}' -> '{value}'")
        return entry

    def get_notes(self) -> Dict[str, Any]:
        return self.db.get_notes()

    def delete_note(self, key: str) -> bool:
        res = self.db.delete_note(key)
        if res:
            self.sync_from_db()
            print(f"[MEMORY-SQLITE3] Deleted note from SQLite: '{key}'")
        return res

    # --- Pin Roles & Hardware Behavior Customizer (SQLite3) ---
    def set_pin_role(self, pin: str, role: str, label: str = "", last_val: int = 0) -> Dict[str, Any]:
        entry = self.db.set_pin_role(pin, role, label, last_val)
        self.sync_from_db()
        print(f"[MEMORY-SQLITE3] Configured Pin {pin} in SQLite: Role={role.upper()}, Label={entry['label']}")
        return entry

    def get_custom_pins(self) -> Dict[str, Any]:
        return self.db.get_custom_pins()

    def delete_pin_role(self, pin: str) -> bool:
        res = self.db.delete_pin_role(pin)
        if res:
            self.sync_from_db()
            print(f"[MEMORY-SQLITE3] Deleted custom role for Pin {pin}")
        return res

    # --- Line Follower Configuration (SQLite3) ---
    def set_line_follower_config(self, enabled: bool, left_pin: int = 2, right_pin: int = 3, speed: int = 140, invert: bool = False) -> Dict[str, Any]:
        cfg = {
            "enabled": enabled,
            "left_pin": left_pin,
            "right_pin": right_pin,
            "speed": speed,
            "invert": invert,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.db.set_setting("line_follower", cfg)
        self.sync_from_db()
        print(f"[MEMORY-SQLITE3] Saved Line Follower config to SQLite: Enabled={enabled}, L={left_pin}, R={right_pin}, Spd={speed}")
        return cfg

    def get_line_follower_config(self) -> Dict[str, Any]:
        return self.db.get_setting("line_follower", {
            "enabled": False,
            "left_pin": 2,
            "right_pin": 3,
            "speed": 140,
            "invert": False
        })

    # --- Pin Labels ---
    def set_pin_label(self, pin: str, label: str):
        existing = self.db.get_custom_pins().get(str(pin), {})
        role = existing.get("role", "OUTPUT")
        self.db.set_pin_role(pin, role, label)
        self.sync_from_db()

    def get_pin_labels(self) -> Dict[str, str]:
        labels = dict(self._default_pin_labels)
        for p, d in self.db.get_custom_pins().items():
            if d.get("label"):
                labels[p] = d["label"]
        return labels

    # --- Conversation Logging (SQLite3) ---
    def log_chat(self, sender: str, message: str, emotion: str = "neutral") -> Dict[str, Any]:
        return self.db.log_chat(sender, message, emotion)

    def get_recent_chats(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.db.get_recent_chat_logs(limit)

    def get_db_stats(self) -> Dict[str, Any]:
        return self.db.get_database_stats()

    # --- Photo Gallery (SQLite3) ---
    def save_photo(self, filename: str, filepath: str, notes: str = "") -> Dict[str, Any]:
        return self.db.save_photo(filename, filepath, notes)

    def get_photos(self) -> List[Dict[str, Any]]:
        return self.db.get_photos()

    def delete_photo(self, identifier: Any) -> bool:
        return self.db.delete_photo(identifier)

    # --- Summary for AI Prompt Injection ---
    def get_context_for_prompt(self) -> str:
        """Constructs a concise memory block for Gemini's prompt."""
        lines = []
        faces = self.get_faces()
        if faces:
            names = [f"{f} ({data.get('role', 'Orbit')})" for f, data in faces.items()]
            lines.append(f"Recognized Orbit faces: {', '.join(names)}.")

        notes = self.get_notes()
        if notes:
            n_list = [f"{k}: {v.get('value', v)}" for k, v in list(notes.items())[-5:]]
            lines.append(f"User saved notes: {'; '.join(n_list)}.")

        cmds = self.get_commands()
        if cmds:
            c_list = list(cmds.keys())[:6]
            lines.append(f"Custom user macro triggers: {', '.join(c_list)}.")

        custom_pins = self.get_custom_pins()
        if custom_pins:
            p_list = [f"GPIO {p}: {data.get('role', 'OUTPUT')} ({data.get('label', '')})" for p, data in custom_pins.items()]
            lines.append(f"Custom expansion hardware pins: {', '.join(p_list)}.")

        lf = self.get_line_follower_config()
        if lf.get("enabled"):
            lines.append(f"Line Follower: ACTIVE on Left Pin {lf['left_pin']}, Right Pin {lf['right_pin']}.")

        return "\n".join(lines)


# Singleton memory vault instance
memory_vault = MemoryService()
