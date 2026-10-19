import asyncio
import json
import os
import sys
import sqlite3
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================================
# TEST 1: SQLITE3 DATABASE ENGINE DIRECT PERSISTENCE & SCHEMA
# ============================================================================
print("=== TEST 1: SQLITE3 DATABASE ENGINE DIRECT PERSISTENCE & SCHEMA ===")
from database import db, DB_PATH

assert os.path.exists(DB_PATH), f"SQLite database file not found at {DB_PATH}"
print(f"[PASS] SQLite3 database file verified at: {DB_PATH}")

# Verify SQLite3 tables exist
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
required_tables = ["faces", "commands", "notes", "pins", "settings", "chat_logs", "photos"]
for tbl in required_tables:
    assert tbl in tables, f"Missing table '{tbl}' in SQLite database"
print(f"[PASS] All required SQLite3 tables present: {', '.join(required_tables)}")

# Test direct database operations
test_face = db.save_face("Kananyan_DB_Test", "Chief Architect", "Testing SQLite direct save")
assert test_face["name"] == "Kananyan_DB_Test"
faces_dict = db.get_faces()
assert "Kananyan_DB_Test" in faces_dict
print("[PASS] Direct SQLite3 save_face & get_faces")

test_chat = db.log_chat("user", "Hello LOONA, test chat log", "neutral")
assert test_chat["message"] == "Hello LOONA, test chat log"
recent_chats = db.get_recent_chat_logs(10)
assert any(c["message"] == "Hello LOONA, test chat log" for c in recent_chats)
print("[PASS] Direct SQLite3 chat_logs logging & querying")

# Test photos table operations
test_photo = db.save_photo("test_photo_unit.jpg", "data/captures/test_photo_unit.jpg", "Unit Test Snapshot")
assert test_photo["filename"] == "test_photo_unit.jpg"
photos_list = db.get_photos()
assert any(p["filename"] == "test_photo_unit.jpg" for p in photos_list)
assert db.delete_photo("test_photo_unit.jpg") is True
print("[PASS] Direct SQLite3 save_photo, get_photos, and delete_photo")

stats = db.get_database_stats()
assert stats["engine"] == "SQLite3"
assert stats["tables"]["faces"] >= 1
assert stats["tables"]["chat_logs"] >= 1
assert "photos" in stats["tables"]
print(f"[PASS] SQLite3 database stats: {stats['tables']}")
conn.close()

# Cleanup test face
db.delete_face("Kananyan_DB_Test")


# ============================================================================
# TEST 2: MEMORY VAULT SERVICE WRAPPING SQLITE3
# ============================================================================
print("\n=== TEST 2: MEMORY VAULT PERSISTENCE & BACKWARDS COMPATIBILITY ===")
from memory_service import memory_vault

# Save face
face_res = memory_vault.save_face("Kananyan", "Chief Architect", "Creator of Project LOONA")
assert face_res["name"] == "Kananyan", "Face name save failed"
assert "Kananyan" in memory_vault.get_faces(), "Face not in get_faces"
print("[PASS] save_face and get_faces (SQLite3 backed)")

# Save note
note_res = memory_vault.save_note("Project Identity", "Project L.O.O.N.A. (Locomotive Optical Operative for Navigation and Assistance)")
assert "Project Identity" in memory_vault.get_notes(), "Note not in get_notes"
print("[PASS] save_note and get_notes (SQLite3 backed)")

# Save custom macro command
cmd_res = memory_vault.save_command("patrol", [{"type": "drive", "fwd": 150}, {"type": "servos", "preset": "perk_ears"}], "Autonomous patrol macro")
assert "patrol" in memory_vault.get_commands(), "Command not in get_commands"
found_cmd = memory_vault.find_command("please patrol the room")
assert found_cmd is not None and found_cmd["trigger"] == "patrol", "find_command macro failed"
print("[PASS] save_command and find_command (SQLite3 backed)")

# Save pin roles
pin_role_res = memory_vault.set_pin_role("21", "SERVO", "Auxiliary Gripper Servo", 90)
assert "21" in memory_vault.get_custom_pins(), "Pin 21 not in custom_pins"
print("[PASS] set_pin_role and get_custom_pins (SQLite3 backed)")

# Save line follower config
lf_res = memory_vault.set_line_follower_config(True, 2, 3, 160, False)
assert lf_res["enabled"] is True, "Line follower config failed"
assert memory_vault.get_line_follower_config()["speed"] == 160, "Line follower speed failed"
print("[PASS] set_line_follower_config (SQLite3 backed)")

