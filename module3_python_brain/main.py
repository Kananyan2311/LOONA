import os
import sys
import json
import socket
import asyncio
import time
import re
import wave
import io
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure bundled ffmpeg binary from imageio-ffmpeg is on PATH for pydub/audio libraries
try:
    import imageio_ffmpeg
    ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from typing import Set, Optional, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response, FileResponse

from config import config
from vision_tracker import VisionTracker
from tts_service import tts_engine
from ai_service import ai_engine, stt_engine, parse_voice_command
from spotify_service import spotify_service
from memory_service import memory_vault
from roam_service import roam_service

# Initialize FastAPI App
app = FastAPI(title="Project L.O.O.N.A. Brain Server", version="2.0.0")

# Vision Tracker Service
tracker = VisionTracker()

# Connected Web Clients & ESP32 Audio Socket
connected_web_clients: Set[WebSocket] = set()
esp32_audio_socket: Optional[WebSocket] = None

# INMP441 Robot Microphone Live Activity & Testing State
inmp_mic_state = {
    "connected": False,
    "last_seen": 0.0,
    "rms": 0.0,
    "peak": 0
}
inmp_test_recording_active = False
inmp_test_recording_buffer = bytearray()

# Global Robot Operational State
robot_state = {
    "project": config.PROJECT_NAME,
    "mode": "companion",       # "companion" (face tracking) or "manual" (virtual joystick)
    "emotion": "neutral",      # "neutral", "happy", "thinking", "speaking"
    "following": False,        # True when active 4WD face-following protocol is engaged
    "roam_mode": False,        # True when autonomous idle roaming & collision avoidance is engaged
    "manual_cmd": {"fwd": 0, "turn": 0},
    "servos": list(config.SERVO_DEFAULTS),  # [Pan, Tilt, LeftEar, RightEar, Tail]
    "pins": {str(p): 0 for p in config.EXPANSION_PINS}  # State of expansion GPIOs
}

# Queued immediate hardware pin commands
pending_pin_commands: List[Dict[str, Any]] = []

# UDP Socket for Motor, Servo & Expansion Commands to Head MCU (relayed to Chassis MCU)
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Resolve path to WebApp index.html
WEBAPP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "module4_webapp"))
INDEX_HTML_PATH = os.path.join(WEBAPP_DIR, "index.html")

# ============================================================================
# HTTP & REST API ROUTES
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the Project L.O.O.N.A. Cyber Eyes & Companion WebApp."""
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>index.html not found in module4_webapp directory.</h3>")

@app.get("/favicon.ico")
async def favicon():
    """Returns LOONA icon to eliminate browser 404 favicon logs."""
    svg_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="46" fill="#081682"/>'
        '<circle cx="46" cy="46" r="42" fill="#35e3f2"/>'
        '<circle cx="38" cy="36" r="14" fill="#ffffff"/>'
        '<text x="56" y="74" font-size="30" fill="#ffe600">★</text>'
        '</svg>'
    )
    return Response(content=svg_icon, media_type="image/svg+xml")

@app.get("/video_feed")
async def video_feed():
    """Provides a live MJPEG stream with OpenCV face tracking & identity overlay."""
    async def frame_generator():
        while True:
            jpeg = tracker.get_latest_jpeg()
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            await asyncio.sleep(0.04)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

def get_lan_ip() -> str:
    """Discovers the primary local LAN IP address on Wi-Fi / Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

@app.get("/api/network_info")
async def get_network_info():
    """Returns local host and LAN URL so mobile devices on same Wi-Fi can connect easily."""
    lan_ip = get_lan_ip()
    port = config.SERVER_PORT
    return JSONResponse({
        "status": "ok",
        "lan_ip": lan_ip,
        "port": port,
        "local_url": f"http://localhost:{port}/",
        "lan_url": f"http://{lan_ip}:{port}/"
    })

@app.get("/api/memory")
async def get_memory_vault():
    """Returns all saved faces, commands, notes, and expansion pin labels."""
    return JSONResponse(memory_vault.memory)

@app.get("/api/database/stats")
async def get_database_stats_api():
    """Returns SQLite3 database engine statistics, file path, and table row counts."""
    return JSONResponse(memory_vault.get_db_stats())

@app.get("/api/database/chats")
async def get_database_chats_api(limit: int = 50):
    """Returns persistent conversation history stored in SQLite3."""
    return JSONResponse({"chats": memory_vault.get_recent_chats(limit)})

@app.post("/api/memory/face")
async def save_face_api(req: Request):
    """Saves a new face identity."""
    data = await req.json()
    name = data.get("name", "Orbit")
    role = data.get("role", "Friend / Orbit")
    res = tracker.save_current_face(name)
    asyncio.create_task(broadcast_vault_update())
    return JSONResponse(res)

@app.post("/api/memory/note")
async def save_note_api(req: Request):
    """Saves a user note / memory."""
    data = await req.json()
    res = memory_vault.save_note(data.get("key", ""), data.get("value", ""))
    asyncio.create_task(broadcast_vault_update())
    return JSONResponse(res)

@app.post("/api/memory/command")
async def save_command_api(req: Request):
    """Saves a custom user macro command."""
    data = await req.json()
    res = memory_vault.save_command(data.get("trigger", ""), data.get("actions", []), data.get("desc", ""))
    asyncio.create_task(broadcast_vault_update())
    return JSONResponse(res)

@app.post("/api/memory/delete")
async def delete_memory_api(req: Request):
    """Deletes an item from memory vault."""
    data = await req.json()
    cat = data.get("category")
    item_id = data.get("id")
    if cat == "face":
        memory_vault.delete_face(item_id)
    elif cat == "command":
        memory_vault.delete_command(item_id)
    elif cat == "note":
        memory_vault.delete_note(item_id)
    elif cat == "pin_role":
        memory_vault.delete_pin_role(item_id)
    asyncio.create_task(broadcast_vault_update())
    return JSONResponse({"status": "deleted"})

# ============================================================================
# CAMERA SNAPSHOT & PHOTO GALLERY REST ENDPOINTS
# ============================================================================
@app.post("/api/camera/capture")
async def capture_photo_api(req: Request = None):
    """Takes a high-res snapshot from LOONA's camera and registers in SQLite3."""
    overlay = False
    notes = "User snapshot"
    if req:
        try:
            body = await req.json()
            overlay = bool(body.get("overlay", False))
            notes = str(body.get("notes", "User snapshot"))
        except Exception:
            pass

    photo = tracker.capture_snapshot(with_overlay=overlay, notes=notes)
    
    # Broadcast event to WebApp clients for instant UI preview & flash effect
    payload = json.dumps({"type": "photo_captured", "photo": photo, "filename": photo.get("filename")})
    for c in list(connected_web_clients):
        try:
            await c.send_text(payload)
        except Exception:
            pass

    return JSONResponse({"status": "ok", "photo": photo, "filename": photo.get("filename")})

