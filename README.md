# LOONA - Smart Multimodal Desktop Companion & 4WD Rover

LOONA is a smart multimodal desktop robot and 4WD rover inspired by the LOOI robot. It combines computer vision, robotic locomotion, facial expression animations, and Google Gemini 1.5 Pro multimodal intelligence.

---

## Architecture Overview

```
========================================================================================================================
                                     LOONA ROBOT ARCHITECTURE (4WD SYSTEM)
========================================================================================================================
                                          +----------------------------------+
                                          |        SMARTPHONE / BROWSER      |
                                          |      (Local WebApp Dashboard)    |
                                          |      [ TOGGLE: MODE SWITCH ]     |
                                          | [COMPANION MODE]     [MANUAL MODE]
                                          | * LOONA Animated     * Virtual Joysticks
                                          |   Canvas Eyes (LERP) * Speed Sliders     
                                          | * Emotion States     * Override Tracking 
                                          +-----------------+----------------+
                                                            ^
                                             HTTP (Port 80) │  WebSocket (/ws/client)
                                             Static HTML/JS │  JSON {mode, cmd, gaze, state}
                                                            v
+----------------------------------------------------------------------------------------------------------------------+
|                                                 HOST PC / SERVER BRAIN                                               |
|   +-----------------------+     +--------------------------+     +------------------------+     +----------------+   |
|   |  FastAPI / WebSockets |     |     Command Router       |     |  STT & Gemini Service  |     |   TTS Engine   |   |
|   | * WebApp HTTP Server  |====>| -> Manual: Joysticks     |     | * Whisper Speech-to-Txt|     | * Convert text |   |
|   | * ESP32 UDP Endpoint  |     | -> Auto: OpenCV Tracking |     | * Gemini 1.5 Pro Chat  |     |   to PCM audio |   |
|   +-----------+-----------+     +------------+-------------+     +-----------+------------+     +-------+--------+   |
+---------------|------------------------------|-------------------------------|--------------------------|------------+
                ^                              |                               ^                          |
   WebSocket /  │                              │ UDP Datagrams                 │ Raw Audio (PCM)          │ Audio Stream
   MJPEG Stream │                              │ {"fwd": 120, "turn": 50}      │ 16kHz Mono               │ 24kHz Stereo
                v                              v                               v                          v
+----------------------------------------------------------------------------------------------------------------------+
|                                               HEAD CONTROLLER: ESP32-S3 CAM                                          |
|   [OV2640 Sensor]                   [INMP441 MEMS Mic]              [MAX98357A Amp]            [UART Inter-MCU]      |
|   * Frame fetch -> Stream           * I2S Port 0 (RX)               * I2S Port 1 (TX)          * TX: GPIO 17         |
|   * 320x240 @ 15+ FPS               * 16-bit, 16kHz                 * 16-bit, 24kHz            * RX: GPIO 16         |
+---------------|-------------------------------|-------------------------------|--------------------------|-----------+
                                  3-Wire Physical Link (UART + Common Ground)                              |
         ==================================================================================================+
         | CAM_TX (GPIO 17) --------------> DEVKIT_RX (GPIO 16)
         | CAM_RX (GPIO 16) <-------------- DEVKIT_TX (GPIO 1)
         | COMMON GND       --------------> COMMON GND
         ==================================================================================================+
                                                                                                           v
+----------------------------------------------------------------------------------------------------------------------+
|                                          CHASSIS & MOTION: ESP32-S3 DEVKITC                                          |
|   * Hardware UART Listener (115200 Baud) -> JSON Command Parser                                                      |
|   * ESP-IDF LEDC Hardware PWM Matrix (8 Channels utilized for 4 Motors)                                              |
|                                                                                                                      |
|         Front Axle Output                                                Rear Axle Output                            |
|   +--------------+---------------+                         +----------------------+----------------------+           |
|   | FRONT LEFT      FRONT RIGHT  |                         | REAR LEFT               REAR RIGHT          |           |
|   | RPWM->GPIO 4    RPWM->GPIO 7 |                         | RPWM->GPIO 17           RPWM->GPIO 9        |           |
|   | LPWM->GPIO 5    LPWM->GPIO 15|                         | LPWM->GPIO 18           LPWM->GPIO 10       |           |
|   +-------|--------------|-------+                         +-------|----------------------|--------------+           |
+-----------|--------------|-----------------------------------------|----------------------|--------------------------+
            v              v                                         v                      v
      +-----------+  +-----------+                             +-----------+          +-----------+
      | BTS7960 1 |  | BTS7960 2 |                             | BTS7960 3 |          | BTS7960 4 | 
      | Front L   |  | Front R   |                             | Rear L    |          | Rear R    |
      +-----------+  +-----------+                             +-----------+          +-----------+
========================================================================================================================
```

---

## Directory Structure

