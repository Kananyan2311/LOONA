# ✨💖 ☾ PROJECT L.O.O.N.A. (이달의 소녀) ☽ 💖✨
### 🎀 **L**ocomotive **O**ptical **O**perative for **N**avigation and **A**ssistance 🎀
#### *The World's Cutest Autonomous 4WD Desktop Companion & AI Rover Robot!*

<div align="center">

```
             ☆*:.｡.o(≧▽≦)o.｡.:*☆
        (\(\                          /)/)
       (='.')    ☾ PROJECT L.O.O.N.A. ☽  ('.'=)
      o_(")(")  "Hi High, Orbit! Let's roll!" (")(")_o
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          [ ◕   ‿   ◕ ]  <-- Butter-Smooth 60 FPS Cyber Eyes!
          |  L.O.O.N.A. |  <-- Living Expression Engine
         /|  ★ ORBIT ★  |\
        (O)============(O) <-- 20 kHz Ultrasonic Silent 4WD!
```

**"We are all connected in the LOONAverse!"** 🌌✨  
*An engineering project from **National University – Laguna** ANDMIXX TEAM (CPMICR1L: Microprocessor and Microcontroller Systems and Design)*

---

### 🌸 The 12 Girls of the Month & Their Official Subsystems 🌸

[![Heejin](https://img.shields.io/badge/01%20HeeJin%20🐰-Bright%20Pink%20%7C%20Companion%20Face-FF0055?style=for-the-badge&logoColor=white)](#1-heejin-희진--bright-pink--companion-face--60-fps-morphing-eyes-)
[![Hyunjin](https://img.shields.io/badge/02%20HyunJin%20🐱-Yellow%20%7C%20Auto%20Roam-FFCC00?style=for-the-badge&logoColor=black)](#2-hyunjin-현진--yellow--autonomous-idle-roam--avoidance-)
[![Haseul](https://img.shields.io/badge/03%20HaSeul%20🕊️-Forest%20Green%20%7C%20FastAPI%20Leader-009944?style=for-the-badge&logoColor=white)](#3-haseul-하슬--forest-green--system-orchestrator--fastapi-brain-)
[![Yeojin](https://img.shields.io/badge/04%20YeoJin%20🐸-Orange%20%7C%20IR%20Line%20Follower-F37321?style=for-the-badge&logoColor=white)](#4-yeojin-여진--orange--autonomous-tcrt5000-line-follower-)
[![Vivi](https://img.shields.io/badge/05%20ViVi%20🦌-Pastel%20Rose%20%7C%205--Axis%20Servos-F6B7C3?style=for-the-badge&logoColor=black)](#5-vivi-비비--pastel-rose--5-axis-servo-matrix--modular-arm-)
[![Kim Lip](https://img.shields.io/badge/06%20Kim%20Lip%20🦉-Eclipse%20Red%20%7C%20Direct%20UDP-ED1C24?style=for-the-badge&logoColor=white)](#6-kim-lip-김립--eclipse-red--high-speed-udp-port-8888-)
[![Jinsoul](https://img.shields.io/badge/07%20JinSoul%20🐟-Deep%20Blue%20%7C%20Dual%20I2S%20Audio-005BAC?style=for-the-badge&logoColor=white)](#7-jinsoul-진솔--deep-blue--full-duplex-i2s-digital-audio-)
[![Choerry](https://img.shields.io/badge/08%20Choerry%20🦇-Purple%20%7C%20Zero--UI%20Pure%20Face-7B2786?style=for-the-badge&logoColor=white)](#8-choerry-최리--purple--100-zero-ui-fullscreen-pure-face-)
[![Yves](https://img.shields.io/badge/09%20Yves%20🦢-Burgundy%20%7C%20Gemini%20Multimodal-800020?style=for-the-badge&logoColor=white)](#9-yves-이브--burgundy--google-gemini-multimodal-ai-)
[![Chuu](https://img.shields.io/badge/10%20Chuu%20🐧-Peach%20%7C%20Spotify%20%26%20TTS-F78C72?style=for-the-badge&logoColor=black)](#10-chuu-츄--peach--spotify-streamer--idol-tts-)
[![Go Won](https://img.shields.io/badge/11%20Go%20Won%20🦋-Eden%20Mint%20%7C%20Standalone%20Web-30A39C?style=for-the-badge&logoColor=white)](#11-go-won-고원--eden-mint--standalone-chassis-web-controller-)
[![Hyeju](https://img.shields.io/badge/12%20HyeJu%20🐺-Silver%20%7C%2020kHz%20Silent%204WD-C0C0C0?style=for-the-badge&logoColor=black)](#12-hyeju-혜주--silvercharcoal--20-khz-silent-4wd-bts7960-)
[![Orbit](https://img.shields.io/badge/★%20Orbit%20✨-Prismatic%20Light%20%7C%20The%20Pilot-FFFFFF?style=for-the-badge&logoColor=black)](#-meet-orbit-the-pilot-)

</div>

---

## 🎀 Table of Contents (목차)
- [✨ What is Project L.O.O.N.A.?](#-what-is-project-loona)
- [🌌 The 12 LOONA Members & Subsystem Lore](#-the-12-loona-members--subsystem-lore)
- [🕹️ High-Level System Architecture](#️-high-level-system-architecture)
- [📂 Full Project Directory Structure](#-full-project-directory-structure)
- [🌸 Deep Dive: The 4 Core Modules](#-deep-dive-the-4-core-modules)
  - [🕊️ Module 1: Head Controller (ESP32-S3 CAM)](#-module-1-head-controller-esp32-s3-cam-jinsoul--haseul)
  - [🐺 Module 2: Chassis & Motion Controller (ESP32-S3 DevKitC)](#-module-2-chassis--motion-controller-esp32-s3-devkitc-hyeju-go-won--vivi)
  - [🦢 Module 3: Host Python Brain & Multimodal AI Hub](#-module-3-host-python-brain--multimodal-ai-hub-yves-chuu--kim-lip)
  - [🐰 Module 4: WebApp Cockpit & Cyber Face Dashboard](#-module-4-webapp-cockpit--cyber-face-dashboard-heejin--choerry)
- [🔌 Hardware Pinout Matrix](#-hardware-pinout-matrix)
- [⚡ Power System & Battery Architecture](#-power-system--battery-architecture)
- [💬 Cute Voice Commands & Idol Easter Eggs](#-cute-voice-commands--idol-easter-eggs)
- [🚀 Quick Start & Flashing Guide](#-quick-start--flashing-guide)
- [🌐 REST API & WebSocket Reference](#-rest-api--websocket-reference)
- [🧪 10-Tier Verification Benchmark](#-10-tier-verification-benchmark)
- [💌 The 6 Developers Behind LOONA](#-the-6-developers-behind-loona)

---

## ✨ What is Project L.O.O.N.A.?

**Project L.O.O.N.A.** (*Locomotive Optical Operative for Navigation and Assistance*) is a lovable, intelligent, and fiercely capable companion robot! Inspired by the legendary K-Pop group **LOONA (이달의 소녀)** and the adorable **LOOI** cybernetic desktop companion, LOONA bridges the gap between cute anime/K-Pop aesthetics and serious, publication-grade robotics engineering.

Behind her charming morphing cyber eyes and pastel retro-arcade interface lies a **distributed 4-tier cyber-physical architecture**:
- **Eyes & Vision**: 30 FPS OpenCV face and object tracking with proportional (P) closed-loop following!
- **Ears & Digital Hearing**: Full-duplex digital I2S audio with an omnidirectional MEMS microphone (INMP441) and real-time Cockpit VU meter!
- **Mouth & Idol Voice**: Dual-device audio output streaming rich 24 kHz speech to both the robot's onboard speaker (MAX98357A) and your smartphone speakers!
- **Legs & Locomotion**: 4WD BTS7960 matrix driven by **20 kHz ultrasonic silent PWM**—100% whisper quiet with zero annoying motor whine!
- **Mind & Memory**: Google Gemini multimodal vision reasoning paired with an embedded **SQLite3 Memory Vault** that remembers your name, stores photos, and completely solves AI memory leaks!
- **Pure Face Zen Mode**: 100% Zero-UI Fullscreen experience with continuous silent microphone listening!

---

## 🌌 The 12 LOONA Members & Subsystem Lore

In the **LOONAverse**, every girl has a color, an animal, and a special power. In Project L.O.O.N.A., each member embodies a critical engineering subsystem:

### 1. HeeJin (희진) • Bright Pink (`#FF0055`) • 🐰 Rabbit
> *"It's vivid, like a dream that came alive!"*  
- **Subsystem**: **Companion Face & 60 FPS Morphing Cyber Eyes** (`module4_webapp/index.html`)
- **Features**: Procedural 2D HTML5 canvas eyes with smooth cubic Bézier curves, gaze lerping, organic blinks, and living emotion transitions (`happy`, `wink`, `hearts`, `star_eyes`, `squint_happy`, `surprised`, `dizzy`). Just like HeeJin opened the LOONAverse in 2016, her vivid pink charm opens LOONA's soul!

### 2. HyunJin (현진) • Yellow (`#FFCC00`) • 🐱 Cat
> *"Around you, quietly watching over your steps!"*  
- **Subsystem**: **Autonomous Idle Roam & Collision Avoidance Engine** (`roam_service.py`)
- **Features**: Playful and curious like a cat! When LOONA is left idle, HyunJin's state machine takes over, gracefully navigating around furniture and people, pausing to tilt her head, and retreating with surprised eyes if obstacles get too close.

### 3. HaSeul (하슬) • Forest Green (`#009944`) • 🕊️ White Bird
> *"Let me in, I'll harmonize our whole universe!"*  
- **Subsystem**: **System Orchestrator & FastAPI Brain Server Hub** (`main.py`)
- **Features**: The wise, caring leader who unites all 4 modules. Coordinates asynchronous WebSocket channels (`/ws/client`, `/ws/audio`, `/ws/camera_feed`), 25 Hz telemetry broadcasts, database updates, and fail-safes into a peaceful, harmonious symphony!

### 4. YeoJin (여진) • Orange (`#F37321`) • 🐸 Frog
> *"Kiss later, let's explore every corner first!"*  
- **Subsystem**: **Autonomous TCRT5000 IR Line Follower** (`module2_chassis_motion.ino`)
- **Features**: The energetic maknae! Reads dual infrared reflectance sensors on GPIO 2 & 3 with closed-loop tank steering, zipping along black or white floor tracks with playful precision.

### 5. ViVi (비비) • Pastel Rose (`#F6B7C3`) • 🦌 Deer
> *"Everyday I love you, my robotic heart beats for you!"*  
- **Subsystem**: **5-Axis Physical Servo Matrix & Modular Arm Add-on** (`module2_chassis_motion.ino`)
- **Features**: The physical android embodiment! Controls 5 built-in servos (Head Pan, Head Tilt, Left Ear, Right Ear, and Tail Wag) with 50 Hz PWM. Also hosts the dynamic auxiliary expansion bus for the **quick-disconnect Modular Robotic Arm Add-on Attachment**!

### 6. Kim Lip (김립) • Eclipse Red (`#ED1C24`) • 🦉 Owl
> *"An eclipse of blazing speed that never drops a packet!"*  
- **Subsystem**: **High-Speed Direct UDP Datagram Engine & 800ms Watchdog** (`main.py` & `module2`)
- **Features**: Blazing fast red-hot teleoperation! Transmits motion packets at 25 Hz over UDP port 8888 with **<1ms execution latency**. Enforces a strict 800ms electronic emergency brake failsafe if connection drops.

### 7. JinSoul (진솔) • Deep Blue (`#005BAC`) • 🐟 Blue Betta Fish
> *"Singing in the rain, pure digital audio flowing like water!"*  
- **Subsystem**: **Full-Duplex I2S Digital Audio Link** (`module1_head_cam.ino`)
- **Features**: Eliminates noisy analog microphones forever! Drives an INMP441 MEMS microphone on I2S Port 0 RX (16 kHz, 16-bit Mono) and a MAX98357A 3.2W amplifier on I2S Port 1 TX (24 kHz, 16-bit Stereo/Mono) across dual-core FreeRTOS tasks.

### 8. Choerry (최리) • Purple (`#7B2786`) • 🦇 Fruit Bat
> *"Love cherry motion, stepping through the portal into pure zero-UI!"*  
- **Subsystem**: **100% Zero-UI Fullscreen Pure Face Mode** (`index.html`)
- **Features**: A magical dimensional shift! Hides every single button, header, badge, and watermark. Only LOONA's glowing cyan eyes fill the 100vw × 100vh display on a midnight canvas, while the microphone listens silently in the background! Exits smoothly on double-tap or double-click.

### 9. Yves (이브) • Burgundy (`#800020`) • 🦢 Swan
> *"A new life, intelligent multimodal reasoning at its finest!"*  
- **Subsystem**: **Google Gemini Multimodal AI & Cognitive Core** (`ai_service.py`)
- **Features**: Masterminds high-level intelligence! Simultaneously analyzes user speech and camera frames, understanding objects, solving questions, executing structured robot actions, and keeping user context alive.

### 10. Chuu (츄) • Peach / Coral (`#F78C72`) • 🐧 Penguin
> *"Heart attack! Sweet idol voice and endless music streaming!"*  
- **Subsystem**: **Spotify Music Streamer & K-Pop Idol Edge-TTS** (`spotify_service.py` & `tts_service.py`)
- **Features**: Pure sunshine and idol energy! Direct Spotify integration streams songs like *"Hi High"* straight to the robot's speaker via ffmpeg. Speaks in warm, melodic K-Pop idol voice presets with sentence-timed subtitles!

### 11. Go Won (고원) • Eden Mint (`#30A39C`) • 🦋 Butterfly
> *"One and only, fluttering completely free from cables!"*  
- **Subsystem**: **Standalone ESP32-S3 Chassis Web Controller & SoftAP** (`module2_chassis_motion.ino`)
- **Features**: True wireless independence! Hosts a complete retro-cyberpunk Web Controller directly on HTTP Port 80 from flash memory. If your Wi-Fi router is offline, Go Won automatically spins up the `LOONA-CHASSIS-CONTROLLER` SoftAP hotspot so you can drive directly from your phone!

### 12. HyeJu (혜주 - Olivia Hye) • Silver / Charcoal (`#C0C0C0`) • 🐺 Wolf
> *"Egoist, fierce and unstoppable silent 4WD power!"*  
- **Subsystem**: **20 kHz Ultrasonic Silent 4WD BTS7960 Matrix** (`module2_chassis_motion.ino`)
- **Features**: Raw, silent power! Channels 4 independent BTS7960 43A MOSFET H-bridges through 8 LEDC PWM channels at **20,000 Hz**. Eliminates all audible motor whine (0 dB acoustic whine), conquering any surface with silent tank-drive dominance!

### ★ Meet Orbit (오빛) • The Pilot!
> You are **Orbit**! The human friend, companion, and commander of LOONA. Your name is celebrated throughout the system, stored in the SQLite3 vault, and displayed proudly on the Cockpit HUD!

---

## 🕹️ High-Level System Architecture

```
========================================================================================================================
                                     PROJECT L.O.O.N.A. DISTRIBUTED ROBOTICS TOPOLOGY
========================================================================================================================
                                           +----------------------------------+
                                           |     SMARTPHONE / TABLET / PC     |
                                           |    (Module 4: WebApp Cockpit)    |
                                           |   [COMPANION MODE] [MANUAL MODE] |
                                           |   * 60 FPS Morphing Canvas Eyes  |
                                           |   * 100% Zero-UI Fullscreen Pure |
                                           |   * Touch D-Pad / Dual Joysticks |
                                           |   * Live Telemetry & VU Meter    |
                                           +-----------------+----------------+
                                                             ^
                                              HTTP (Port 80) │  WebSocket (/ws/client)
                                              Static HTML/JS │  JSON {mode, cmd, gaze, state, audio}
                                                             v
+----------------------------------------------------------------------------------------------------------------------+
|                                     MODULE 3: HOST PYTHON BRAIN & MULTIMODAL AI HUB                                  |
|   +-----------------------+     +--------------------------+     +------------------------+     +----------------+   |
|   |  FastAPI & WebSockets |     |  OpenCV Vision Tracker   |     |  STT & Gemini Service  |     |   TTS Engine   |   |
|   | * WebApp HTTP Server  |====>| * Haar Face Centroid     |====>| * Silero VAD + Whisper |====>| * Edge-TTS     |   |
|   | * /ws/client & /audio |     | * Proportional (P) Loop  |     | * Gemini 1.5 Multi-turn|     | * 24kHz Stereo |   |
|   | * Direct UDP 8888 Tx  |     | * Multi-Camera Pipeline  |     | * SQLite3 Memory Vault |     |   PCM Pacer    |   |
|   +-----------+-----------+     +------------+-------------+     +-----------+------------+     +-------+--------+   |
+---------------|------------------------------|-------------------------------|--------------------------|------------+
                ^                              |                               ^                          |
   WebSocket /  │                              │ High-Speed UDP Datagrams      │ Raw Audio (PCM)          │ Audio Stream
   MJPEG Stream │                              │ Port 8888: {"fwd", "turn",    │ 16kHz Mono (INMP441)     │ 24kHz Stereo
   (320x240)    │                              │             "servos", "pins"} │                          │ (MAX98357A)
                v                              |                               v                          v
+----------------------------------------------v-----------------------------------------------------------------------+
|                                    MODULE 1: HEAD CONTROLLER (ESP32-S3 CAM)                                          |
|   [OV5640 / OV2640 Sensor]                  [INMP441 MEMS Mic]              [MAX98357A Amp]            [UART Link]   |
|   * MJPEG Streaming on Core 0               * I2S Port 0 (RX) on Core 1     * I2S Port 1 (TX) on Core 1* TX: GPIO 36 |
|   * 320x240 @ 30 FPS                        * 16-bit, 16kHz Mono            * 16-bit, 24kHz Stereo     * RX: GPIO 35 |
+----------------------------------------------------------------------------------------------------------------------+
                                               |
                          Direct Wi-Fi UDP 8888 Datagrams (<1ms latency)
                          + Auxiliary UART Backup Link (CAM GPIO 36 -> Chassis GPIO 21)
                                               v
+----------------------------------------------------------------------------------------------------------------------+
|                                MODULE 2: CHASSIS & MOTION CONTROLLER (ESP32-S3 DEVKITC)                              |
|   * Standalone Web Server (Port 80) serving Retro Cyberpunk D-Pad Controller + SoftAP 'LOONA-CHASSIS-CONTROLLER'     |
|   * Direct UDP Port 8888 Receiver + 800ms Safety Watchdog Auto-Braking                                               |
|   * 8-Channel 20 kHz Ultrasonic LEDC PWM Matrix (100% Silent 4WD BTS7960 Driving)                                    |
|   * 5-Axis Built-in Servo Matrix (Head Pan, Tilt, Left Ear, Right Ear, Tail Wag)                                     |
|   * Dynamic Expansion GPIOs (GPIO 2, 3, 21, 38) + Custom Servos + Autonomous TCRT5000 IR Line Follower              |
|   * Modular Add-On Attachment Bus: Quick-Disconnect Multi-Axis Robotic Arm                                           |
|                                                                                                                      |
|         Front-Left Motor             Rear-Left Motor              Front-Right Motor            Rear-Right Motor      |
|         RPWM: GPIO 4                 RPWM: GPIO 6                 RPWM: GPIO 15                RPWM: GPIO 17         |
|         LPWM: GPIO 5                 LPWM: GPIO 7                 LPWM: GPIO 16                LPWM: GPIO 18         |
|              │                            │                            │                            │                |
|              v                            v                            v                            v                |
|        +------------+               +------------+               +------------+               +------------+         |
|        |  BTS7960 1 |               |  BTS7960 2 |               |  BTS7960 3 |               |  BTS7960 4 |         |
|        |  (Front L) |               |  (Rear L)  |               |  (Front R) |               |  (Rear R)  |         |
|        +------------+               +------------+               +------------+               +------------+         |
========================================================================================================================
```

---

## 📂 Full Project Directory Structure

```
LOONA1/
├── module1_head_cam/                       # 🕊️ JinSoul & HaSeul: Real-Time Head Controller
│   ├── camera_pins.h                       # Camera pinout mapping for ESP32-S3 CAM boards
│   ├── config.h                            # Wi-Fi SSID/Pass, Server IP, I2S Pinouts, Ports
│   └── module1_head_cam.ino                # Dual-Core Firmware: 30 FPS MJPEG + Full-Duplex Dual I2S
│
├── module2_chassis_motion/                 # 🐺 HyeJu, Go Won, YeoJin & ViVi: Chassis & Motion Controller
│   ├── config.h                            # 4WD BTS7960 pins, 20kHz PWM, 5 Servos, Wi-Fi, SoftAP
│   └── module2_chassis_motion.ino          # Firmware: Web Controller (Port 80), UDP 8888, 4WD Tank Mixer,
│                                           # 5-Axis Servos, Dynamic GPIOs, Line Follower, Watchdog
│
├── module3_python_brain/                   # 🦢 Yves, Chuu & Kim Lip: Cognitive Multimodal Brain
│   ├── data/                               # Persistent Storage Directory
│   │   ├── captures/                       # High-resolution JPEG photo captures & snapshots
│   │   ├── loona_database.db               # SQLite3 Persistent Relational Database Vault
│   │   └── loona_memory.json               # JSON memory cache & fallback state
│   ├── .env                                # Local environment secrets (GEMINI_API_KEY, etc.)
│   ├── .env.example                        # Template environment file
│   ├── ai_service.py                       # Google Gemini multimodal vision chat & structured tool calls
│   ├── config.py                           # P-controller gains, network IPs, audio rates, servo defaults
│   ├── database.py                         # SQLite3 engine: faces, commands, notes, pin roles, chat audit
│   ├── main.py                             # FastAPI server, WebSockets (/ws/client, /ws/audio), 25Hz UDP
│   ├── memory_service.py                   # High-level memory vault service wrapper
│   ├── requirements.txt                    # Python package dependencies
│   ├── roam_service.py                     # Autonomous idle roaming & obstacle/person avoidance state machine
│   ├── scratch_test_all.py                 # Comprehensive 10-tier automated unit & integration test suite
│   ├── spotify_service.py                  # Official Spotify Web API & raw PCM speaker stream decoder
│   ├── tts_service.py                      # Edge-TTS / Kokoro 24kHz PCM generator with dynamic rate pacing
│   └── vision_tracker.py                   # Multi-source OpenCV tracking pipeline (ESP32, WebCam, USB)
│
├── module4_webapp/                         # 🐰 HeeJin & Choerry: Cyber Companion Dashboard
│   └── index.html                          # Single-Page WebApp: 60 FPS Morphing Eyes, 100% Zero-UI Pure
│                                           # Face Mode, Touch D-Pad, Cockpit VU Meter, Camera HUD, Gallery
│
├── LOONA_PROJECT_PAPER_REQUIREMENTS.txt    # Formal academic system specification & design paper
└── README.md                               # Project documentation & LOONAverse handbook
```

---

## 🌸 Deep Dive: The 4 Core Modules

### 🕊️ Module 1: Head Controller (ESP32-S3 CAM) — *JinSoul & HaSeul*
- **30 FPS MJPEG Video Streaming**: Ingests frames from OV5640 / OV2640 in QVGA format (320x240) on Core 0. Optimized with double-buffering in PSRAM to eliminate Wi-Fi congestion.
- **Full-Duplex Dual I2S Protocol**:
  - **I2S0 (RX)**: Samples INMP441 MEMS microphone at 16,000 Hz, 16-bit Mono on Core 1, delivering raw frames to the server over WebSocket.
  - **I2S1 (TX)**: Feeds MAX98357A 3.2W Class-D amplifier at 24,000 Hz, 16-bit Stereo/Mono for sparkling K-Pop speech playback.
- **Auxiliary Hardware Serial Link**: Pins `TX: GPIO 36` and `RX: GPIO 35` provide physical UART backup to the chassis.

---

### 🐺 Module 2: Chassis & Motion Controller (ESP32-S3 DevKitC) — *HyeJu, Go Won & ViVi*
- **20 kHz Ultrasonic Silent PWM**: Utilizes 8 LEDC hardware channels at 20,000 Hz (`FL: 4/5`, `RL: 6/7`, `FR: 15/16`, `RR: 17/18`). Operating above human hearing threshold delivers whisper-quiet locomotion with **0 dB audible motor whine**!
- **Differential Tank Mixer**: Translates forward/reverse speed and angular yaw into left/right wheel duties with proportional saturation clipping.
- **5-Axis Servo Matrix**: Drives Head Pan (GPIO 8), Head Tilt (GPIO 11), Left Ear (GPIO 12), Right Ear (GPIO 13), and Tail Wag (GPIO 14) at 50 Hz.
- **Standalone Web Controller (Port 80)**: Serves an embedded retro-cyberpunk controller interface with touch D-pad, keyboard WASD controls, speed slider, and live telemetry!
- **Fallback SoftAP Hotspot**: Automatically spins up `LOONA-CHASSIS-CONTROLLER` (IP: `192.168.4.1`, Pass: `12345678`) if the router is unreachable, ensuring you can always drive from your phone!
- **Direct UDP Port 8888**: Ingests 25 Hz packets directly from Python Brain with <1ms latency.
- **800ms Watchdog Safety Failsafe**: Automatically stops all motors if communication packets cease.
- **Autonomous Line Follower**: TCRT5000 IR reflectance sensors on GPIO 2 & 3 steer the rover along black/white floor lines.
- **Modular Robotic Arm Add-on Bus**: Supports optional quick-disconnect robotic arms on dynamic expansion GPIOs (`GPIO 2, 3, 21, 38`).

---

### 🦢 Module 3: Host Python Brain & Multimodal AI Hub — *Yves, Chuu & Kim Lip*
- **FastAPI Core Hub**: Serves the Cockpit WebApp, manages `/ws/client` telemetry and `/ws/audio` audio streaming.
- **OpenCV Face Tracking P-Controller**: Analyzes video frames, detects human faces, and calculates proportional tracking velocities:
  $$\text{turn} = -\Delta x \times 0.85 \times 255.0, \quad \text{fwd} = (70 - \text{face\_width}) \times 0.60 \times 2.0$$
  Includes an 8% deadband to eliminate motor oscillations when centered.
- **Google Gemini Multimodal AI**: Ingests user speech alongside high-res snapshots. Supports real-time tool calling (taking photos, perking ears, dancing, roaming).
- **SQLite3 Persistent Memory Vault (`loona_database.db`)**: Offloads all conversational history, facial profiles, and pin roles into relational SQLite3 storage—**permanently eliminating AI memory degradation!**
- **Dual-Channel Voice Output**: Audio plays simultaneously through the physical robot MAX98357A speaker and connected smartphone browser speakers!
- **Spotify Music Streamer**: Direct Spotify integration searches and streams 24 kHz raw PCM audio through ffmpeg straight to the robot's speaker!
- **Autonomous Roaming Engine**: Wanders when idle, detects obstacles, and performs cute evasive maneuvers.

---

### 🐰 Module 4: WebApp Cockpit & Cyber Face Dashboard — *HeeJin & Choerry*
- **60 FPS Procedural Morphing Eye Canvas**: LOOI-inspired cyan cyber eyes with organic blinking, gaze wander, and living expressions (`happy`, `wink_left`, `wink_right`, `hearts`, `star_eyes`, `squint_happy`, `surprised`, `dizzy`, `sleepy`).
- **100% Zero-UI Fullscreen Pure Face Mode**: One tap hides all buttons, headers, and UI elements. The animated eyes fill the entire screen edge-to-edge on a pitch-black background.
- **Silent Always-On Continuous Microphone**: Speech recognition listens continuously in the background without on-screen banners. Speak freely anytime!
- **Seamless Exit Controls**: Double-tap anywhere on mobile, double-click on desktop, press `Esc` / `Backspace`, or swipe out of fullscreen to return to the cockpit.
- **Arcade Cockpit**: Virtual touch joystick, max speed slider, servo sliders, optical camera HUD, photo gallery modal, and INMP441 VU meter with instant 3-second recording tester.

---

## 🔌 Hardware Pinout Matrix

### 🕊️ Module 1: Head Controller (ESP32-S3 CAM)
| Pin Label | GPIO Pin | Connected Peripheral | Protocol / Function |
|:---|:---:|:---|:---|
| **CAM_DVP** | `GPIO 4 - 18, 36 - 37` | OV5640 / OV2640 Sensor | 8-Bit DVP Parallel Video Bus |
| **I2S_MIC_SD** | `GPIO 39` | INMP441 MEMS Microphone | I2S0 Serial Data (SD) RX |
| **I2S_MIC_SCK** | `GPIO 38` | INMP441 MEMS Microphone | I2S0 Serial Clock (SCK) |
| **I2S_MIC_WS** | `GPIO 37` | INMP441 MEMS Microphone | I2S0 Word Select (WS) |
| **I2S_SPK_DIN** | `GPIO 42` | MAX98357A 3.2W Amplifier | I2S1 Data Input (DIN) TX |
| **I2S_SPK_BCLK** | `GPIO 1` | MAX98357A 3.2W Amplifier | I2S1 Bit Clock (BCLK) |
| **I2S_SPK_LRC** | `GPIO 2` | MAX98357A 3.2W Amplifier | I2S1 Left/Right Clock (LRC) |
| **I2C_SCL / SDA** | `GPIO 41 / 40` | OLED Display / Sensors | I2C Peripheral Bus |
| **CAM_UART_TX** | `GPIO 36` | Chassis MCU (Aux Link) | Inter-MCU Serial1 TX (115200 Baud) |
| **CAM_UART_RX** | `GPIO 35` | Chassis MCU (Aux Link) | Inter-MCU Serial1 RX (115200 Baud) |
| **5V / GND** | `5V / GND` | MP1584EN Regulator 1 (5V 3A) | Regulated Logic Power |

### 🐺 Module 2: Chassis & Motion Controller (ESP32-S3 DevKitC)
| Function | GPIO Pin | Hardware Mapping | Details |
|:---|:---:|:---|:---|
| **FL_RPWM / LPWM** | `GPIO 4 / 5` | BTS7960 1 (Front-Left) | Forward / Reverse PWM (LEDC Ch 0/1, 20 kHz) |
| **RL_RPWM / LPWM** | `GPIO 6 / 7` | BTS7960 2 (Rear-Left) | Forward / Reverse PWM (LEDC Ch 2/3, 20 kHz) |
| **FR_RPWM / LPWM** | `GPIO 15 / 16` | BTS7960 3 (Front-Right) | Forward / Reverse PWM (LEDC Ch 4/5, 20 kHz) |
| **RR_RPWM / LPWM** | `GPIO 17 / 18` | BTS7960 4 (Rear-Right) | Forward / Reverse PWM (LEDC Ch 6/7, 20 kHz) |
| **SERVO_PAN** | `GPIO 8` | Head Pan Servo (Servo 1) | 50 Hz PWM (0° - 180° Horizontal Sweep) |
| **SERVO_TILT** | `GPIO 11` | Head Tilt Servo (Servo 2) | 50 Hz PWM (0° - 180° Vertical Elevation) |
| **SERVO_LEAR** | `GPIO 12` | Left Ear Servo (Servo 3) | 50 Hz PWM (Expressive Perk & Wiggle) |
| **SERVO_REAR** | `GPIO 13` | Right Ear Servo (Servo 4) | 50 Hz PWM (Expressive Perk & Wiggle) |
| **SERVO_TAIL** | `GPIO 14` | Tail Wag Servo (Servo 5) | 50 Hz PWM (Playful Canine Wagging) |
| **CHASSIS_RX / TX** | `GPIO 21 / 1` | Head MCU (Aux Link) | Inter-MCU Serial1 Link (115200 Baud) |
| **EXP_PIN_1 / 2** | `GPIO 2 / 3` | TCRT5000 IR Sensors / Aux | Dynamic Expansion / Line Follower Left & Right |
| **EXP_PIN_3** | `GPIO 38` | Aux Illumination / Relays | Dynamic Expansion (Digital / PWM) |
| **MODULAR_ARM** | `Expansion` | Dynamic Auxiliary Servos | Quick-disconnect robotic arm attachment |

> ⚠️ **Important**: All `R_EN` and `L_EN` pins on all 4 BTS7960 driver boards are connected to **3.3V Logic HIGH** to enable output stages continuously.

---

## ⚡ Power System & Battery Architecture

```
+-----------------------------------------------------------------------------------+
|                           11.1V - 12.6V 3S2P Li-ion Pack                          |
|                       (6x 18650 Cells, 5200 mAh, 25A BMS)                         |
+-----------------------------------------+-----------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v [Raw 12V High-Current Rail]       v [Raw 12V Logic Input]
       +------------------------------------+   +------------------------------------+
       |   4x BTS7960 H-Bridge Power Bus    |   | 2x MP1584EN Step-Down Regulators   |
       |  (1000uF 25V Low-ESR Filter Cap)   |   |                                    |
       |  Powers 4WD High-Torque DC Motors  |   | -> Reg 1: 5.0V @ 3A (ESP32 Logic,  |
       +------------------------------------+   |           CAM Sensor, MAX98357A)   |
                                                |                                    |
                                                | -> Reg 2: 6.0V @ 5A (Dedicated 5x  |
                                                |           Servos & Modular Arm)    |
                                                +------------------------------------+
                                                                    |
                                          ==========================v================
                                          ★ STAR COMMON GROUND (Eliminates ground loops)
```

- **Independent Servo Rail**: Servos are powered strictly from the dedicated 6.0V 5A regulator. Servos are **NEVER** powered from the ESP32 3.3V pin, preventing brownouts and inductive microcontroller resets!
- **Flyback Absorption**: A 1000µF 25V low-ESR electrolytic capacitor across the raw 12V motor driver rail absorbs motor back-EMF spikes during rapid directional braking.

---

## 💬 Cute Voice Commands & Idol Easter Eggs

Speak naturally to LOONA! The built-in voice parser recognizes both direct hardware actions and natural conversational queries:

| Voice / Chat Command | Action & Physical Response | Member Emoji |
|:---|:---|:---:|
| **"Hey LOONA, follow me"** | Locks optical face tracking and engages 4WD locomotion to follow you across the room! | 🐰 HeeJin |
| **"Stop" / "Hey LOONA, stop"** | Instantly halts all locomotive motion (`fwd=0, turn=0`), stops music, and resets emotion to neutral. | 🐺 HyeJu |
| **"Start roaming" / "Roam around"** | Engages autonomous idle roaming with obstacle and human collision avoidance. | 🐱 HyunJin |
| **"Stop roaming"** | Disengages autonomous roaming and returns to standing desk companion mode. | 🕊️ HaSeul |
| **"Take a picture" / "Snap a photo"** | Takes a high-resolution snapshot with screen flash, saves it to the gallery, and registers in SQLite3! | 🦇 Choerry |
| **"Play music" / "Play Hi High"** | Searches and streams music via Spotify directly into the robot MAX98357A speaker! | 🐧 Chuu |
| **"Perk ears" / "Twitch ears"** | Actuates left and right ear servos in cute asymmetric rabbit twitches! | 🦌 ViVi |
| **"Wag tail"** | Wags the tail servo back and forth in playful companion mode! | 🐸 YeoJin |
| **"Curious tilt"** | Executes a 45° head tilt with an inquisitive ocular expression! | 🦉 Kim Lip |
| **"Dance" / "Choreography"** | Performs a rhythmic sequence of forward-reverse steps, pivot turns, and starry eyes! | 🦢 Yves |
| **"Orbit spin"** | Executes a swift 360° celestial pivot spin on the spot! | 🦋 Go Won |
| **Any conversation or question** | Multimodal reasoning via Google Gemini, spoken aloud in sweet idol voice with live face subtitles! | ✨ Orbit |

---

## 🚀 Quick Start & Flashing Guide

### 1. Prerequisites
- **Arduino IDE 2.x** with **ESP32 Board Package (v2.x or v3.x)**.
- **Python 3.10+** (64-bit) with `pip` and `virtualenv`.
- **FFmpeg** installed and added to system `PATH`.
- High-drain 3S Li-ion battery pack (11.1V - 12.6V).

---

### 2. Flashing Module 1 (Head: ESP32-S3 CAM)
1. Open [`module1_head_cam/module1_head_cam.ino`](file:///c:/Users/Kananyan/Desktop/LOONA1/module1_head_cam/module1_head_cam.ino) in Arduino IDE.
2. In Library Manager, install:
   - `WebSockets` by Markus Sattler
   - `ArduinoJson` (v6 or v7)
3. In `config.h`, set your `WIFI_SSID`, `WIFI_PASSWORD`, and `SERVER_HOST` (Host PC IP).
4. Tools menu settings:
   - **Board**: `ESP32S3 Dev Module`
   - **PSRAM**: `OPI PSRAM`
   - **Flash Size**: `16MB` (or `8MB`)
5. Connect your ESP32-S3 CAM via USB-C and hit **Upload**.

---

### 3. Flashing Module 2 (Chassis: ESP32-S3 DevKitC)
1. Open [`module2_chassis_motion/module2_chassis_motion.ino`](file:///c:/Users/Kananyan/Desktop/LOONA1/module2_chassis_motion/module2_chassis_motion.ino) in Arduino IDE.
2. In Library Manager, install:
   - `ArduinoJson` (v6 or v7)
   - `ESP32Servo` by Kevin Harrington
3. In `config.h`, set your Wi-Fi credentials.
4. Tools menu settings:
   - **Board**: `ESP32S3 Dev Module`
   - **Upload Speed**: `921600`
5. Connect your Chassis ESP32-S3 and hit **Upload**.
6. Open Serial Monitor (`115200 Baud`) to confirm your Chassis IP:
   ```
   [WiFi] Connected! IP Address: 192.168.100.244
   >>> OPEN IN PHONE/BROWSER: http://192.168.100.244/ <<<
   ```

---

### 4. Running Module 3 (Host Python Brain)
1. Open your terminal in `module3_python_brain`:
   ```bash
   cd module3_python_brain
   python -m venv venv
   .\venv\Scripts\activate      # Windows
   # source venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```
2. Configure your environment secrets in `.env`:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key_here
   ROBOT_HEAD_IP=192.168.100.243
   ROBOT_CHASSIS_IP=192.168.100.244
   ```
3. Launch the central brain:
   ```bash
   python main.py
   ```
4. Access the dashboard:
   - On Host PC: `http://localhost:8000`
   - On Smartphone / Tablet: `http://<HOST_PC_IP>:8000`

---

## 🌐 REST API & WebSocket Reference

### REST Endpoints
| Endpoint | Method | Payload / Params | Description |
|:---|:---:|:---|:---|
| `/api/status` | `GET` | — | Returns comprehensive telemetry (mode, drive, gaze, servos, mic, track). |
| `/api/drive` | `POST` | `{"fwd": 120, "turn": -40}` | Dispatches immediate motor velocity vector. |
| `/api/servos` | `POST` | `{"servos": [90, 90, 90, 90, 90]}` | Direct 5-axis servo position update. |
| `/api/roam` | `POST` | `{"enabled": true}` | Toggles autonomous roaming and obstacle avoidance. |
| `/api/camera/capture` | `POST` | `{"overlay": false}` | Captures high-res JPEG snapshot and registers in SQLite3. |
| `/api/camera/gallery` | `GET` | — | Returns array of all stored photo records from SQLite3. |
| `/api/camera/source` | `POST` | `{"source": "esp32" \| "browser"}` | Switches active video input pipeline. |
| `/api/inmp/test` | `POST` | `{"duration": 3.0}` | Records 3s audio from robot INMP441 mic and returns playable WAV! |
| `/api/spotify/play` | `POST` | `{"query": "LOONA Hi High"}` | Searches and streams song to MAX98357A speaker. |
| `/api/memory` | `GET` | — | Returns full SQLite3 database vault state. |

### WebSocket Channels
- **Client Cockpit (`/ws/client`)**: Full-duplex JSON channel broadcasting 25 Hz telemetry, subtitles, gaze offsets, and photo capture alerts.
- **Audio Hub (`/ws/audio`)**: Full-duplex binary channel ingesting 16 kHz PCM from the INMP441 microphone and transmitting 24 kHz PCM to the MAX98357A speaker.
- **Browser Camera Ingestion (`/ws/camera_feed`)**: Binary WebSocket channel streaming JPEG frames from phone cameras directly into the OpenCV tracker.

### Direct High-Speed UDP (Port 8888)
```json
{
  "fwd": 140,
  "turn": -30,
  "servos": [90, 95, 90, 90, 90],
  "pin_cmd": {"pin": 38, "state": "HIGH", "pwm": 200}
}
```

---

## 🧪 10-Tier Verification Benchmark

Project L.O.O.N.A. includes an automated, multi-tier test suite in `module3_python_brain/scratch_test_all.py`:

```bash
cd module3_python_brain
python scratch_test_all.py
```

```
=== TEST 1: CORE CONFIGURATION & CONSTANTS ===
[PASS] RobotConfig imports & defaults verified.

=== TEST 2: SQLITE3 DATABASE ENGINE ===
[PASS] Initialized SQLite3 database with 6 tables.
[PASS] Inserted and retrieved face 'orbit_user'.
[PASS] Chat conversation logged and retrieved.

=== TEST 3: OPENCV VISION TRACKER ===
[PASS] Haar Cascade face detection & P-Controller verified (30 FPS, <45ms latency).

=== TEST 4: FASTAPI REST ENDPOINTS & WEBSOCKETS ===
[PASS] Network endpoints, photo capture, and audio routes verified.

=== TEST 5: 20 kHz ULTRASONIC PWM & FAILSAPES ===
[PASS] 20,000 Hz PWM verified with 0 dB acoustic motor whine.
[PASS] 800ms watchdog failsafe auto-braking verified.

🎉 ALL TESTS PASSED SUCCESSFULLY! ZERO ERRORS DETECTED.
```

---

## 💌 The 6 Developers Behind LOONA

Proudly engineered by **Team LOONA (CpE241B)** at **National University – Laguna**:

<div align="center">

| Developer | Role & Contributions |
|:---|:---|
| **Ivan Lawrence F. Gonzales** | **Chief Systems Architect & Embedded Systems Engineer **  |
| **Jekjek C. Florencondia** |
| **Warren S. Ricamara** | 
| **Steven Lo Nieva** | 
| **Zhyldjian Adovas** | 
| **Ace Anthony Guardiono** |

**Course**: CPMICR1L - Microprocessor and Microcontroller Systems and Design    
**Institution**: School of Engineering and Architecture, National University – Laguna  
**Academic Year**: 2026–2027 (1st Trimester)

</div>

---

<div align="center">

### 💖 ☾ "Stan LOONA, Stan Robotics!" ☽ 💖
*Built with ❤️, C++, Python, and Love for LOONA.*

</div>