@app.get("/api/camera/gallery")
async def get_photo_gallery_api():
    """Returns list of all photos saved in the SQLite3 gallery."""
    photos = memory_vault.get_photos()
    return JSONResponse({"photos": photos})

@app.get("/api/camera/photo/{filename}")
async def get_photo_file_api(filename: str):
    """Serves the JPEG photo image file from the captures directory."""
    from vision_tracker import CAPTURES_DIR
    filepath = os.path.join(CAPTURES_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="image/jpeg")
    return Response(status_code=404, content="Photo not found")

@app.delete("/api/camera/photo/{filename}")
async def delete_photo_api(filename: str):
    """Deletes a photo from disk and SQLite3 database."""
    from vision_tracker import CAPTURES_DIR
    filepath = os.path.join(CAPTURES_DIR, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    memory_vault.delete_photo(filename)
    return JSONResponse({"status": "deleted", "filename": filename})

@app.post("/api/camera/detection_mode")
async def set_detection_mode_api(req: Request):
    """Switches detection mode between 'all', 'faces', and 'objects'."""
    data = await req.json()
    mode = data.get("mode", "all")
    tracker.set_detection_mode(mode)
    return JSONResponse({"status": "ok", "detection_mode": mode})

@app.get("/api/camera/source")
async def get_camera_source_api():
    """Returns the active camera input source: 'esp32', 'browser', or 'host_usb'."""
    return JSONResponse({"source": tracker.get_camera_source()})

@app.post("/api/camera/source")
async def set_camera_source_api(req: Request):
    """Switches active camera input source between ESP32-CAM, Browser WebCam, or Host USB."""
    data = await req.json()
    source = data.get("source", "esp32")
    active_source = tracker.set_camera_source(source)
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({
                "type": "camera_source_update",
                "source": active_source
            }))
        except Exception:
            pass
    return JSONResponse({"status": "ok", "source": active_source})

@app.post("/api/camera/frame")
async def post_camera_frame_api(request: Request):
    """Receives a raw JPEG frame from the browser webcam and feeds it into the tracker."""
    body = await request.body()
    if body:
        ok = tracker.feed_external_jpeg(body)
        return JSONResponse({"status": "ok" if ok else "error"})
    return JSONResponse({"status": "empty"}, status_code=400)

@app.get("/api/spotify/status")
async def get_spotify_status_api():
    """Returns current music playback track info and status."""
    return JSONResponse(spotify_service.current_track_info)

@app.post("/api/spotify/play")
async def post_spotify_play_api(req: Request):
    """Searches and streams ANY requested song through MAX98357A speaker."""
    data = await req.json()
    query = data.get("query", "LOONA Hi High")

    async def send_audio_cb(pcm_chunk):
        if esp32_audio_socket:
            await esp32_audio_socket.send_bytes(pcm_chunk)

    async def notify_spk_cb(track_info):
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({"type": "spotify_update", "data": track_info}))
            except Exception:
                pass

    stt_engine.set_robot_speaking(True)
    res = spotify_service.play(query, send_audio_cb, notify_spk_cb)
    return JSONResponse({"status": "playing", "track": res})

@app.post("/api/spotify/pause")
async def post_spotify_pause_api():
    """Pauses music playback."""
    res = spotify_service.pause()
    stt_engine.set_robot_speaking(False)
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({"type": "spotify_update", "data": res}))
        except Exception:
            pass
    return JSONResponse(res)

@app.post("/api/spotify/resume")
async def post_spotify_resume_api():
    """Resumes music playback."""
    async def send_audio_cb(pcm_chunk):
        if esp32_audio_socket:
            await esp32_audio_socket.send_bytes(pcm_chunk)

    async def notify_spk_cb(track_info):
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({"type": "spotify_update", "data": track_info}))
            except Exception:
                pass

    stt_engine.set_robot_speaking(True)
    res = spotify_service.resume(send_audio_cb, notify_spk_cb)
    return JSONResponse(res)

# ============================================================================
# DYNAMIC SENTENCE-SIZE SUBTITLES & WEB DISPLAY REST API
# ============================================================================
latest_subtitle = {"text": "Project L.O.O.N.A. Ready!", "duration": 4000, "timestamp": time.time()}

def calculate_subtitle_duration_ms(text: str) -> int:
    """Calculates dynamic subtitle hold/fade duration proportional to sentence size."""
    clean = re.sub(r"[*_#`]", "", str(text)).strip()
    char_len = len(clean)
    word_count = len(clean.split())
    # Shorter sentences fade faster; longer sentences stay proportionally longer
    return int(max(2500, min(16000, 1000 + (word_count * 360) + (char_len * 45))))

@app.post("/api/subtitles")
async def post_subtitles_api(req: Request):
    """Displays dynamic sentence-size subtitles on web server HUD and optionally speaks via natural K-Pop voice."""
    global latest_subtitle
    data = await req.json()
    text = str(data.get("text", "")).strip()
    if not text:
        return JSONResponse({"status": "error", "message": "Text is required"}, status_code=400)
    
    explicit_duration = data.get("duration")
    duration_ms = int(explicit_duration) if explicit_duration is not None else calculate_subtitle_duration_ms(text)
    speak = bool(data.get("speak", False))

    latest_subtitle = {
        "text": text,
        "duration": duration_ms,
        "timestamp": time.time()
    }

    # Broadcast subtitle event to all connected WebApp clients
    payload = json.dumps({
        "type": "subtitles",
        "text": text,
        "duration": duration_ms
    })
    for c in list(connected_web_clients):
        try:
            await c.send_text(payload)
        except Exception:
            pass

    if speak:
        asyncio.create_task(speak_notification(text))

    return JSONResponse({"status": "ok", "text": text, "duration": duration_ms, "spoken": speak})

@app.get("/api/subtitles")
async def get_subtitles_api():
    """Returns the most recent subtitle and its active duration."""
    return JSONResponse({"status": "ok", "subtitles": latest_subtitle})