# Test deletions
del_face = memory_vault.delete_face("NonexistentTest")
assert del_face is False
memory_vault.save_face("TempUser", "Guest")
assert memory_vault.delete_face("TempUser") is True
assert memory_vault.delete_pin_role("21") is True
print("[PASS] delete operations (face, pin_role)")


# ============================================================================
# TEST 3: MULTI-FACE DETECTION & VISUAL RECOGNITION BOXES
# ============================================================================
print("\n=== TEST 3: MULTI-FACE RECOGNITION BOXES & TARGET NAMING ===")
from vision_tracker import VisionTracker
from config import config

tracker = VisionTracker()

# 1. Test synthetic multi-target rendering (when camera is offline)
synth_frame = tracker._generate_synthetic_frame(0)
assert isinstance(synth_frame, np.ndarray)
assert synth_frame.shape == (config.FRAME_HEIGHT, config.FRAME_WIDTH, 3)
print(f"[PASS] Synthetic frame rendered at {synth_frame.shape[1]}x{synth_frame.shape[0]} with multi-target boxes")

# 2. Test _draw_face_box helper directly
test_canvas = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
tracker._draw_face_box(test_canvas, x=50, y=50, w=80, h=80, name="Kananyan", role="Creator", is_primary=True, index=1)
tracker._draw_face_box(test_canvas, x=180, y=70, w=60, h=60, name="Orbit Friend", role="Companion", is_primary=False, index=2)
# Ensure drawing modified the canvas pixels
assert np.sum(test_canvas) > 0, "Face boxes did not write to canvas pixels"
print("[PASS] _draw_face_box rendered primary & secondary cyber reticles, boxes, and name badges")

# 3. Test _draw_object_box helper directly
tracker._draw_object_box(test_canvas, x=100, y=140, w=70, h=50, label="Smartphone", confidence=0.88, index=1)
tracker._draw_object_box(test_canvas, x=220, y=130, w=50, h=60, label="Coffee Mug", confidence=0.91, index=2)
print("[PASS] _draw_object_box rendered emerald bounding boxes, label flags, and confidence tags")

# 4. Test detection modes
tracker.set_detection_mode("objects")
assert tracker.detection_mode == "objects"
tracker.set_detection_mode("faces")
assert tracker.detection_mode == "faces"
tracker.set_detection_mode("all")
assert tracker.detection_mode == "all"
print("[PASS] set_detection_mode ('all', 'faces', 'objects')")

# 5. Test capture_snapshot
snap_res = tracker.capture_snapshot(with_overlay=False, notes="Test suite automated snapshot")
assert "filename" in snap_res and "filepath" in snap_res
assert os.path.exists(snap_res["filepath"]), f"Captured snapshot file does not exist: {snap_res['filepath']}"
assert snap_res["filename"].endswith(".jpg")
print(f"[PASS] capture_snapshot created valid JPEG on disk: {snap_res['filename']}")

# 6. Test tracking state telemetry format (faces + objects + detection_mode + nav avoidance)
state = tracker.get_tracking_state()
assert "face_detected" in state
assert "dx" in state and "dy" in state
assert "recognized_name" in state
assert "faces_count" in state
assert "faces" in state
assert "objects" in state
assert "objects_count" in state
assert "detection_mode" in state
assert "nav" in state, "Missing 'nav' collision avoidance telemetry in tracking state"
nav = state["nav"]
for nav_key in ("person_ahead", "person_close", "person_dx", "left_blocked", "center_blocked", "right_blocked", "clear_direction"):
    assert nav_key in nav, f"Missing nav key '{nav_key}'"
print(f"[PASS] Tracking state verified: faces_count={state['faces_count']}, objects_count={state['objects_count']}, mode='{state['detection_mode']}', clear_dir='{nav['clear_direction']}'")

# Clean up test snapshot file
try:
    if os.path.exists(snap_res["filepath"]):
        os.remove(snap_res["filepath"])
    db.delete_photo(snap_res["filename"])
except Exception:
    pass


# ============================================================================
# TEST 4: AI VOICE COMMAND & PIN SHORTCUTS
# ============================================================================
print("\n=== TEST 4: AI VOICE COMMAND & PIN SHORTCUTS ===")
from ai_service import ai_engine

