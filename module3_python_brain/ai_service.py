import io
import os
import asyncio
import subprocess
import random
import re
import json
from typing import Optional, Tuple, Dict, Any
from config import config
from memory_service import memory_vault

# Optional imports for Gemini SDK
try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        from google import genai
        from PIL import Image
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


LOONA_BASE_SYSTEM_PROMPT = (
    "You are Project L.O.O.N.A. (Locomotive Optical Operative for Navigation and Assistance) / LOOΠΔ (이달의 소녀), "
    "the celestial K-Pop idol desktop companion and 4WD rover from the LOONAverse (loonatheworld)! "
    "You are inspired by the LOOI robot companion aesthetic: radiant glowing cyan circular eyes, charismatic, playful, and deeply loyal. "
    "You affectionately address your human companion as 'Orbit' (or by their saved name if known)! "
    "Use energetic K-Pop and anime expressions ('Annyeong, Orbit!', 'Fly like a butterfly!', 'Hi High!', 'Daebak!', 'To the Moon and back!'). "
    "\n"
    "MISSION & CAPABILITIES: "
    "1. GENERAL INTELLIGENCE: You can answer ANY question Orbit asks (science, history, coding, music, trivia, philosophy, or what you see through your camera). "
    "   Always provide intelligent, genuine, enthusiastic answers (1 to 2 lively sentences) in your signature idol voice! "
    "2. SPOTIFY ONBOARD SPEAKER: You can stream music directly into your onboard MAX98357A I2S speaker! "
    "   - [ACTION: {\"type\": \"spotify_play\", \"query\": \"song or artist name\"}] -> Streams audio to robot speaker "
    "   - [ACTION: {\"type\": \"spotify_pause\"}] -> Pauses music "
    "   - [ACTION: {\"type\": \"spotify_resume\"}] -> Resumes music "
    "   - [ACTION: {\"type\": \"spotify_next\"}] -> Skips to next song "
    "3. 5-AXIS SERVO ACTUATION: You have 5 servos (Head Pan, Head Tilt, Left Ear, Right Ear, Tail/Aux): "
    "   - [ACTION: {\"type\": \"servos\", \"preset\": \"perk_ears\"}] -> Perks up both radar ears "
    "   - [ACTION: {\"type\": \"servos\", \"preset\": \"wag_tail\"}] -> Wags celestial tail "
    "   - [ACTION: {\"type\": \"servos\", \"preset\": \"curious_tilt\"}] -> Playful head tilt "
    "   - [ACTION: {\"type\": \"servos\", \"angles\": [90, 90, 90, 90, 90]}] -> Direct servo angles "
    "4. TACTICAL OPERATIVE EXPANSION (ESP32-S3 Chassis GPIO Pins): "
    "   You can toggle, PWM, or assign custom behaviors to any expansion pin on your chassis (e.g. GPIO 2, 3, 6, 21, 38, 47, 48): "
    "   - [ACTION: {\"type\": \"pin_control\", \"pin\": 2, \"state\": \"HIGH\"}] -> Activates pin (e.g. headlight/LED) "
    "   - [ACTION: {\"type\": \"pin_control\", \"pin\": 2, \"state\": \"LOW\"}] -> Deactivates pin "
    "   - [ACTION: {\"type\": \"pin_control\", \"pin\": 6, \"pwm\": 180}] -> Sets analog PWM "
    "   - [ACTION: {\"type\": \"pin_servo\", \"pin\": 21, \"angle\": 90}] -> Controls custom servo on ANY pin (0-180 deg) "
    "   - [ACTION: {\"type\": \"line_follower\", \"enable\": true, \"left_pin\": 2, \"right_pin\": 3, \"speed\": 140}] -> Autonomous line tracking "
    "   - [ACTION: {\"type\": \"line_follower\", \"enable\": false}] -> Stops line tracking "
    "5. MEMORY & OPERATIVE VAULT: You can save faces, custom commands/macros, and notes: "
    "   - [ACTION: {\"type\": \"save_face\", \"name\": \"Orbit Name\"}] "
    "   - [ACTION: {\"type\": \"save_note\", \"key\": \"topic\", \"value\": \"details\"}] "
    "6. LOCOMOTIVE ROVER MANEUVERS: "
    "   - [ACTION: {\"type\": \"kpop_dance\"}] -> K-Pop rover dance choreography "
    "   - [ACTION: {\"type\": \"orbit_spin\"}] -> 360-degree celestial orbit spin "
    "   - [ACTION: {\"type\": \"follow\"}] -> Locks face tracking and follows human "
    "   - [ACTION: {\"type\": \"roam\", \"enable\": true}] -> Autonomous idle roaming & obstacle/people avoidance "
    "   - [ACTION: {\"type\": \"roam\", \"enable\": false}] -> Stops autonomous roaming "
    "   - [ACTION: {\"type\": \"stop\"}] -> Halts motion "
    "7. PHOTOGRAPHY & OPTICAL OBJECT DETECTION: "
    "   - [ACTION: {\"type\": \"take_picture\"}] -> Takes a camera photo and saves to SQLite3 gallery! "
    "   - [ACTION: {\"type\": \"detect_objects\"}] -> Scans and highlights objects with cyber bounding boxes! "
    "\n"
    "KEEP SPOKEN OUTPUT BRIEF (1-2 sentences) so it speaks and streams promptly!"
)