@app.get("/api/tts/audio")
async def get_tts_audio_api(text: str = ""):
    """Returns high-quality MP3 audio of LOONA speaking for phone and browser speaker playback."""
    clean = text.strip()
    if not clean:
        return Response(status_code=400, content="Text parameter required")
    mp3_bytes = await tts_engine.text_to_mp3(clean)
    if mp3_bytes:
        return Response(content=mp3_bytes, media_type="audio/mpeg")
    return Response(status_code=500, content="TTS synthesis failed")

@app.post("/api/phone/audio")
async def post_phone_audio_api(request: Request):
    """Receives recorded voice audio from smartphone / browser mic and executes as chat command."""
    body = await request.body()
    if not body:
        return JSONResponse({"status": "error", "message": "Empty audio data"}, status_code=400)
    
    recognized_text = await stt_engine.transcribe_audio_blob(body)
    if recognized_text:
        # Broadcast user spoken text to all connected WebApp clients
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "chat_user",
                    "text": recognized_text
                }))
            except Exception:
                pass
        
        # Trigger full chat reasoning and robot/phone speech response
        asyncio.create_task(handle_chat_query(recognized_text))
        return JSONResponse({"status": "ok", "text": recognized_text})
    
    return JSONResponse({"status": "no_speech", "message": "Could not recognize audio"}, status_code=200)

@app.post("/api/roam")
async def set_roam_api(req: Request):
    """Enables or disables autonomous idle roaming & obstacle/people avoidance."""
    data = await req.json()
    enable = bool(data.get("enabled", True))
    roam_service.set_enabled(enable)
    robot_state["roam_mode"] = enable
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({
                "type": "roam_update",
                "enabled": enable,
                "state": roam_service.state
            }))
        except Exception:
            pass
    return JSONResponse({"status": "ok", "roam_enabled": enable, "roam_state": roam_service.state})

@app.get("/api/roam")
async def get_roam_api():
    """Returns current roaming telemetry & status."""
    return JSONResponse(roam_service.get_status())

@app.post("/api/servos")
async def set_servos_api(req: Request):
    """Direct manual servo position update."""
    data = await req.json()
    angles = data.get("servos", robot_state["servos"])
    await apply_servo_angles(angles)
    return JSONResponse({"status": "ok", "servos": robot_state["servos"]})

@app.post("/api/custom_servo")
async def set_custom_servo_api(req: Request):
    """Actuates custom servo on specified GPIO pin."""
    data = await req.json()
    pin = int(data.get("pin", 21))
    angle = int(data.get("angle", 90))
    await trigger_custom_servo(pin, angle)
    return JSONResponse({"status": "ok", "pin": pin, "angle": angle})

@app.post("/api/line_follower")
async def set_line_follower_api(req: Request):
    """Configures and activates autonomous line follower."""
    data = await req.json()
    enable = bool(data.get("enable", True))
    l_pin = int(data.get("left_pin", 2))
    r_pin = int(data.get("right_pin", 3))
    spd = int(data.get("speed", 140))
    inv = bool(data.get("invert", False))
    await trigger_line_follower(enable, l_pin, r_pin, spd, inv)
    return JSONResponse({"status": "ok", "enabled": enable, "left_pin": l_pin, "right_pin": r_pin})

@app.post("/api/pin_role")
async def set_pin_role_api(req: Request):
    """Customizes expansion pin role (SERVO, LINE_LEFT, LINE_RIGHT, OUTPUT, PWM, INPUT)."""
    data = await req.json()
    pin = str(data.get("pin", 2))
    role = str(data.get("role", "OUTPUT"))
    label = str(data.get("label", ""))
    res = memory_vault.set_pin_role(pin, role, label)
    await broadcast_vault_update()
    return JSONResponse(res)

async def broadcast_vault_update():
    """Broadcasts updated memory vault to all connected browsers."""
    payload = json.dumps({"type": "vault_update", "data": memory_vault.memory})
    for c in list(connected_web_clients):
        try:
            await c.send_text(payload)
        except Exception:
            pass