```
LOONA1/
├── module1_head_cam/              # Head Controller Firmware
│   ├── camera_pins.h              # Pin definitions for ESP32-S3 CAM boards
│   ├── config.h                   # WiFi credentials & Server IP/Port configuration
│   └── module1_head_cam.ino       # Main Arduino sketch (OV2640, Dual I2S, UDP->UART)
├── module2_chassis_motion/        # Chassis & Locomotion Firmware
│   ├── config.h                   # 4WD BTS7960 pin map, PWM channels, UART config
│   └── module2_chassis_motion.ino # Main Arduino sketch (UART, JSON, Tank Mixer, LEDC)
├── module3_python_brain/          # Host Brain Server
│   ├── config.py                  # P-controller gains, IPs, ports, Gemini settings
│   ├── vision_tracker.py          # MJPEG puller, Haar Cascade face detection, P-Controller
│   ├── ai_service.py              # Gemini 1.5 Pro multimodal chat & STT processing
│   ├── tts_service.py             # edge-tts to 24kHz raw PCM audio streaming
│   ├── main.py                    # FastAPI server, WebSockets, and UDP dispatcher
│   └── requirements.txt           # Python package dependencies
└── module4_webapp/                # Smartphone / Tablet Cyber Face & Controller
    └── index.html                 # Canvas Eyes (LERP), procedural blinking, touch joystick
```

---

## Quick Start Guide

### 1. Flashing Module 1 (Head: ESP32-S3 CAM)
1. Open [`module1_head_cam/module1_head_cam.ino`](file:///c:/Users/Kananyan/Desktop/LOONA1/module1_head_cam/module1_head_cam.ino) in Arduino IDE.
2. Install the **WebSockets** library by Markus Sattler via the Library Manager.
3. In `config.h`, set your `WIFI_SSID`, `WIFI_PASSWORD`, and `SERVER_HOST` (Host PC IP).
4. Board Settings:
   - Board: **ESP32S3 Dev Module**
   - PSRAM: **OPI PSRAM** (or QSPI depending on board)
   - Flash Size: **8MB** or **16MB**
5. Upload to your ESP32-S3 CAM board.

### 2. Flashing Module 2 (Chassis: ESP32-S3 DevKitC)
1. Open [`module2_chassis_motion/module2_chassis_motion.ino`](file:///c:/Users/Kananyan/Desktop/LOONA1/module2_chassis_motion/module2_chassis_motion.ino) in Arduino IDE.
2. Install the **ArduinoJson** library (v6 or v7).
3. Board Settings:
   - Board: **ESP32S3 Dev Module**
4. Connect BTS7960 motor driver pins as shown in the diagram.
5. Upload to the Chassis ESP32-S3 board.

### 3. Running the Python Server Brain (Module 3)
1. Open terminal in `module3_python_brain`:
   ```bash
   cd module3_python_brain
   pip install -r requirements.txt
   ```
2. (Optional) Set your Gemini API key in environment:
   ```powershell
   $env:GEMINI_API_KEY="your_api_key_here"
   ```
3. Launch the server:
   ```bash
   python main.py
   ```
4. Access the dashboard:
   - On Host PC: `http://localhost:8000`
   - On Smartphone/Tablet: `http://<HOST_PC_IP>:8000`

---

## ☾ LOONA (loonatheworld) Voice Protocols & Commands

| Voice / Chat Command | Action / Response |
| :--- | :--- |
| **"Hey LOONA, follow me"** | Activates active 4WD face-tracking locomotion across the Lunar path. LOONA confirms with idol speech and glowing crescent eyes, continuously steering to keep you in orbit. |
| **"Hey LOONA, stop"** | Immediately disengages chassis locomotion (`fwd=0, turn=0`), halts the rover, and returns to desk companion mode. |
| **"Dance" / "Choreography"** | Performs the LOONA K-Pop rover choreography (rhythmic forward/backward steps, sweeps, and turns) with glowing starry eyes! |
| **"Orbit spin" / "Spin"** | Executes a 360° celestial orbit spin at speed. |
| **Any questions or chat** | Multimodal reasoning via Gemini 1.5 Pro with LOONA (`loonatheworld`) idol persona ("Orbit"), analyzing camera vision in real time and speaking via high-pitch K-Pop/Anime neural voice presets. |

---

## ☾ K-Pop & Moon Voice Presets (MAX98357A I2S)
Available and switchable on-the-fly in the WebApp:
- 🌸 **K-Pop Idol (KR)**: `ko-KR-SunHiNeural` (+12% Pitch, +6% Rate) — Energetic, sparkling Korean idol voice.
- 🌙 **Lunar Goddess (KR)**: `ko-KR-InJoonNeural` (+4% Pitch, normal tempo) — Elegant, mysterious lunar persona.
- ✨ **K-Pop Star (EN)**: `en-US-AnaNeural` (+10% Pitch, +5% Rate) — Sweet bilingual idol tone.
- 🎌 **Anime Idol (EN)**: `en-US-JennyNeural` (+18% Pitch, +8% Rate) — Ultra-cute anime companion voice.