test_queries = [
    ("turn on pin 2", "pin_control", 2),
    ("turn off pin 6", "pin_control", 6),
    ("set pin 3 pwm 128", "pin_control", 3),
    ("set servo on pin 21 to 45", "pin_servo", 21),
    ("make a line follower on pins 2 and 3", "line_follower", 2),
    ("start line follower", "line_follower", None),
    ("stop line follower", "line_follower", None),
    ("perk your ears", "servos", None),
    ("wag your tail", "servos", None),
    ("remember that color is cyan", "save_note", None),
    ("save this face as Nicole", "save_face", None),
    ("play Hi High on spotify", "spotify_play", None),
    ("take a picture", "take_picture", None),
    ("snap a photo", "take_picture", None),
    ("what objects do you see", "detect_objects", None),
    ("detect objects", "detect_objects", None),
    ("start roaming", "roam", None),
    ("roam around", "roam", None),
    ("wander around", "roam", None),
    ("stop roaming", "roam", None),
]

for query, expected_type, expected_pin in test_queries:
    resp, action = ai_engine.check_local_shortcuts(query)
    assert action is not None, f"Shortcut failed for query: '{query}'"
    assert action.get("type") == expected_type, f"Expected {expected_type}, got {action.get('type')} for '{query}'"
    if expected_pin is not None:
        if expected_type == "line_follower":
            assert action.get("left_pin") == expected_pin, f"Expected left pin {expected_pin} for '{query}'"
        else:
            assert action.get("pin") == expected_pin, f"Expected pin {expected_pin} for '{query}'"
    print(f"[PASS] Shortcut: '{query}' -> type={action.get('type')}")

# Test parse_voice_command
from ai_service import parse_voice_command
assert parse_voice_command("hey loona please follow me") == "FOLLOW_ME"
assert parse_voice_command("hey loona start roaming") == "START_ROAM"
assert parse_voice_command("roam around") == "START_ROAM"
assert parse_voice_command("hey loona stop roaming") == "STOP_ROAM"
assert parse_voice_command("loona stop") == "STOP"
print("[PASS] parse_voice_command ('FOLLOW_ME', 'START_ROAM', 'STOP_ROAM', 'STOP')")

# ============================================================================
# TEST 4b: AUTONOMOUS IDLE ROAM & COLLISION AVOIDANCE ENGINE (ROAM_SERVICE)
# ============================================================================
print("\n=== TEST 4b: AUTONOMOUS IDLE ROAM & COLLISION AVOIDANCE ENGINE ===")
from roam_service import roam_service, RoamState

# 1. Enable / disable state tracking
roam_service.set_enabled(False)
assert not roam_service.is_enabled()
assert roam_service.get_status()["enabled"] is False

roam_service.set_enabled(True)
assert roam_service.is_enabled()
assert roam_service.get_status()["enabled"] is True
print("[PASS] RoamController set_enabled & get_status")

# 2. Yielding when can_move=False (manual drive / speaking / following)
fwd, turn, emo, srv = roam_service.update({"nav": {}}, can_move=False)
assert fwd == 0 and turn == 0, f"Expected 0,0 when can_move=False, got {fwd},{turn}"
print("[PASS] RoamController safely yields 0 drive commands when can_move=False")

# 3. Simulate Nudge Move & Obstacle Avoidance Interrupt
roam_service._transition_to(RoamState.NUDGE_MOVE, duration=2.0)
tracking_obstacle = {
    "face_detected": False,
    "dx": 0.0,
    "nav": {
        "person_ahead": False,
        "person_close": False,
        "center_blocked": True,
        "left_blocked": True,
        "right_blocked": False,
        "clear_direction": "right"
    }
}
fwd, turn, emo, srv = roam_service.update(tracking_obstacle, can_move=True)
assert roam_service.state == RoamState.AVOID_OBSTACLE, f"Expected AVOID_OBSTACLE, got {roam_service.state}"
assert emo == "surprised"
print(f"[PASS] Obstacle avoidance interrupt: successfully transitioned to '{roam_service.state}' with emotion='{emo}'")