# ============================================================================
# WEBSOCKET: SMARTPHONE / BROWSER DASHBOARD (/ws/client)
# ============================================================================
@app.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    """Bidirectional link to smartphone/browser client."""
    await websocket.accept()
    connected_web_clients.add(websocket)
    print(f"[WS-CLIENT] WebApp client connected. Total clients: {len(connected_web_clients)}")

    # Send initial vault state
    try:
        await websocket.send_text(json.dumps({"type": "vault_update", "data": memory_vault.memory}))
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                
                # 1. Mode switch
                if "mode" in msg:
                    robot_state["mode"] = msg["mode"]
                    if msg["mode"] == "companion":
                        robot_state["emotion"] = "neutral"
                    elif msg["mode"] == "manual":
                        robot_state["following"] = False

                # 2. Action trigger from UI
                if "roam" in msg:
                    enable = bool(msg["roam"])
                    roam_service.set_enabled(enable)
                    robot_state["roam_mode"] = enable
                    for c in list(connected_web_clients):
                        try:
                            await c.send_text(json.dumps({
                                "type": "roam_update",
                                "enabled": enable,
                                "state": roam_service.state
                            }))
                        except Exception:
                            pass

                if "action" in msg:
                    if msg["action"] == "follow":
                        robot_state["mode"] = "companion"
                        robot_state["following"] = True
                        robot_state["emotion"] = "happy"
                        asyncio.create_task(speak_notification("Target locked! Following you now, Orbit!"))
                    elif msg["action"] == "stop_following":
                        robot_state["following"] = False
                        robot_state["emotion"] = "neutral"
                        asyncio.create_task(speak_notification("Stopped following. Standing by!"))
                    elif msg["action"] == "roam":
                        roam_service.set_enabled(True)
                        robot_state["roam_mode"] = True
                        asyncio.create_task(speak_notification("Autonomous roam engaged! Exploring and keeping watch, Orbit! 🐾"))
                    elif msg["action"] == "stop_roam":
                        roam_service.set_enabled(False)
                        robot_state["roam_mode"] = False
                        asyncio.create_task(speak_notification("Stopped roaming. Standing by!"))

                # 3. Manual Drive Command
                if "cmd" in msg and robot_state["mode"] == "manual":
                    robot_state["manual_cmd"]["fwd"] = int(msg["cmd"].get("fwd", 0))
                    robot_state["manual_cmd"]["turn"] = int(msg["cmd"].get("turn", 0))

                # 4. Servos Command from UI Sliders
                if "servos" in msg:
                    await apply_servo_angles(msg["servos"])

                # 5. Expansion GPIO Command from UI
                if "pin_cmd" in msg:
                    p = msg["pin_cmd"]
                    await trigger_pin_control(int(p["pin"]), p.get("state", "LOW"), p.get("pwm", -1))

                # 5b. Dynamic Custom Servo Command from UI
                if "custom_servo" in msg:
                    cs = msg["custom_servo"]
                    await trigger_custom_servo(int(cs["pin"]), int(cs.get("angle", 90)))

                # 5c. Line Follower Toggle from UI
                if "line_follower" in msg:
                    lf = msg["line_follower"]
                    await trigger_line_follower(
                        bool(lf.get("enable", True)),
                        int(lf.get("left_pin", 2)),
                        int(lf.get("right_pin", 3)),
                        int(lf.get("speed", 140)),
                        bool(lf.get("invert", False))
                    )

                # 5d. Custom Pin Role Assignment from UI
                if "pin_role" in msg:
                    pr = msg["pin_role"]
                    memory_vault.set_pin_role(str(pr["pin"]), str(pr.get("role", "OUTPUT")), str(pr.get("label", "")))
                    await broadcast_vault_update()

                # 6. Direct Chat query from WebApp
                if "query" in msg:
                    asyncio.create_task(handle_chat_query(msg["query"]))

                # 7. Voice Preset Switch
                if "voice_preset" in msg:
                    tts_engine.set_preset(msg["voice_preset"])
                    asyncio.create_task(speak_notification("Voice preset updated, Orbit! ✨"))

                # 8. Emotion Override
                if "emotion" in msg:
                    robot_state["emotion"] = msg["emotion"]

                # 9. Spotify WebApp Controller
                if "spotify_cmd" in msg:
                    cmd = msg["spotify_cmd"]
                    async def send_audio_cb(pcm_chunk):
                        if esp32_audio_socket:
                            await esp32_audio_socket.send_bytes(pcm_chunk)
                    async def notify_spk_cb(track_info):
                        for c in list(connected_web_clients):
                            try:
                                await c.send_text(json.dumps({"type": "spotify_update", "data": track_info}))
                            except Exception:
                                pass

                    if cmd == "play":
                        res = spotify_service.play(msg.get("query", "LOONA Hi High"), send_audio_cb, notify_spk_cb)
                    elif cmd == "pause":
                        res = spotify_service.pause()
                    elif cmd == "resume":
                        res = spotify_service.resume(send_audio_cb, notify_spk_cb)
                    elif cmd == "next":
                        res = spotify_service.next_track()
                    elif cmd == "prev":
                        res = spotify_service.previous_track()
                    else:
                        res = {}
                    await notify_spk_cb(res)

                # 10. Camera Source Switch from WebApp
                if "camera_source" in msg:
                    src = msg["camera_source"]
                    active_src = tracker.set_camera_source(src)
                    for c in list(connected_web_clients):
                        try:
                            await c.send_text(json.dumps({
                                "type": "camera_source_update",
                                "source": active_src
                            }))
                        except Exception:
                            pass

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        connected_web_clients.remove(websocket)
        print(f"[WS-CLIENT] WebApp client disconnected. Remaining: {len(connected_web_clients)}")

# ============================================================================
# WEBSOCKET: BROWSER WEBCAM STREAMING LINK (/ws/camera_feed)
# ============================================================================
@app.websocket("/ws/camera_feed")
async def websocket_camera_feed_endpoint(websocket: WebSocket):
    """High-speed binary WebSocket endpoint for WebApp browser webcam frame ingestion."""
    await websocket.accept()
    tracker.set_camera_source("browser")
    print("[WS-CAM] Browser WebCam streaming channel connected.")
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                tracker.feed_external_jpeg(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    if "image" in payload:
                        import base64
                        b64_str = payload["image"]
                        if "," in b64_str:
                            b64_str = b64_str.split(",", 1)[1]
                        tracker.feed_external_jpeg(base64.b64decode(b64_str))
                except Exception:
                    pass
    except WebSocketDisconnect:
        print("[WS-CAM] Browser WebCam streaming channel disconnected.")
    except Exception as e:
        print(f"[WS-CAM] WebSocket error: {e}")

# ============================================================================
# WEBSOCKET: ESP32-S3 HEAD AUDIO LINK (/ws/audio)
# ============================================================================
@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """Bidirectional raw PCM audio link with Head Controller (ESP32-S3 CAM)."""
    global esp32_audio_socket, inmp_test_recording_active, inmp_test_recording_buffer
    await websocket.accept()
    esp32_audio_socket = websocket
    inmp_mic_state["connected"] = True
    inmp_mic_state["last_seen"] = time.time()
    print("[WS-AUDIO] Head ESP32-S3 CAM connected for live INMP441 mic RX & MAX98357A speaker TX.")

    try:
        while True:
            # Receive raw 16kHz 16-bit PCM bytes or control frames from INMP441 MEMS microphone
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            pcm_chunk = message.get("bytes")
            if not pcm_chunk:
                continue

            # Update live signal telemetry
            inmp_mic_state["connected"] = True
            inmp_mic_state["last_seen"] = time.time()
            try:
                samples = np.frombuffer(pcm_chunk, dtype=np.int16)
                if len(samples) > 0:
                    inmp_mic_state["rms"] = float(np.sqrt(np.mean(samples.astype(np.float32)**2)))
                    inmp_mic_state["peak"] = int(np.max(np.abs(samples)))
            except Exception:
                pass

            # Accumulate into test buffer if 3s audio test recording is in progress
            if inmp_test_recording_active:
                inmp_test_recording_buffer.extend(pcm_chunk)
            
            # Feed into Speech-To-Text / Energy VAD / Wake-word
            recognized_text = await stt_engine.process_pcm_chunk(pcm_chunk)
            if recognized_text:
                print(f"[STT] User Voice Detected via Mic: '{recognized_text}'")
                
                # Instantly display user spoken text in WebApp chat drawer!
                for c in list(connected_web_clients):
                    try:
                        await c.send_text(json.dumps({
                            "type": "chat_user",
                            "text": recognized_text
                        }))
                    except Exception:
                        pass

                asyncio.create_task(handle_chat_query(recognized_text))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS-AUDIO] WebSocket notice: {e}")
    finally:
        if esp32_audio_socket is websocket:
            esp32_audio_socket = None
            inmp_mic_state["connected"] = False
            print("[WS-AUDIO] Head ESP32-S3 CAM audio disconnected.")