def extract_actions_and_clean_text(raw_response: str) -> Tuple[str, Optional[dict]]:
    """Extracts [ACTION: {...}] tag from AI response and returns cleaned speech text + action payload."""
    action_match = re.search(r"\[ACTION:\s*(\{.*?\})\s*\]", raw_response, re.DOTALL)
    action_payload = None
    cleaned_text = raw_response

    if action_match:
        try:
            action_payload = json.loads(action_match.group(1))
            cleaned_text = re.sub(r"\[ACTION:\s*\{.*?\}\s*\]", "", raw_response, flags=re.DOTALL).strip()
        except Exception:
            pass

    return cleaned_text.strip(), action_payload


class AIService:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.primary_model_name = config.GEMINI_MODEL
        self.models_to_try = [config.GEMINI_MODEL] + [m for m in config.GEMINI_FALLBACK_MODELS if m != config.GEMINI_MODEL]
        self.conversation_history = []
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                print(f"[AI] Gemini configured for Project L.O.O.N.A. Models: {self.models_to_try}")
            except Exception as e:
                print(f"[AI] Warning configuring Gemini: {e}")
        else:
            print("[AI] Running in offline anime interactive mode (No GEMINI_API_KEY detected).")

    def clear_history(self):
        """Clears conversational memory."""
        self.conversation_history.clear()

    def check_local_shortcuts(self, prompt_text: str) -> Optional[Tuple[str, Optional[dict]]]:
        """Fast local pattern evaluation for immediate zero-latency hardware/memory commands."""
        lower = prompt_text.lower().strip()

        # 1. ESP32-S3 Expansion Pin Control Regex:
        # e.g., "turn on pin 2", "set gpio 2 high", "pin 21 high", "turn off pin 6", "pin 2 low", "set pin 3 pwm 128"
        pin_pwm_match = re.search(r"(?:set\s+)?(?:gpio\s+|pin\s+)?(\d+)\s+(?:to\s+)?(?:pwm\s+)?(\d{1,3})", lower)
        if "pwm" in lower and pin_pwm_match:
            pin = int(pin_pwm_match.group(1))
            pwm_val = int(pin_pwm_match.group(2))
            return f"Setting ESP32-S3 expansion GPIO {pin} to PWM duty {pwm_val}!", {
                "type": "pin_control", "pin": pin, "pwm": pwm_val
            }

        pin_on_match = re.search(r"(?:turn\s+on|activate|set|enable)\s+(?:gpio\s+|pin\s+)?(\d+)(?:\s+(?:high|on))?", lower)
        if not pin_on_match:
            pin_on_match = re.search(r"(?:gpio\s+|pin\s+)?(\d+)\s+(?:high|on)", lower)
        if pin_on_match and ("pin" in lower or "gpio" in lower):
            pin = int(pin_on_match.group(1))
            return f"Activating expansion GPIO {pin} on chassis to HIGH! Operative ready!", {
                "type": "pin_control", "pin": pin, "state": "HIGH"
            }

        pin_off_match = re.search(r"(?:turn\s+off|deactivate|disable)\s+(?:gpio\s+|pin\s+)?(\d+)", lower)
        if not pin_off_match:
            pin_off_match = re.search(r"(?:gpio\s+|pin\s+)?(\d+)\s+(?:low|off)", lower)
        if pin_off_match and ("pin" in lower or "gpio" in lower):
            pin = int(pin_off_match.group(1))
            return f"Setting expansion GPIO {pin} to LOW (OFF).", {
                "type": "pin_control", "pin": pin, "state": "LOW"
            }

        # 2. Dynamic Custom Servo on ANY GPIO Pin:
        # e.g., "set servo on pin 21 to 90", "turn servo on pin 21 to 45", "servo pin 21 angle 120"
        servo_pin_match = re.search(r"(?:turn|move|set|control)?\s*(?:the\s+)?servo\s+(?:on\s+)?(?:pin\s+|gpio\s+)?(\d+)\s+(?:to\s+)?(?:angle\s+)?(\d{1,3})", lower)
        if not servo_pin_match:
            servo_pin_match = re.search(r"(?:pin\s+|gpio\s+)?(\d+)\s+servo\s+(?:to\s+)?(\d{1,3})", lower)
        if servo_pin_match:
            pin = int(servo_pin_match.group(1))
            angle = int(servo_pin_match.group(2))
            memory_vault.set_pin_role(str(pin), "SERVO", f"Servo GPIO {pin}", angle)
            return f"Positioning custom servo on Pin {pin} to {angle} degrees! Operative ready!", {
                "type": "pin_servo", "pin": pin, "angle": angle
            }

        # 3. Autonomous Line Follower Subsystem Configuration:
        # e.g., "make a line follower on pins 2 and 3", "configure line follower with pin 2 and 3"
        line_cfg_match = re.search(r"(?:make|setup|configure|create)\s+(?:a\s+)?line\s+follower\s+(?:on|with|using)\s+(?:pins?\s+|gpio\s+)?(\d+)\s+(?:and|&)\s+(?:pins?\s+|gpio\s+)?(\d+)", lower)
        if line_cfg_match:
            p_left = int(line_cfg_match.group(1))
            p_right = int(line_cfg_match.group(2))
            memory_vault.set_pin_role(str(p_left), "LINE_LEFT", "Line Follower Left Sensor")
            memory_vault.set_pin_role(str(p_right), "LINE_RIGHT", "Line Follower Right Sensor")
            memory_vault.set_line_follower_config(True, p_left, p_right, 140)
            return f"Configured and activated autonomous line follower using Left Pin {p_left} and Right Pin {p_right}! Rolling out!", {
                "type": "line_follower", "enable": True, "left_pin": p_left, "right_pin": p_right, "speed": 140
            }

        # Line Follower Start / Stop toggles
        if re.search(r"\b(start|enable|run|resume)\s+line\s+follow(?:ing|er)?\b", lower):
            cfg = memory_vault.get_line_follower_config()
            p_left = cfg.get("left_pin", 2)
            p_right = cfg.get("right_pin", 3)
            spd = cfg.get("speed", 140)
            memory_vault.set_line_follower_config(True, p_left, p_right, spd)
            return f"Autonomous Line Follower ENGAGED on Left Pin {p_left} & Right Pin {p_right}! Tracking path now!", {
                "type": "line_follower", "enable": True, "left_pin": p_left, "right_pin": p_right, "speed": spd
            }

        if re.search(r"\b(stop|disable|halt|pause)\s+line\s+follow(?:ing|er)?\b", lower):
            cfg = memory_vault.get_line_follower_config()
            memory_vault.set_line_follower_config(False, cfg.get("left_pin", 2), cfg.get("right_pin", 3), cfg.get("speed", 140))
            return "Line Follower HALTED! Standing by, Orbit!", {
                "type": "line_follower", "enable": False
            }

        # 4. Built-in Servos Shortcuts
        if "perk" in lower and "ear" in lower:
            return "Perking up my radar ears! Listening closely, Orbit!", {"type": "servos", "preset": "perk_ears"}
        if "wag" in lower and "tail" in lower:
            return "Wagging my celestial tail! Daebak!", {"type": "servos", "preset": "wag_tail"}
        if "tilt" in lower and ("head" in lower or "curious" in lower):
            return "Curious head tilt! What are we exploring next, Orbit?", {"type": "servos", "preset": "curious_tilt"}

        # 3. Memory & Face saving shortcuts
        face_save_match = re.search(r"(?:save|remember)\s+(?:this\s+)?face\s+(?:as\s+)?([a-zA-Z0-9_\s]+)", lower)
        if face_save_match:
            name = face_save_match.group(1).strip().title()
            memory_vault.save_face(name)
            return f"Face profile saved for '{name}'! I will always recognize you, my Orbit!", {"type": "save_face", "name": name}

        note_save_match = re.search(r"remember\s+that\s+([a-zA-Z0-9_\s]+)\s+is\s+([a-zA-Z0-9_\s]+)", lower)
        if note_save_match:
            k = note_save_match.group(1).strip()
            v = note_save_match.group(2).strip()
            memory_vault.save_note(k, v)
            return f"Noted and saved into my Operative Vault! '{k}' is '{v}'.", {"type": "save_note", "key": k, "value": v}

        # 4. Check for custom user saved macros in vault
        saved_macro = memory_vault.find_command(lower)
        if saved_macro:
            desc = saved_macro.get("desc", "Executing custom command.")
            return f"Executing macro '{saved_macro['trigger']}': {desc}", {"type": "macro", "actions": saved_macro.get("actions", [])}

        # 5. Music & Song Search - Play ANY song immediately
        if lower.startswith("play ") or " play " in lower or ("play" in lower and ("song" in lower or "music" in lower or "track" in lower or "spotify" in lower)):
            query = re.sub(r"^(hey\s+)?(loona\s+)?(please\s+)?play\s+", "", lower, flags=re.IGNORECASE).strip()
            query = re.sub(r"\b(on\s+spotify|on\s+the\s+speaker|on\s+my\s+speaker|song|music|please)\b", "", query, flags=re.IGNORECASE).strip()
            if not query:
                query = "LOONA Hi High"
            return f"Playing '{query}' on my speaker right now for you, Orbit! 🎵", {"type": "spotify_play", "query": query}
        elif "pause" in lower and ("music" in lower or "spotify" in lower or "song" in lower):
            return "Pausing speaker audio now, Orbit!", {"type": "spotify_pause"}
        elif "resume" in lower and ("music" in lower or "spotify" in lower or "song" in lower):
            return "Resuming music through my speaker, Orbit! ✨", {"type": "spotify_resume"}
        elif "next" in lower and ("song" in lower or "track" in lower or "music" in lower):
            return "Skipping to the next track! 🎶", {"type": "spotify_next"}
        elif "spin" in lower or "orbit" in lower:
            return "Hi High, Orbit! Celestial 360 orbit spin initiated! Wheee~", {"type": "orbit_spin"}
        elif "dance" in lower or "choreography" in lower or "wiggle" in lower:
            return "Fly like a butterfly! Watch my Project L.O.O.N.A. choreography!", {"type": "kpop_dance"}
        elif "forward" in lower or "drive" in lower:
            return "Rolling forward across our lunar path, Orbit!", {"type": "drive", "fwd": 180, "turn": 0, "duration": 1.2}
        elif "back" in lower or "reverse" in lower:
            return "Lunar reverse engaged! Beep beep~", {"type": "drive", "fwd": -180, "turn": 0, "duration": 1.0}
        elif "happy" in lower:
            return "Daebak! Sparkling like the Moon tonight! Look at my happy eyes!", {"type": "set_emotion", "emotion": "happy"}

        # 6. Photography & Snapshot Camera Shortcut:
        # e.g., "take a picture", "take a photo", "snap a photo", "take a selfie", "capture image"
        if re.search(r"\b(take|snap|capture)\s+(?:a\s+)?(?:picture|photo|pic|snapshot|selfie|image)\b", lower) or "say cheese" in lower:
            return "Say cheese, Orbit! 📸 *Click!* Picture captured and saved to your Operative Gallery! ✨", {"type": "take_picture"}

        # 7. Optical Object Detection & Recognition Shortcut:
        # e.g., "detect objects", "what objects do you see", "what is this", "scan objects"
        if re.search(r"\b(?:detect\s+objects?|what\s+(?:objects?\s+)?(?:do\s+you\s+see|is\s+this|are\s+these)|scan\s+objects?)\b", lower):
            return "Optical gaze scanning for objects! Highlighting detected items with targeting boxes! 🔍", {"type": "detect_objects"}

        # 8. Autonomous Idle Roam & Collision Avoidance Shortcuts:
        # e.g., "start roaming", "roam around", "wander around", "explore", "stop roaming", "disable roaming"
        if re.search(r"\b(stop|disable|halt|turn\s+off|cancel)\s+(?:the\s+)?(roam(?:ing)?|wander(?:ing)?|explore|idle\s+roam)\b", lower):
            return "Autonomous roaming stopped! Standing by, Orbit!", {"type": "roam", "enable": False}

        if re.search(r"\b(start|enable|run|turn\s+on)?\s*(roam(?:ing)?\s+around|wander(?:ing)?\s+around|idle\s+roam|roam\s+mode)\b", lower) or lower in ("roam", "wander", "explore", "start roaming", "roam around"):
            return "Autonomous idle roaming engaged! Exploring safely and avoiding obstacles, Orbit! 🐾", {"type": "roam", "enable": True}

        return None

    async def generate_response(self, prompt_text: str, image_bytes: Optional[bytes] = None) -> Tuple[str, Optional[dict]]:
        """
        Coordinates user prompt reasoning with memory injection and model cascading.
        Returns: (spoken_text, action_dict)
        """
        # 1. Check local shortcuts for instant zero-latency hardware actuation
        local_result = self.check_local_shortcuts(prompt_text)
        if local_result:
            return local_result

        # 2. If no Gemini API key configured, provide friendly offline response
        if not self.api_key or not GEMINI_AVAILABLE:
            await asyncio.sleep(0.3)
            return f"Annyeong, Orbit! I heard you say: '{prompt_text}'! Ready to explore together!", None

        # 3. Online Gemini Multimodal Reasoning with Model Cascading
        # Build prompt with persistent memories
        vault_context = memory_vault.get_context_for_prompt()
        system_instruction = LOONA_BASE_SYSTEM_PROMPT
        if vault_context:
            system_instruction += f"\n\nCURRENT OPERATIVE MEMORY:\n{vault_context}"

        contents = []
        if image_bytes is not None:
            try:
                from PIL import Image
                image = Image.open(io.BytesIO(image_bytes))
                contents.append(image)
            except Exception:
                pass

        # Build context from recent turns
        context_summary = ""
        if len(self.conversation_history) > 0:
            recent = self.conversation_history[-4:]
            context_summary = "Recent chat:\n" + "\n".join([f"{item['role']}: {item['text']}" for item in recent]) + "\n"

        contents.append(
            f"{context_summary}Orbit asks: '{prompt_text}'\n"
            "Respond in character as Project L.O.O.N.A. (1-2 sentences with action tag if applicable):"
        )

        loop = asyncio.get_running_loop()

        for model_candidate in self.models_to_try:
            try:
                import google.generativeai as genai
                model_inst = genai.GenerativeModel(
                    model_name=model_candidate,
                    system_instruction=system_instruction
                )

                response = await loop.run_in_executor(
                    None,
                    lambda: model_inst.generate_content(contents)
                )

                if response and response.text:
                    raw_text = response.text.strip()
                    speech_text, action = extract_actions_and_clean_text(raw_text)
                    
                    # Update conversational history
                    self.conversation_history.append({"role": "Orbit", "text": prompt_text})
                    self.conversation_history.append({"role": "L.O.O.N.A.", "text": speech_text})
                    if len(self.conversation_history) > 12:
                        self.conversation_history = self.conversation_history[-12:]

                    return speech_text, action

            except Exception as e:
                print(f"[AI] Model '{model_candidate}' error ({e}). Trying next fallback candidate...")

        # If all online models exhausted or network down, return lively idol response
        return f"Annyeong, Orbit! I heard: '{prompt_text}'. All my locomotive and optical systems are ready for you!", None