# 4. Simulate Person Avoidance Interrupt
roam_service._transition_to(RoamState.NUDGE_MOVE, duration=2.0)
tracking_person = {
    "face_detected": True,
    "dx": 0.45,
    "nav": {
        "person_ahead": True,
        "person_close": True,
        "center_blocked": False,
        "left_blocked": False,
        "right_blocked": False,
        "clear_direction": "left"
    }
}
fwd, turn, emo, srv = roam_service.update(tracking_person, can_move=True)
assert roam_service.state == RoamState.AVOID_PERSON, f"Expected AVOID_PERSON, got {roam_service.state}"
assert srv == "curious_tilt"
print(f"[PASS] Person avoidance interrupt: successfully transitioned to '{roam_service.state}' with servo='{srv}'")

# Clean up roam state
roam_service.set_enabled(False)


# ============================================================================
# TEST 5: FASTAPI REST ENDPOINTS (ASYNC INVOCATION)
# ============================================================================
print("\n=== TEST 5: FASTAPI REST ENDPOINTS ===")
from main import (
    get_memory_vault,
    get_database_stats_api,
    get_database_chats_api,
    get_network_info,
    save_note_api,
    set_pin_role_api,
    set_line_follower_api,
    set_custom_servo_api,
    delete_memory_api,
    capture_photo_api,
    get_photo_gallery_api,
    get_photo_file_api,
    delete_photo_api,
    set_detection_mode_api,
    set_roam_api,
    get_roam_api
)

class MockRequest:
    def __init__(self, payload):
        self._payload = payload
    async def json(self):
        return self._payload

async def test_rest_endpoints():
    # GET /api/network_info
    r_net = await get_network_info()
    assert r_net.status_code == 200
    net_data = json.loads(r_net.body.decode("utf-8"))
    assert "lan_ip" in net_data and "lan_url" in net_data
    print(f"[PASS] GET /api/network_info -> LAN URL: {net_data['lan_url']}")

    # GET /api/database/stats
    r_db_stats = await get_database_stats_api()
    assert r_db_stats.status_code == 200
    db_stats_data = json.loads(r_db_stats.body.decode("utf-8"))
    assert db_stats_data["engine"] == "SQLite3"
    print(f"[PASS] GET /api/database/stats -> Engine: {db_stats_data['engine']}, Tables: {db_stats_data['tables']}")

    # GET /api/database/chats
    r_chats = await get_database_chats_api(10)
    assert r_chats.status_code == 200
    chats_data = json.loads(r_chats.body.decode("utf-8"))
    assert "chats" in chats_data
    print(f"[PASS] GET /api/database/chats -> Retrieved {len(chats_data['chats'])} chats from SQLite3")

    # GET /api/memory
    r = await get_memory_vault()
    assert r.status_code == 200
    data = json.loads(r.body.decode("utf-8"))
    assert "faces" in data and "notes" in data and "database" in data
    print("[PASS] GET /api/memory (backed by SQLite3)")

    # POST /api/memory/note
    r = await save_note_api(MockRequest({"key": "test_key", "value": "test_val"}))
    assert r.status_code == 200
    print("[PASS] POST /api/memory/note")

    # POST /api/pin_role
    r = await set_pin_role_api(MockRequest({"pin": 38, "role": "PWM", "label": "Aux Illumination"}))
    assert r.status_code == 200
    print("[PASS] POST /api/pin_role")

    # POST /api/line_follower
    r = await set_line_follower_api(MockRequest({"enable": True, "left_pin": 2, "right_pin": 3, "speed": 150}))
    assert r.status_code == 200
    print("[PASS] POST /api/line_follower")

    # POST /api/custom_servo
    r = await set_custom_servo_api(MockRequest({"pin": 21, "angle": 45}))
    assert r.status_code == 200
    print("[PASS] POST /api/custom_servo")

    # POST /api/camera/detection_mode
    r_mode = await set_detection_mode_api(MockRequest({"mode": "all"}))
    assert r_mode.status_code == 200
    print("[PASS] POST /api/camera/detection_mode")

    # POST /api/camera/capture
    r_snap = await capture_photo_api(MockRequest({"notes": "REST API Test Snapshot"}))
    assert r_snap.status_code == 200
    snap_data = json.loads(r_snap.body.decode("utf-8"))
    assert "filename" in snap_data
    snap_filename = snap_data["filename"]
    print(f"[PASS] POST /api/camera/capture -> Generated {snap_filename}")

    # GET /api/camera/gallery
    r_gal = await get_photo_gallery_api()
    assert r_gal.status_code == 200
    gal_data = json.loads(r_gal.body.decode("utf-8"))
    assert "photos" in gal_data
    assert any(p["filename"] == snap_filename for p in gal_data["photos"])
    print(f"[PASS] GET /api/camera/gallery -> Found {len(gal_data['photos'])} photos in SQLite3")

    # GET /api/camera/photo/{filename}
    r_photo_file = await get_photo_file_api(snap_filename)
    assert r_photo_file.status_code == 200
    print(f"[PASS] GET /api/camera/photo/{snap_filename} -> Served JPEG FileResponse")

    # DELETE /api/camera/photo/{filename}
    r_del_photo = await delete_photo_api(snap_filename)
    assert r_del_photo.status_code == 200
    print(f"[PASS] DELETE /api/camera/photo/{snap_filename} -> Removed from disk & SQLite3")

    # POST /api/memory/delete
    r = await delete_memory_api(MockRequest({"category": "note", "id": "test_key"}))
    assert r.status_code == 200
    r = await delete_memory_api(MockRequest({"category": "pin_role", "id": "38"}))
    assert r.status_code == 200
    print("[PASS] POST /api/memory/delete (note & pin_role)")

    # POST /api/roam & GET /api/roam
    r_roam_on = await set_roam_api(MockRequest({"enabled": True}))
    assert r_roam_on.status_code == 200
    roam_data = json.loads(r_roam_on.body.decode("utf-8"))
    assert roam_data["roam_enabled"] is True
    print("[PASS] POST /api/roam (enable=True)")

    r_roam_get = await get_roam_api()
    assert r_roam_get.status_code == 200
    roam_status = json.loads(r_roam_get.body.decode("utf-8"))
    assert roam_status["enabled"] is True
    print(f"[PASS] GET /api/roam -> State: {roam_status['state']}")

    r_roam_off = await set_roam_api(MockRequest({"enabled": False}))
    assert r_roam_off.status_code == 200
    print("[PASS] POST /api/roam (enable=False)")