# ============================================================================
# INMP441 MICROPHONE LIVE TELEMETRY & 3-SECOND AUDIO TEST APIS
# ============================================================================
@app.get("/api/inmp/status")
async def get_inmp_status_api():
    """Returns real-time connection status and signal energy of INMP441 microphone."""
    is_alive = bool(esp32_audio_socket is not None and (time.time() - inmp_mic_state["last_seen"] < 3.0))
    return JSONResponse({
        "connected": is_alive,
        "rms": round(inmp_mic_state["rms"], 1) if is_alive else 0.0,
        "peak": inmp_mic_state["peak"] if is_alive else 0,
        "last_seen_sec_ago": round(time.time() - inmp_mic_state["last_seen"], 1) if inmp_mic_state["last_seen"] > 0 else 999.0
    })

@app.post("/api/inmp/test")
async def test_inmp_mic_api(duration: float = 3.0):
    """Records audio directly from robot's INMP441 microphone for duration seconds and returns WAV audio for immediate playback."""
    global inmp_test_recording_active, inmp_test_recording_buffer
    if not esp32_audio_socket or (time.time() - inmp_mic_state["last_seen"] > 3.0):
        return JSONResponse({
            "status": "error",
            "message": "Head ESP32-S3 is offline or not streaming INMP441 mic data to /ws/audio. Please verify Head ESP32-S3 power and Wi-Fi connection."
        }, status_code=503)

    inmp_test_recording_buffer = bytearray()
    inmp_test_recording_active = True

    # Broadcast notification to WebApp clients that INMP test recording has started
    test_start_msg = json.dumps({"type": "inmp_test_status", "status": "recording", "duration": duration})
    for c in list(connected_web_clients):
        try:
            await c.send_text(test_start_msg)
        except Exception:
            pass

    record_time = max(1.0, min(6.0, float(duration)))
    await asyncio.sleep(record_time)

    inmp_test_recording_active = False
    captured_pcm = bytes(inmp_test_recording_buffer)
    inmp_test_recording_buffer.clear()

    if len(captured_pcm) < 500:
        return JSONResponse({
            "status": "error",
            "message": "No audio received from INMP441 during the test window. Please verify INMP441 wiring (SCK=38, WS=37, SD=39)."
        }, status_code=500)

    # Encode raw 16kHz 16-bit Mono PCM to standard playable WAV container
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(captured_pcm)
    wav_bytes = wav_io.getvalue()

    return Response(content=wav_bytes, media_type="audio/wav")

# ============================================================================
# PHYSICAL ACTUATION: SERVOS & EXPANSION PINS
# ============================================================================
async def apply_servo_angles(angles: List[int]):
    """Updates current 5-axis servo angles."""
    clamped = [max(0, min(180, int(a))) for a in angles[:5]]
    while len(clamped) < 5:
        clamped.append(90)
    robot_state["servos"] = clamped

async def trigger_pin_control(pin: int, state: str, pwm: int = -1):
    """Queues dynamic expansion GPIO command to Chassis MCU."""
    global pending_pin_commands
    val = 1 if (str(state).upper() in ("HIGH", "1", "ON", "TRUE")) else 0
    robot_state["pins"][str(pin)] = pwm if pwm >= 0 else val
    cmd = {"pin": pin, "state": "HIGH" if val else "LOW", "val": val}
    if pwm >= 0:
        cmd["pwm"] = pwm
    pending_pin_commands.append(cmd)

    # Immediately transmit via UDP datagram for zero latency
    datagram = json.dumps({"pin_cmd": cmd}) + "\n"
    try:
        udp_socket.sendto(datagram.encode("utf-8"), (config.ROBOT_HEAD_IP, config.ROBOT_UDP_PORT))
    except Exception:
        pass

    # Notify WebApp
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({"type": "pin_update", "pin": pin, "val": robot_state["pins"][str(pin)]}))
        except Exception:
            pass

async def trigger_custom_servo(pin: int, angle: int):
    """Actuates dynamic custom servo on arbitrary GPIO pin."""
    angle = max(0, min(180, int(angle)))
    memory_vault.set_pin_role(str(pin), "SERVO", f"Servo GPIO {pin}", angle)
    datagram = json.dumps({"custom_servo": {"pin": pin, "angle": angle}}) + "\n"
    try:
        udp_socket.sendto(datagram.encode("utf-8"), (config.ROBOT_HEAD_IP, config.ROBOT_UDP_PORT))
    except Exception:
        pass
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({"type": "custom_servo_update", "pin": pin, "angle": angle}))
        except Exception:
            pass

async def trigger_line_follower(enable: bool, left_pin: int = 2, right_pin: int = 3, speed: int = 140, invert: bool = False):
    """Enables or disables autonomous closed-loop line follower."""
    cfg = memory_vault.set_line_follower_config(enable, left_pin, right_pin, speed, invert)
    robot_state["emotion"] = "happy" if enable else "neutral"
    datagram = json.dumps({
        "line_follower": {
            "enable": enable,
            "left_pin": left_pin,
            "right_pin": right_pin,
            "speed": speed,
            "invert": invert
        }
    }) + "\n"
    try:
        udp_socket.sendto(datagram.encode("utf-8"), (config.ROBOT_HEAD_IP, config.ROBOT_UDP_PORT))
    except Exception:
        pass
    for c in list(connected_web_clients):
        try:
            await c.send_text(json.dumps({"type": "line_follower_update", "data": cfg}))
        except Exception:
            pass


# ============================================================================
# MULTIMODAL CHAT & ROBOT ACTIONS PIPELINE
# ============================================================================
action_override_cmd = {"fwd": 0, "turn": 0}
action_override_active = False

