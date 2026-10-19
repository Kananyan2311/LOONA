import os
from dataclasses import dataclass, field

def _load_env_file():
    """Auto-loads key-value pairs from .env if present without requiring external libraries."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_env_file()

@dataclass
class RobotConfig:
    # IP Address of Head Controller (ESP32-S3 CAM)
    ROBOT_HEAD_IP: str = os.getenv("ROBOT_HEAD_IP", "192.168.100.243")
    ROBOT_UDP_PORT: int = int(os.getenv("ROBOT_UDP_PORT", "8888"))

    # IP Address of Chassis Motion Controller (ESP32-S3 DevKitC Web Controller)
    ROBOT_CHASSIS_IP: str = os.getenv("ROBOT_CHASSIS_IP", "192.168.100.244")
    CHASSIS_HTTP_PORT: int = int(os.getenv("CHASSIS_HTTP_PORT", "80"))

    # Camera MJPEG URL from Head Controller
    CAM_STREAM_URL: str = os.getenv("CAM_STREAM_URL", f"http://{ROBOT_HEAD_IP}/stream")
    
    # Server Brain Binding
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # --- Vision & Tracking (P-Controller) ---
    FRAME_WIDTH: int = 320
    FRAME_HEIGHT: int = 240
    
    # Target face width in pixels (for forward/backward distance keeping)
    TARGET_FACE_WIDTH: int = 70
    
    # Proportional gains for face following
    KP_TURN: float = 0.85      # Steer left/right to center face
    KP_FWD: float = 0.60       # Drive forward/back to maintain distance
    
    # Deadbands (ignore tiny oscillations)
    DEADBAND_X: float = 0.08   # Normalized horizontal error deadband (-1 to 1)
    DEADBAND_DIST: int = 10    # Face width pixel deadband
    
    # Drive limits
    MAX_SPEED: int = 220       # Out of 255
    MIN_DRIVE_PWM: int = 60    # Overcome motor static friction
    
    # --- Audio Parameters ---
    MIC_SAMPLE_RATE: int = 16000     # 16 kHz Mono from INMP441
    SPK_SAMPLE_RATE: int = 24000     # 24 kHz Stereo/Mono for MAX98357A
    AUDIO_CHUNK_SIZE: int = 512
    
    # --- Project L.O.O.N.A. System Metadata ---
    PROJECT_NAME: str = "Project L.O.O.N.A. (Locomotive Optical Operative for Navigation and Assistance)"
    SERVO_DEFAULTS: list = field(default_factory=lambda: [90, 90, 90, 90, 90])  # Pan, Tilt, LeftEar, RightEar, Tail
    EXPANSION_PINS: list = field(default_factory=lambda: [2, 3, 6, 21, 38, 47, 48])  # Safe GPIOs on ESP32-S3 Chassis DevKitC

    # --- AI & Gemini Service ---
    # PASTE YOUR GEMINI API KEY HERE (from https://aistudio.google.com/):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6L4Ei197rUk2y2kZAx2lVpJjWPwyT_cNbd0HNtDWV9QXQ")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    GEMINI_FALLBACK_MODELS: list = field(default_factory=lambda: ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"])


    
    # LOONA (loonatheworld) Charismatic K-Pop Idol Voice Configuration
    TTS_PRESET: str = os.getenv("TTS_PRESET", "kpop_idol_en")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-US-JennyNeural")
    TTS_PITCH: str = os.getenv("TTS_PITCH", "+0Hz")       # Natural charismatic K-pop idol pitch
    TTS_RATE: str = os.getenv("TTS_RATE", "+0%")          # Smooth natural cadence

    # --- Spotify Integration ---
    # Optional Developer API credentials (from https://developer.spotify.com/dashboard)
    # If not set, LOONA automatically falls back to instant desktop URI & WebApp player!
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI: str = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    SPOTIFY_DEVICE_ID: str = os.getenv("SPOTIFY_DEVICE_ID", "")

config = RobotConfig()