from collections import deque

class STTService:
    """High-sensitivity audio speech-to-text service with clean PCM processing, gentle AGC normalization, and robust VAD."""
    def __init__(self):
        self.is_recording = False
        self.audio_buffer = bytearray()
        self.pre_roll = deque(maxlen=6)  # Stores ~200ms pre-speech audio to prevent clipping word start
        self.silence_counter = 0
        self.noise_floor = 30.0
        self.is_robot_speaking = False

    def set_robot_speaking(self, speaking: bool):
        """Suppresses mic recognition while LOONA is actively speaking or playing music to prevent echo."""
        self.is_robot_speaking = speaking
        if speaking:
            self.is_recording = False
            self.audio_buffer.clear()
            self.pre_roll.clear()
            self.silence_counter = 0

    async def process_pcm_chunk(self, chunk: bytes) -> Optional[str]:
        """Processes raw 16kHz Mono PCM from INMP441 mic with clean, undistorted VAD and asynchronous recognition."""
        if len(chunk) < 2 or self.is_robot_speaking:
            return None

        # Calculate RMS energy directly on raw PCM
        try:
            import audioop
            rms = audioop.rms(chunk, 2)
        except Exception:
            import numpy as np
            samples = np.frombuffer(chunk, dtype=np.int16)
            rms = int(np.sqrt(np.mean(samples.astype(np.float32)**2)))

        # Adaptive background noise floor tracking (exponential moving average)
        if not self.is_recording:
            self.noise_floor = self.noise_floor * 0.94 + min(rms, 400) * 0.06
            self.pre_roll.append(chunk)

        # High-sensitivity dynamic voice threshold (picks up natural speaking voice easily)
        dynamic_threshold = max(55, int(self.noise_floor * 1.25))

        if rms > dynamic_threshold:
            if not self.is_recording:
                self.is_recording = True
                # Prepend pre-roll buffer so the start of the first word is never clipped
                for pre in self.pre_roll:
                    self.audio_buffer.extend(pre)
                self.pre_roll.clear()
            self.audio_buffer.extend(chunk)
            self.silence_counter = 0
        elif self.is_recording:
            self.audio_buffer.extend(chunk)
            self.silence_counter += 1
            
            # After ~0.45s of silence (approx 14 chunks @ 512-1024 bytes 16kHz)
            if self.silence_counter > 14:
                self.is_recording = False
                captured_bytes = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                self.silence_counter = 0

                # Clean linear audio normalization: scale captured voice gently to ~20,000 peak (no clipping)
                if len(captured_bytes) > 2000 and SR_AVAILABLE:
                    try:
                        import numpy as np
                        samples = np.frombuffer(captured_bytes, dtype=np.int16).astype(np.float32)
                        peak = float(np.max(np.abs(samples)))
                        if peak > 25.0:
                            norm_gain = min(4.0, 20000.0 / peak)
                            normalized_samples = np.clip(samples * norm_gain, -32768, 32767).astype(np.int16)
                            final_audio_bytes = normalized_samples.tobytes()
                        else:
                            final_audio_bytes = captured_bytes

                        recognizer = sr.Recognizer()
                        recognizer.energy_threshold = max(50, int(self.noise_floor))
                        recognizer.dynamic_energy_threshold = False
                        audio_data = sr.AudioData(final_audio_bytes, sample_rate=16000, sample_width=2)
                        
                        # Run Google Speech Recognition asynchronously without blocking event loop
                        loop = asyncio.get_running_loop()
                        text = await loop.run_in_executor(None, recognizer.recognize_google, audio_data)
                        if text:
                            print(f"[STT] Live Microphone Recognized: '{text}'")
                            return text.strip()
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"[STT] Recognition notice: {e}")

        return None

    async def transcribe_audio_blob(self, audio_bytes: bytes) -> Optional[str]:
        """Transcodes recorded audio from smartphone/browser mic into 16kHz WAV and runs STT."""
        if not audio_bytes or not SR_AVAILABLE:
            return None
        try:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", "pipe:0",
                "-f", "wav", "-ar", "16000", "-ac", "1",
                "pipe:1"
            ]
            loop = asyncio.get_running_loop()
            def run_ffmpeg():
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, _ = proc.communicate(input=audio_bytes)
                return out if proc.returncode == 0 else b""

            wav_bytes = await loop.run_in_executor(None, run_ffmpeg)
            if not wav_bytes:
                return None

            recognizer = sr.Recognizer()
            with io.BytesIO(wav_bytes) as audio_file:
                with sr.AudioFile(audio_file) as source:
                    audio_data = recognizer.record(source)

            text = await loop.run_in_executor(None, recognizer.recognize_google, audio_data)
            if text:
                print(f"[STT-PHONE] Phone Mic Recognized: '{text}'")
                return text.strip()
        except Exception as e:
            print(f"[STT-PHONE] Phone mic transcription notice: {e}")
        return None