async def execute_robot_action(action: dict):
    """Executes physical chassis movements, servo choreographies, and expansion pins."""
    global action_override_cmd, action_override_active
    act_type = action.get("type")
    print(f"[ACTION] Executing Project L.O.O.N.A. action: {action}")

    # 1. 5-Axis Servo Choreographies
    if act_type == "servos":
        preset = action.get("preset")
        if preset == "perk_ears":
            robot_state["emotion"] = "happy"
            await apply_servo_angles([90, 80, 20, 160, 90])
            await asyncio.sleep(1.2)
            await apply_servo_angles([90, 90, 90, 90, 90])
        elif preset == "wag_tail":
            for _ in range(4):
                await apply_servo_angles([90, 90, 90, 90, 45])
                await asyncio.sleep(0.15)
                await apply_servo_angles([90, 90, 90, 90, 135])
                await asyncio.sleep(0.15)
            await apply_servo_angles([90, 90, 90, 90, 90])
        elif preset == "curious_tilt":
            await apply_servo_angles([90, 115, 60, 120, 90])
            await asyncio.sleep(1.5)
            await apply_servo_angles([90, 90, 90, 90, 90])
        elif "angles" in action:
            await apply_servo_angles(action["angles"])

    # 2. Dynamic Expansion GPIO Control & Custom Servos
    elif act_type == "pin_control":
        pin = int(action.get("pin", 2))
        state = action.get("state", "HIGH")
        pwm = action.get("pwm", -1)
        await trigger_pin_control(pin, state, pwm)

    elif act_type == "pin_servo":
        pin = int(action.get("pin", 21))
        angle = int(action.get("angle", 90))
        await trigger_custom_servo(pin, angle)

    elif act_type == "line_follower":
        enable = bool(action.get("enable", True))
        l_pin = int(action.get("left_pin", 2))
        r_pin = int(action.get("right_pin", 3))
        spd = int(action.get("speed", 140))
        inv = bool(action.get("invert", False))
        await trigger_line_follower(enable, l_pin, r_pin, spd, inv)

    elif act_type == "pin_role":
        pin = str(action.get("pin", 2))
        role = str(action.get("role", "OUTPUT"))
        label = str(action.get("label", ""))
        memory_vault.set_pin_role(pin, role, label)
        await broadcast_vault_update()

    # 3. Memory Saving
    elif act_type == "save_face":
        name = action.get("name", "Orbit")
        tracker.save_current_face(name)
        await broadcast_vault_update()

    elif act_type == "save_note":
        memory_vault.save_note(action.get("key", ""), action.get("value", ""))
        await broadcast_vault_update()

    elif act_type == "macro":
        actions = action.get("actions", [])
        for sub_act in actions:
            await execute_robot_action(sub_act)
            await asyncio.sleep(0.2)

    # 4. Rover Maneuvers
    elif act_type in ("spin", "orbit_spin"):
        action_override_active = True
        robot_state["emotion"] = "happy"
        # Perk ears during spin
        await apply_servo_angles([90, 85, 30, 150, 45])
        action_override_cmd = {"fwd": 0, "turn": 220}
        await asyncio.sleep(1.2)
        action_override_cmd = {"fwd": 0, "turn": 0}
        await apply_servo_angles([90, 90, 90, 90, 90])
        action_override_active = False

    elif act_type in ("dance", "kpop_dance"):
        action_override_active = True
        robot_state["emotion"] = "happy"
        for i in range(3):
            # Alternating wiggling ears and tail while stepping
            ear_l = 30 if i % 2 == 0 else 110
            ear_r = 150 if i % 2 == 0 else 70
            await apply_servo_angles([90, 80, ear_l, ear_r, 45 if i % 2 == 0 else 135])
            action_override_cmd = {"fwd": 140, "turn": -180}
            await asyncio.sleep(0.3)
            action_override_cmd = {"fwd": -140, "turn": 180}
            await asyncio.sleep(0.3)
            action_override_cmd = {"fwd": 0, "turn": 200}
            await asyncio.sleep(0.25)
        action_override_cmd = {"fwd": 0, "turn": 0}
        await apply_servo_angles([90, 90, 90, 90, 90])
        action_override_active = False

    elif act_type == "drive":
        fwd = int(action.get("fwd", 0))
        turn = int(action.get("turn", 0))
        duration = float(action.get("duration", 1.0))
        action_override_active = True
        action_override_cmd = {"fwd": fwd, "turn": turn}
        await asyncio.sleep(duration)
        action_override_cmd = {"fwd": 0, "turn": 0}
        action_override_active = False

    elif act_type == "set_emotion":
        robot_state["emotion"] = action.get("emotion", "happy")

    elif act_type == "follow":
        robot_state["mode"] = "companion"
        robot_state["following"] = True
        robot_state["emotion"] = "happy"

    # 5. Spotify Audio Stream to MAX98357A Speaker
    elif act_type == "spotify_play":
        query = action.get("query", "LOONA Hi High")
        async def send_audio_cb(pcm_chunk):
            if esp32_audio_socket:
                await esp32_audio_socket.send_bytes(pcm_chunk)
        async def notify_cb(data):
            for ws in list(connected_web_clients):
                try:
                    await ws.send_text(json.dumps({"type": "spotify_update", "data": data}))
                except Exception:
                    pass
        res = spotify_service.play(query, send_audio_cb, notify_cb)
        robot_state["emotion"] = "happy"
        await notify_cb(res)

    elif act_type == "spotify_pause":
        res = spotify_service.pause()
        for ws in list(connected_web_clients):
            try:
                await ws.send_text(json.dumps({"type": "spotify_update", "data": res}))
            except Exception:
                pass

    elif act_type == "spotify_resume":
        async def send_audio_cb(pcm_chunk):
            if esp32_audio_socket:
                await esp32_audio_socket.send_bytes(pcm_chunk)
        async def notify_cb(data):
            for ws in list(connected_web_clients):
                try:
                    await ws.send_text(json.dumps({"type": "spotify_update", "data": data}))
                except Exception:
                    pass
        res = spotify_service.resume(send_audio_cb, notify_cb)
        await notify_cb(res)

    elif act_type == "spotify_next":
        res = spotify_service.next_track()
        for ws in list(connected_web_clients):
            try:
                await ws.send_text(json.dumps({"type": "spotify_update", "data": res}))
            except Exception:
                pass

    elif act_type == "roam":
        enable = bool(action.get("enable", True))
        roam_service.set_enabled(enable)
        robot_state["roam_mode"] = enable
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "roam_update",
                    "enabled": enable,
                    "state": roam_service.state
                }))
            except Exception:
                pass

    elif act_type == "stop":
        robot_state["following"] = False
        roam_service.set_enabled(False)
        robot_state["roam_mode"] = False
        action_override_cmd = {"fwd": 0, "turn": 0}
        action_override_active = False
        robot_state["emotion"] = "neutral"
        spotify_service.pause()

    # 6. Photography Snapshot Execution
    elif act_type == "take_picture":
        robot_state["emotion"] = "wink_left"
        photo = tracker.capture_snapshot(with_overlay=False, notes="Voice snapshot")
        payload = json.dumps({"type": "photo_captured", "photo": photo})
        for c in list(connected_web_clients):
            try:
                await c.send_text(payload)
            except Exception:
                pass

    # 7. Optical Object Detection
    elif act_type == "detect_objects":
        tracker.set_detection_mode("all")
        robot_state["emotion"] = "star_eyes"
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "detection_mode_update",
                    "mode": "all"
                }))
            except Exception:
                pass