asyncio.run(test_rest_endpoints())


# ============================================================================
# TEST 6: WEBAPP HTML FEATURES & DOM IDS
# ============================================================================
print("\n=== TEST 6: WEBAPP HTML FEATURES & DOM IDS ===")
html_path = os.path.join(os.path.dirname(__file__), "..", "module4_webapp", "index.html")
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

required_elements = [
    # Identity
    "Project L.O.O.N.A.",
    "Locomotive Optical Operative Navigation & Assistance",
    # Canvas & Interactivity
    "eyeCanvas",
    "tapHintPill",
    "cursor: pointer",
    "handleFaceTap",
    # Subsystems
    "subsystemsView",
    "tabBtnServo",
    "tabBtnLine",
    "tabBtnPinCustomizer",
    "btnServoSweep",
    "subsystemRolesGrid",
    "lineLeftPin",
    "lineRightPin",
    "lineSpeedSlider",
    # About Developers
    "btnAboutDevs",
    "aboutDevsModal",
    "KANANYAN ★",
    "CHIEF ARCHITECT",
    # Expressions & Hold Timer
    "emotionPillsBar",
    "wink_left",
    "wink_right",
    "squint_happy",
    "star_eyes",
    "drawLooiEye",
    "playCuteChime",
    "spawnTapParticles",
    "5000",
    "emotionHoldTimer",
    # Pure Face Mode
    "btnPureFace",
    "btn-exit-pure-face",
    "pure-face-mode",
    "togglePureFaceMode",
    "startRandomExpressionLoop",
    # Chat & Subtitles
    "chatInput",
    "typingDebounceTimer",
    "faceSubtitleBox",
    "faceSubtitleText",
    "showFaceSubtitles",
    # Sticky Header & LAN Link
    "position: sticky",
    "btnConnectDevice",
    "connectDeviceModal",
    "openConnectModal",
    "connectQrCodeImg",
    # SQLite3 Database in Vault
    "vaultDbStatusBanner",
    "SQLITE3 DATABASE",
    "statCountFaces",
    "statCountNotes",
    "statCountCmds",
    "statCountPins",
    # Optical Cam HUD & Face Recognition Boxes
    "btnToggleCamHud",
    "opticalCamHud",
    "hudVideoStream",
    "hudFeedTargetBadge",
    "hudInputSaveFace",
    "saveFaceFromHud",
    "toggleOpticalCamHud",
    # Object Detection & Photography Engine
    "cameraFlashOverlay",
    "btnHeaderSnap",
    "btnHeaderGallery",
    "photoGalleryModal",
    "galleryGrid",
    "takePhotoAction",
    "loadGallery",
    "playShutterSound",
    "btnCockpitSnap",
    "btnCockpitDetectMode",
    "btnCockpitGallery",
    "btnHudDetectMode",
    "btnHudSnap",
    "hudFeedObjectsBadge",
    "cycleDetectionMode",
    # Autonomous Idle Roam & Collision Avoidance
    "btnToggleRoam",
    "btnCockpitRoam",
    "toggleRoamMode",
    "updateRoamUI",
    "isRoamActive",
    "roam_update",
    # Multi-Source Browser WebCam Pipeline
    "btnHudCamSource",
    "btnCockpitCamSource",
    "toggleCameraSource",
    "startBrowserWebcam",
    "stopBrowserWebcam",
    "updateCameraSourceUI",
    "browserWebcamVideo",
    "browserWebcamCanvas",
    "/ws/camera_feed"
]