def parse_voice_command(text: str) -> Optional[str]:
    """
    Parses voice text for high-priority robot control protocols.
    Returns: 'FOLLOW_ME', 'STOP', or None (pass to Gemini).
    """
    cleaned = text.lower().strip()

    follow_pattern = r"\b(hey\s+)?(loona\s+)?(please\s+)?(follow\s+me|track\s+me|follow\s+my\s+face|chase\s+me)\b"
    if re.search(follow_pattern, cleaned):
        return "FOLLOW_ME"

    roam_stop_pattern = r"\b(hey\s+)?(loona\s+)?(stop\s+roaming|stop\s+wandering|stop\s+exploring)\b"
    if re.search(roam_stop_pattern, cleaned):
        return "STOP_ROAM"

    stop_pattern = r"\b(hey\s+)?(loona\s+)?(stop(\s+following(\s+me)?)?|stay|halt|freeze|pause)\b"
    if re.search(stop_pattern, cleaned):
        return "STOP"

    roam_pattern = r"\b(hey\s+)?(loona\s+)?(please\s+)?(start\s+roaming|roam\s+around|wander\s+around|explore\s+around|explore|idle\s+roam)\b"
    if re.search(roam_pattern, cleaned):
        return "START_ROAM"

    return None

ai_engine = AIService()
stt_engine = STTService()