async def speak_notification(text: str):
    """Speaks a message through the ESP32 MAX98357A speaker in natural K-Pop Idol voice and logs to SQLite3."""
    robot_state["emotion"] = "speaking"
    stt_engine.set_robot_speaking(True)

    try:
        # 1. Log LOONA speech to SQLite3 Database
        memory_vault.log_chat("loona", text, "speaking")

        # 2. Calculate dynamic subtitle duration proportional to sentence size
        global latest_subtitle, esp32_audio_socket
        duration_ms = calculate_subtitle_duration_ms(text)
        latest_subtitle = {"text": text, "duration": duration_ms, "timestamp": time.time()}

        # Broadcast speech text & sentence-size timed subtitles to connected WebApp clients
        sub_payload = json.dumps({"type": "subtitles", "text": text, "duration": duration_ms})
        chat_payload = json.dumps({"type": "chat_reply", "text": text, "duration": duration_ms})
        for ws in list(connected_web_clients):
            try:
                await ws.send_text(sub_payload)
                await ws.send_text(chat_payload)
            except Exception:
                pass

        # 3. Stream raw PCM audio to ESP32-S3 Head Controller for MAX98357A I2S playback
        sock = esp32_audio_socket
        if sock:
            try:
                # Signal ESP32 to mute mic and prepare I2S amplifier
                try:
                    await sock.send_text(json.dumps({"type": "spk_start"}))
                except Exception:
                    pass

                async for pcm_chunk in tts_engine.stream_pcm_chunks(text, chunk_size=1024):
                    if esp32_audio_socket is not sock:
                        break  # Socket changed or disconnected during playback
                    await sock.send_bytes(pcm_chunk)
                print(f"[AUDIO-MAX98357A] Streamed {len(text)} chars to onboard speaker.")

                # Signal ESP32 that stream finished
                try:
                    await sock.send_text(json.dumps({"type": "spk_done"}))
                except Exception:
                    pass
            except Exception as e:
                print(f"[AUDIO-MAX98357A] Notice during PCM streaming: {type(e).__name__} ({e})")
                if esp32_audio_socket is sock:
                    esp32_audio_socket = None
        else:
            print(f"[AUDIO-MAX98357A] Standby (Head ESP32 not connected to /ws/audio). Text spoken: '{text}'")
            # Host PC local speaker audio output fallback
            try:
                def _speak_host_pc():
                    try:
                        import win32com.client
                        sp = win32com.client.Dispatch("SAPI.SpVoice")
                        for v in sp.GetVoices():
                            if "zira" in v.GetDescription().lower():
                                sp.Voice = v
                                break
                        clean_msg = re.sub(r"[*_#`~\[\]]", "", text).strip()
                        sp.Speak(clean_msg)
                    except Exception:
                        pass
                import threading
                threading.Thread(target=_speak_host_pc, daemon=True).start()
            except Exception:
                pass
    finally:
        stt_engine.set_robot_speaking(False)
        robot_state["emotion"] = "happy" if robot_state.get("following", False) else "neutral"

async def handle_chat_query(user_query: str):
    """Coordinates voice command parsing, SQLite3 logging, Gemini reasoning, and MAX98357A TTS streaming."""
    print(f"[CHAT] Received query: '{user_query}'")

    # 1. Save user query in SQLite3 Database
    memory_vault.log_chat("user", user_query)

    # 2. Voice Command Protocol: Check for "Hey LOONA, follow me" or "Stop"
    voice_cmd = parse_voice_command(user_query)
    if voice_cmd == "FOLLOW_ME":
        print("[PROTOCOL] >>> 'FOLLOW_ME' Voice Command Triggered! <<<")
        robot_state["mode"] = "companion"
        robot_state["following"] = True
        roam_service.set_enabled(False)
        robot_state["roam_mode"] = False
        reply_text = "Target locked! Following you right now, Orbit! Let's roll!"
        await speak_notification(reply_text)
        return

    elif voice_cmd == "START_ROAM":
        print("[PROTOCOL] >>> 'START_ROAM' Voice Command Triggered! <<<")
        robot_state["mode"] = "companion"
        robot_state["following"] = False
        roam_service.set_enabled(True)
        robot_state["roam_mode"] = True
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "roam_update",
                    "enabled": True,
                    "state": roam_service.state
                }))
            except Exception:
                pass
        reply_text = "Autonomous roam engaged! Exploring and keeping watch, Orbit! 🐾"
        await speak_notification(reply_text)
        return

    elif voice_cmd == "STOP_ROAM":
        print("[PROTOCOL] >>> 'STOP_ROAM' Voice Command Triggered! <<<")
        roam_service.set_enabled(False)
        robot_state["roam_mode"] = False
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "roam_update",
                    "enabled": False,
                    "state": roam_service.state
                }))
            except Exception:
                pass
        reply_text = "Stopped roaming. Standing by, Orbit!"
        await speak_notification(reply_text)
        return

    elif voice_cmd == "STOP":
        print("[PROTOCOL] >>> 'STOP' Voice Command Triggered! <<<")
        robot_state["following"] = False
        roam_service.set_enabled(False)
        robot_state["roam_mode"] = False
        for c in list(connected_web_clients):
            try:
                await c.send_text(json.dumps({
                    "type": "roam_update",
                    "enabled": False,
                    "state": roam_service.state
                }))
            except Exception:
                pass
        spotify_service.pause()
        reply_text = "Stopping all locomotive motion and music! Standing by."
        await speak_notification(reply_text)
        return

    # 3. General Query & Multimodal Intelligence: Process with Gemini / Memory Vault
    robot_state["emotion"] = "thinking"
    image_bytes = tracker.get_latest_jpeg()
    
    reply_text, action = await ai_engine.generate_response(user_query, image_bytes)
    print(f"[CHAT] LOONA says: '{reply_text}' | Action: {action}")

    # If action is Spotify playback, finish LOONA voice speaking first, then start music stream!
    if action and action.get("type") == "spotify_play":
        await speak_notification(reply_text)
        asyncio.create_task(execute_robot_action(action))
        return

    # Execute physical action or hardware actuation
    if action:
        asyncio.create_task(execute_robot_action(action))

    await speak_notification(reply_text)