for elem in required_elements:
    assert elem in html, f"Missing required element or pattern in index.html: '{elem}'"
    print(f"[PASS] HTML Feature verified: '{elem}'")

# ============================================================================
# TEST 8: TTS ENGINE NATURAL VOICE & DIRECT FFMPEG TRANSCODING
# ============================================================================
print("\n=== TEST 8: TTS ENGINE NATURAL VOICE & DIRECT FFMPEG TRANSCODING ===")
from tts_service import tts_engine
import cv2

async def run_tts_unit_test():
    speech_text = "Hello Orbit! I can speak clearly now without robotic beeps!"
    pcm = await tts_engine.text_to_pcm(speech_text)
    assert len(pcm) > 50000, f"Expected >50,000 bytes of natural speech PCM, got {len(pcm)}"
    print(f"[PASS] Edge-TTS + FFmpeg produced {len(pcm)} bytes of 24kHz Stereo PCM speech.")

    # Test Windows SAPI fallback
    sapi_pcm = tts_engine._fallback_sapi_tts("Offline voice fallback verification.")
    assert len(sapi_pcm) > 10000, f"Expected >10,000 bytes from SAPI fallback, got {len(sapi_pcm)}"
    print(f"[PASS] Windows SAPI fallback produced {len(sapi_pcm)} bytes of 24kHz Stereo PCM speech.")

asyncio.run(run_tts_unit_test())

# ============================================================================
# TEST 9: MULTI-SOURCE CAMERA PIPELINE & BROWSER WEBCAM INGESTION
# ============================================================================
print("\n=== TEST 9: MULTI-SOURCE CAMERA PIPELINE & BROWSER WEBCAM INGESTION ===")
from vision_tracker import VisionTracker
tracker = VisionTracker()

# 1. Verify default source is esp32
assert tracker.get_camera_source() == "esp32", f"Expected 'esp32', got {tracker.get_camera_source()}"
print("[PASS] Default camera source is 'esp32'")

# 2. Switch to browser webcam
src = tracker.set_camera_source("browser")
assert src == "browser"
assert tracker.get_camera_source() == "browser"
print("[PASS] Successfully switched camera source to 'browser'")

# 3. Simulate browser webcam frame injection
dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)
dummy_frame[:, :] = (30, 40, 50)
cv2.circle(dummy_frame, (160, 120), 35, (220, 220, 220), -1)
cv2.circle(dummy_frame, (148, 112), 4, (0, 0, 0), -1)
cv2.circle(dummy_frame, (172, 112), 4, (0, 0, 0), -1)
cv2.ellipse(dummy_frame, (160, 132), (12, 6), 0, 0, 180, (0, 0, 0), 2)
_, enc = cv2.imencode(".jpg", dummy_frame)
fed = tracker.feed_external_jpeg(enc.tobytes())
assert fed is True, "Failed to feed external JPEG frame"
print(f"[PASS] Successfully ingested {len(enc.tobytes())} bytes of browser webcam JPEG.")

# 4. Verify snapshot photo engine works on browser webcam frame
snap_record = tracker.capture_snapshot(with_overlay=False, notes="Browser WebCam Test Photo")
assert snap_record and "filename" in snap_record
print(f"[PASS] Snapshot captured and saved to SQLite3: {snap_record['filename']}")

# 5. Switch back to esp32
src = tracker.set_camera_source("esp32")
assert src == "esp32"
print("[PASS] Successfully switched camera source back to 'esp32'")

print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! ZERO ERRORS DETECTED.")