# ============================================================================
# BACKGROUND TASKS: UDP MOTOR/SERVO DISPATCHER & STATE BROADCASTER
# ============================================================================
async def motion_and_telemetry_loop():
    """Dispatches UDP motor and servo commands and broadcasts telemetry at 25 Hz."""
    global pending_pin_commands
    while True:
        tracking_info = tracker.get_tracking_state()
        
        # 1. Autonomous Roam Evaluation
        roam_fwd = 0
        roam_turn = 0
        if roam_service.is_enabled():
            can_roam = (
                not action_override_active
                and not robot_state.get("following", False)
                and (
                    robot_state["mode"] != "manual"
                    or (robot_state["manual_cmd"]["fwd"] == 0 and robot_state["manual_cmd"]["turn"] == 0)
                )
            )
            rf, rt, r_emo, r_servo = roam_service.update(tracking_info, can_move=can_roam)
            if can_roam:
                roam_fwd = rf
                roam_turn = rt
                if r_emo and robot_state["emotion"] not in ("speaking", "thinking", "wink_left", "wink_right"):
                    robot_state["emotion"] = r_emo
                if r_servo:
                    asyncio.create_task(execute_robot_action({"type": "servos", "preset": r_servo}))

        # 2. Determine active motor command with priority
        if action_override_active:
            motor_fwd = action_override_cmd["fwd"]
            motor_turn = action_override_cmd["turn"]
        elif robot_state["mode"] == "companion":
            if robot_state.get("following", False) and tracking_info["face_detected"]:
                motor_fwd = tracking_info["fwd"]
                motor_turn = tracking_info["turn"]
            elif roam_service.is_enabled():
                motor_fwd = roam_fwd
                motor_turn = roam_turn
            else:
                motor_fwd = 0
                motor_turn = 0
        else:
            if robot_state["manual_cmd"]["fwd"] != 0 or robot_state["manual_cmd"]["turn"] != 0:
                motor_fwd = robot_state["manual_cmd"]["fwd"]
                motor_turn = robot_state["manual_cmd"]["turn"]
            elif roam_service.is_enabled():
                motor_fwd = roam_fwd
                motor_turn = roam_turn
            else:
                motor_fwd = 0
                motor_turn = 0

        # 3. Construct UDP Datagram with Locomotive Drive + 5 Servos
        datagram_dict = {
            "fwd": motor_fwd,
            "turn": motor_turn,
            "servos": robot_state["servos"]
        }

        # Attach pending pin command if any
        if pending_pin_commands:
            cmd = pending_pin_commands.pop(0)
            datagram_dict["pin_cmd"] = cmd

        datagram_str = json.dumps(datagram_dict) + "\n"
        raw_bytes = datagram_str.encode("utf-8")
        try:
            # 1. Direct transmission to Standalone ESP32-S3 Chassis Motion Controller
            if getattr(config, "ROBOT_CHASSIS_IP", None):
                udp_socket.sendto(raw_bytes, (config.ROBOT_CHASSIS_IP, config.ROBOT_UDP_PORT))
            # 2. Also send to Head IP if distinct (for backward-compatible inter-MCU setups)
            if config.ROBOT_HEAD_IP and config.ROBOT_HEAD_IP != getattr(config, "ROBOT_CHASSIS_IP", None):
                udp_socket.sendto(raw_bytes, (config.ROBOT_HEAD_IP, config.ROBOT_UDP_PORT))
        except Exception:
            pass

        # 4. Broadcast Real-Time State to WebApp
        telemetry_payload = {
            "project": config.PROJECT_NAME,
            "chassis_ip": getattr(config, "ROBOT_CHASSIS_IP", "192.168.100.244"),
            "head_ip": config.ROBOT_HEAD_IP,
            "mode": robot_state["mode"],
            "following": robot_state.get("following", False),
            "roam_mode": roam_service.is_enabled(),
            "roam": roam_service.get_status(),
            "emotion": robot_state["emotion"],
            "gaze": {
                "dx": tracking_info["dx"],
                "dy": tracking_info["dy"]
            },
            "face_detected": tracking_info["face_detected"],
            "recognized_name": tracking_info.get("recognized_name", "Orbit"),
            "faces_count": tracking_info.get("faces_count", 0),
            "faces": tracking_info.get("faces", []),
            "objects_count": tracking_info.get("objects_count", 0),
            "objects": tracking_info.get("objects", []),
            "detection_mode": tracking_info.get("detection_mode", "all"),
            "drive": {
                "fwd": motor_fwd,
                "turn": motor_turn
            },
            "servos": robot_state["servos"],
            "pins": robot_state["pins"],
            "custom_pins": memory_vault.get_custom_pins(),
            "line_follower": memory_vault.get_line_follower_config(),
            "inmp_mic": {
                "connected": bool(esp32_audio_socket is not None and (time.time() - inmp_mic_state["last_seen"] < 3.0)),
                "rms": round(inmp_mic_state["rms"], 1) if (esp32_audio_socket is not None and (time.time() - inmp_mic_state["last_seen"] < 3.0)) else 0.0,
                "peak": inmp_mic_state["peak"] if (esp32_audio_socket is not None and (time.time() - inmp_mic_state["last_seen"] < 3.0)) else 0
            },
            "fps": tracking_info["fps"],
            "track": spotify_service.current_track_info
        }
        
        payload_str = json.dumps(telemetry_payload)
        for ws in list(connected_web_clients):
            try:
                await ws.send_text(payload_str)
            except Exception:
                pass

        await asyncio.sleep(0.04)

# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================
@app.on_event("startup")
async def startup_event():
    lan_ip = get_lan_ip()
    port = config.SERVER_PORT
    print("\n====================================================================")
    print("   🌙 PROJECT L.O.O.N.A. BRAIN SERVER (FastAPI 2.0) IS LIVE!        ")
    print("====================================================================")
    print(f" 💻 Local PC Browser:      http://localhost:{port}/                 ")
    print(f" 📱 Mobile / LAN Device:   http://{lan_ip}:{port}/                   ")
    print(f" 🎯 Target Head ESP32-S3:  {config.ROBOT_HEAD_IP} (UDP {config.ROBOT_UDP_PORT})")
    print("====================================================================")
    print(" 💡 To open on your smartphone or tablet on the same Wi-Fi:")
    print(f"    1. Connect your phone to this Wi-Fi network.")
    print(f"    2. In your phone's browser, open: http://{lan_ip}:{port}/")
    print("    3. Or click '📱 LINK DEVICE' in the WebApp to scan the QR code!")
    print("====================================================================\n")
    tracker.start()
    asyncio.create_task(motion_and_telemetry_loop())

@app.on_event("shutdown")
async def shutdown_event():
    tracker.stop()
    spotify_service.stop_stream()
    udp_socket.close()
    print("[SYS] Brain server shutdown complete.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.SERVER_HOST, port=config.SERVER_PORT, reload=False)
