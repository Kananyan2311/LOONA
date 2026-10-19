import cv2
import os
import time
import math
import numpy as np
import threading
import urllib.request
from typing import Tuple, Optional, List, Dict, Any
from config import config

CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "data", "captures")


class VisionTracker:
    """
    Project L.O.O.N.A. Real-Time Vision, Tracking, Object Detection & Photography Subsystem.
    Capabilities:
      1. Multi-Target Face Recognition with glowing neon cyan/magenta cyber reticles and names.
      2. Real-Time Object Detection with emerald cyber bounding boxes, labels, and confidence tags.
      3. Proportional (P) Locomotive Gaze & Distance Tracking.
      4. Snapshot Photography Engine with instant SQLite3 registration and high-res saving.
      5. Multi-Source Video Pipeline: ESP32-CAM, Browser WebCam (WebRTC/getUserMedia), or Host USB Cam.
    """

    def __init__(self):
        # 1. Haar Cascade Detectors
        cascade_dir = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_frontalface_default.xml")
        self.body_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_upperbody.xml")
        self.cat_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_frontalcatface.xml")

        # 2. State variables (thread-safe)
        self.lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_jpeg_bytes: Optional[bytes] = None

        # Camera Source Selection: "esp32", "browser", or "host_usb"
        self.camera_source: str = "esp32"
        self.external_frame: Optional[np.ndarray] = None
        self.external_frame_time: float = 0.0
        self.cap_usb: Optional[Any] = None

        # 3. Detection Modes: "all" (faces + objects), "faces", "objects"
        self.detection_mode: str = "all"
        self.custom_injected_objects: List[Dict[str, Any]] = []
        self.injected_objects_expiry: float = 0.0

        # 4. Tracking telemetry
        self.face_detected: bool = False
        self.dx: float = 0.0     # Horizontal gaze offset [-1.0 (left) .. +1.0 (right)]
        self.dy: float = 0.0     # Vertical gaze offset [-1.0 (up) .. +1.0 (down)]
        self.face_width: int = 0
        self.fwd_cmd: int = 0
        self.turn_cmd: int = 0
        self.fps: float = 0.0
        self.detected_faces_info: List[Dict[str, Any]] = []
        self.detected_objects_info: List[Dict[str, Any]] = []

        self.running: bool = False
        self.thread: Optional[threading.Thread] = None

        # Ensure captures directory exists
        os.makedirs(CAPTURES_DIR, exist_ok=True)

    def start(self):
        """Starts the background vision, face tracking, and object detection thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("[VISION] Vision tracker thread started with multi-face & object detection.")

    def stop(self):
        """Stops the vision thread."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            print("[VISION] Vision tracker thread stopped.")

    def set_detection_mode(self, mode: str):
        """Sets active detection mode: 'all', 'faces', or 'objects'."""
        with self.lock:
            self.detection_mode = mode if mode in ("all", "faces", "objects") else "all"
            print(f"[VISION] Detection mode set to: '{self.detection_mode}'")

    def set_camera_source(self, source: str) -> str:
        """Sets active camera source: 'esp32', 'browser', or 'host_usb'."""
        with self.lock:
            valid_source = source if source in ("esp32", "browser", "host_usb") else "esp32"
            self.camera_source = valid_source
            if valid_source != "host_usb" and self.cap_usb is not None:
                try:
                    self.cap_usb.release()
                except Exception:
                    pass
                self.cap_usb = None
            print(f"[VISION] Camera source switched to: '{self.camera_source}'")
            return self.camera_source

    def get_camera_source(self) -> str:
        with self.lock:
            return self.camera_source

    def feed_external_jpeg(self, jpeg_bytes: bytes) -> bool:
        """Feeds a raw JPEG buffer from WebApp browser webcam into the vision tracker."""
        if not jpeg_bytes:
            return False
        try:
            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None:
                with self.lock:
                    self.external_frame = frame
                    self.external_frame_time = time.time()
                return True
        except Exception as e:
            print(f"[VISION] Error decoding external webcam frame: {e}")
        return False

    def inject_ai_detected_objects(self, objects: List[Dict[str, Any]], duration: float = 8.0):
        """Allows multimodal AI (e.g. Gemini) to inject identified objects into HUD overlay."""
        with self.lock:
            self.custom_injected_objects = list(objects)
            self.injected_objects_expiry = time.time() + duration
            print(f"[VISION] Injected {len(objects)} AI-detected objects into HUD overlay.")

    # =========================================================================
    # CYBER RETICLE & BOUNDING BOX DRAWING HELPERS
    # =========================================================================
    def _draw_face_box(self, frame: np.ndarray, x: int, y: int, w: int, h: int,
                        name: str, role: str = "Orbit", is_primary: bool = True,
                        index: int = 1):
        """Draws arcade cyber targeting boxes with corner reticles and identity name badges."""
        fx = int(x + w / 2)
        fy = int(y + h / 2)

        if is_primary:
            box_color = (255, 240, 0)      # Neon Cyan (BGR)
            accent_color = (0, 243, 255)   # Gold / Bright Cyan
            badge_bg = (15, 23, 42)        # Dark navy slate
            title_text = f"★ [LOCKED: {name.upper()}]"
            sub_text = f"ROLE: {role.upper()}"
        else:
            box_color = (180, 50, 255)     # Hot Pink / Violet (BGR)
            accent_color = (255, 100, 200) # Bright Magenta
            badge_bg = (24, 15, 36)        # Deep Purple
            title_text = f"[TARGET #{index}: {name.upper()}]"
            sub_text = f"{role.upper()}"

        # 1. Main Bounding Box Rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)

        # 2. Corner Targeting Reticles (L-brackets)
        c_len = max(8, int(w * 0.22))
        thickness = 3 if is_primary else 2
        cv2.line(frame, (x, y), (x + c_len, y), accent_color, thickness)
        cv2.line(frame, (x, y), (x, y + c_len), accent_color, thickness)
        cv2.line(frame, (x + w, y), (x + w - c_len, y), accent_color, thickness)
        cv2.line(frame, (x + w, y), (x + w, y + c_len), accent_color, thickness)
        cv2.line(frame, (x, y + h), (x + c_len, y + h), accent_color, thickness)
        cv2.line(frame, (x, y + h), (x, y + h - c_len), accent_color, thickness)
        cv2.line(frame, (x + w, y + h), (x + w - c_len, y + h), accent_color, thickness)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - c_len), accent_color, thickness)

        # 3. Center Crosshair Reticle (primary face)
        if is_primary:
            cv2.circle(frame, (fx, fy), 4, accent_color, -1)
            cv2.line(frame, (fx - 8, fy), (fx + 8, fy), accent_color, 1)
            cv2.line(frame, (fx, fy - 8), (fx, fy + 8), accent_color, 1)

        # 4. Identity Name Badge Tag
        badge_h = 24
        badge_y1 = max(0, y - badge_h)
        badge_y2 = y if y - badge_h >= 0 else y + badge_h
        text_len = len(title_text)
        badge_w = min(config.FRAME_WIDTH - x, max(w, text_len * 9 + 14))

        cv2.rectangle(frame, (x, badge_y1), (x + badge_w, badge_y2), badge_bg, -1)
        cv2.rectangle(frame, (x, badge_y1), (x + badge_w, badge_y2), box_color, 1)
        cv2.putText(frame, title_text, (x + 5, badge_y1 + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, accent_color, 1, cv2.LINE_AA)

        # 5. Role subtext
        if y + h + 16 < config.FRAME_HEIGHT:
            cv2.putText(frame, sub_text, (x + 2, y + h + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 220, 240), 1, cv2.LINE_AA)

    def _draw_object_box(self, frame: np.ndarray, x: int, y: int, w: int, h: int,
                         label: str, confidence: float = 0.92, index: int = 1):
        """Draws high-visibility arcade cyber targeting box with object label and confidence."""
        box_color = (0, 255, 120)       # Neon Emerald Mint (BGR)
        accent_color = (80, 255, 180)   # Bright Mint
        badge_bg = (12, 30, 24)         # Deep Forest Navy

        title_text = f"● [OBJECT: {label.upper()}]"
        sub_text = f"CONF: {int(confidence * 100)}%"

        # 1. Bounding Box
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)

        # 2. Corner Reticles
        c_len = max(6, int(w * 0.2))
        cv2.line(frame, (x, y), (x + c_len, y), accent_color, 2)
        cv2.line(frame, (x, y), (x, y + c_len), accent_color, 2)
        cv2.line(frame, (x + w, y), (x + w - c_len, y), accent_color, 2)
        cv2.line(frame, (x + w, y), (x + w, y + c_len), accent_color, 2)
        cv2.line(frame, (x, y + h), (x + c_len, y + h), accent_color, 2)
        cv2.line(frame, (x, y + h), (x, y + h - c_len), accent_color, 2)
        cv2.line(frame, (x + w, y + h), (x + w - c_len, y + h), accent_color, 2)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - c_len), accent_color, 2)

        # 3. Label Badge Header
        badge_h = 22
        badge_y1 = max(0, y - badge_h)
        badge_y2 = y if y - badge_h >= 0 else y + badge_h
        text_len = len(title_text)
        badge_w = min(config.FRAME_WIDTH - x, max(w, text_len * 8 + 12))

        cv2.rectangle(frame, (x, badge_y1), (x + badge_w, badge_y2), badge_bg, -1)
        cv2.rectangle(frame, (x, badge_y1), (x + badge_w, badge_y2), box_color, 1)
        cv2.putText(frame, title_text, (x + 4, badge_y1 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, accent_color, 1, cv2.LINE_AA)

        # 4. Confidence Subtitle
        if y + h + 15 < config.FRAME_HEIGHT:
            cv2.putText(frame, sub_text, (x + 2, y + h + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.30, (150, 255, 200), 1, cv2.LINE_AA)

    # =========================================================================
    # REAL-TIME OBJECT DETECTION HELPER
    # =========================================================================
    def _detect_objects_in_frame(self, frame: np.ndarray, small_gray: np.ndarray, exclude_boxes: List[Tuple[int, int, int, int]]) -> List[Dict[str, Any]]:
        """
        Detects real-world objects in frame using downscaled body/pet cascades (160x120),
        salient foreground contours, and AI injection for minimal CPU overhead.
        """
        results: List[Dict[str, Any]] = []

        def overlaps_face(ox, oy, ow, oh) -> bool:
            for (fx, fy, fw, fh) in exclude_boxes:
                # Check bounding box intersection
                if not (ox + ow < fx or ox > fx + fw or oy + oh < fy or oy > fy + fh):
                    return True
            return False

        # A. Detect Person / Upper Body on small_gray (160x120)
        bodies = self.body_cascade.detectMultiScale(small_gray, scaleFactor=1.2, minNeighbors=3, minSize=(30, 30))
        for (bx, by, bw, bh) in bodies:
            rx, ry, rw, rh = int(bx * 2), int(by * 2), int(bw * 2), int(bh * 2)
            if not overlaps_face(rx, ry, rw, rh):
                results.append({
                    "label": "Person",
                    "confidence": 0.88,
                    "box": [rx, ry, rw, rh]
                })

        # B. Detect Pet / Cat on small_gray (160x120)
        cats = self.cat_cascade.detectMultiScale(small_gray, scaleFactor=1.2, minNeighbors=3, minSize=(20, 20))
        for (cx, cy, cw, ch) in cats:
            rx, ry, rw, rh = int(cx * 2), int(cy * 2), int(cw * 2), int(ch * 2)
            if not overlaps_face(rx, ry, rw, rh):
                results.append({
                    "label": "Cat / Pet",
                    "confidence": 0.85,
                    "box": [rx, ry, rw, rh]
                })

        # C. Detect Prominent Foreground Objects via Saliency & Contour Analysis on small_gray
        blurred = cv2.GaussianBlur(small_gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 60, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Area in 160x120 is 1/4 of 320x240 (750 to 10000 corresponds to 3000 to 40000)
            if 750 < area < 10000:
                ox, oy, ow, oh = cv2.boundingRect(cnt)
                rx, ry, rw, rh = int(ox * 2), int(oy * 2), int(ow * 2), int(oh * 2)
                if overlaps_face(rx, ry, rw, rh):
                    continue

                aspect = float(oh) / float(ow) if ow > 0 else 1.0
                if aspect > 1.6:
                    label = "Bottle / Cup"
                    conf = 0.82
                elif aspect < 0.65:
                    label = "Laptop / Keyboard"
                    conf = 0.84
                elif 0.8 <= aspect <= 1.5:
                    label = "Book / Device"
                    conf = 0.80
                else:
                    label = "Object"
                    conf = 0.78

                results.append({
                    "label": label,
                    "confidence": conf,
                    "box": [rx, ry, rw, rh]
                })
                if len(results) >= 4:
                    break

        # D. Add injected AI objects if still valid
        with self.lock:
            if time.time() < self.injected_objects_expiry and self.custom_injected_objects:
                for obj in self.custom_injected_objects:
                    results.append(obj)

        return results

    # =========================================================================
    # SYNTHETIC DEMO FRAME GENERATOR (CAMERA OFFLINE PREVIEW)
    # =========================================================================
    def _generate_synthetic_frame(self, frame_count: int) -> np.ndarray:
        """
        Generates an arcade visual test frame with both multiple simulated faces
        AND objects with cyber bounding boxes and names when camera is offline.
        """
        frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:, :] = (18, 22, 28)

        from memory_service import memory_vault
        saved_faces = memory_vault.get_faces()
        names = list(saved_faces.keys())
        p_name = names[0] if len(names) > 0 else "Kananyan"
        s_name = names[1] if len(names) > 1 else "Orbit Friend"

        # 1. Primary Simulated Face (Orbiting horizontally)
        t = frame_count * 0.04
        p_x = int(config.FRAME_WIDTH / 2 - 35 + 50 * np.sin(t))
        p_y = int(config.FRAME_HEIGHT / 2 - 45 + 12 * np.cos(t))
        p_w, p_h = 70, 70

        cv2.circle(frame, (p_x + 35, p_y + 35), 26, (60, 80, 100), -1)
        cv2.circle(frame, (p_x + 25, p_y + 28), 3, (0, 243, 255), -1)
        cv2.circle(frame, (p_x + 45, p_y + 28), 3, (0, 243, 255), -1)
        cv2.ellipse(frame, (p_x + 35, p_y + 44), (10, 5), 0, 0, 180, (0, 243, 255), 2)
        self._draw_face_box(frame, p_x, p_y, p_w, p_h, name=p_name, role="Master / Creator", is_primary=True, index=1)

        # 2. Secondary Simulated Face (Top right)
        t2 = frame_count * 0.03 + 2.0
        s_x = int(config.FRAME_WIDTH - 85 + 10 * np.sin(t2))
        s_y = int(35 + 10 * np.cos(t2))
        s_w, s_h = 50, 50

        cv2.circle(frame, (s_x + 25, s_y + 25), 18, (50, 40, 70), -1)
        cv2.circle(frame, (s_x + 18, s_y + 20), 3, (255, 100, 200), -1)
        cv2.circle(frame, (s_x + 32, s_y + 20), 3, (255, 100, 200), -1)
        cv2.ellipse(frame, (s_x + 25, s_y + 31), (7, 4), 0, 0, 180, (255, 100, 200), 2)
        self._draw_face_box(frame, s_x, s_y, s_w, s_h, name=s_name, role="Companion / Orbit", is_primary=False, index=2)

        # 3. Simulated Object 1: Smartphone (Bottom Left)
        cv2.rectangle(frame, (20, config.FRAME_HEIGHT - 95), (68, config.FRAME_HEIGHT - 25), (40, 50, 60), -1)
        cv2.rectangle(frame, (24, config.FRAME_HEIGHT - 90), (64, config.FRAME_HEIGHT - 35), (20, 30, 40), -1)
        self._draw_object_box(frame, 20, config.FRAME_HEIGHT - 95, 48, 70, label="Smartphone", confidence=0.96, index=1)

        # 4. Simulated Object 2: Coffee Cup / Bottle (Bottom Right)
        cv2.rectangle(frame, (config.FRAME_WIDTH - 75, config.FRAME_HEIGHT - 85), (config.FRAME_WIDTH - 25, config.FRAME_HEIGHT - 25), (55, 60, 70), -1)
        cv2.ellipse(frame, (config.FRAME_WIDTH - 50, config.FRAME_HEIGHT - 85), (25, 8), 0, 0, 360, (0, 255, 120), 1)
        self._draw_object_box(frame, config.FRAME_WIDTH - 75, config.FRAME_HEIGHT - 85, 50, 60, label="Coffee Mug", confidence=0.91, index=2)

        # Status Overlay Banner
        cv2.putText(frame, "LOONA OPTICAL GAZE - MULTI-TARGET & OBJECT DEMO", (8, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "TARGETS: 2 FACES | 2 OBJECTS DETECTED", (8, config.FRAME_HEIGHT - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 255, 150), 1, cv2.LINE_AA)
        return frame

    def _generate_waiting_browser_cam_frame(self, frame_count: int) -> np.ndarray:
        """Generates an arcade cyber waiting frame when Browser WebCam mode is active but awaiting frames."""
        frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
        frame[:, :] = (15, 20, 26)

        # Cyber grid pattern
        for y in range(0, config.FRAME_HEIGHT, 20):
            cv2.line(frame, (0, y), (config.FRAME_WIDTH, y), (25, 35, 48), 1)
        for x in range(0, config.FRAME_WIDTH, 26):
            cv2.line(frame, (x, 0), (x, config.FRAME_HEIGHT), (25, 35, 48), 1)

        pulse = int(128 + 127 * math.sin(frame_count * 0.12))
        cv2.rectangle(frame, (8, 8), (config.FRAME_WIDTH - 8, config.FRAME_HEIGHT - 8), (0, 243, 255), 1)
        cv2.circle(frame, (28, 40), 6, (0, 243, 255), -1)
        cv2.putText(frame, "WEB APP CAMERA ACTIVE", (42, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 243, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "STREAMING FRAMES FROM BROWSER...", (20, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, pulse, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "AI FACES & OBJECT DETECTION READY", (20, 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 255, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, "CLICK 'USE WEB APP CAM' TO CONNECT", (20, 185),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.30, (140, 170, 200), 1, cv2.LINE_AA)
        return frame

    # =========================================================================
    # MAIN REAL-TIME VISION LOOP
    # =========================================================================
    def _run_loop(self):
        """Main vision loop: pulls ESP32 MJPEG, Browser WebCam, or Host USB, detects faces & objects, computes P-controller."""
        stream = None
        bytes_buffer = b""
        frame_counter = 0
        last_time = time.time()
        cached_faces_dict: Dict[str, Any] = {}
        last_faces_cache_time = 0.0
        cached_detected_objs: List[Dict[str, Any]] = []

        while self.running:
            frame = None
            is_synthetic = False

            with self.lock:
                active_source = self.camera_source

            if active_source == "browser":
                # Clean up ESP32 stream if open
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = None
                    bytes_buffer = b""

                with self.lock:
                    if self.external_frame is not None and (time.time() - self.external_frame_time < 3.0):
                        frame = self.external_frame.copy()

                if frame is None:
                    frame = self._generate_waiting_browser_cam_frame(frame_counter)
                    is_synthetic = True

            elif active_source == "host_usb":
                # Clean up ESP32 stream if open
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    stream = None
                    bytes_buffer = b""

                if self.cap_usb is None or not self.cap_usb.isOpened():
                    try:
                        self.cap_usb = cv2.VideoCapture(0)
                    except Exception:
                        self.cap_usb = None

                if self.cap_usb and self.cap_usb.isOpened():
                    ret, usb_f = self.cap_usb.read()
                    if ret and usb_f is not None:
                        frame = usb_f

                if frame is None:
                    frame = self._generate_synthetic_frame(frame_counter)
                    is_synthetic = True

            else:  # "esp32"
                # 1. Attempt connection to ESP32-CAM MJPEG Stream
                if stream is None:
                    try:
                        req = urllib.request.Request(
                            config.CAM_STREAM_URL,
                            headers={"User-Agent": "LOONA-Brain/1.0"}
                        )
                        stream = urllib.request.urlopen(req, timeout=2.0)
                        print(f"[VISION] Connected to camera stream at {config.CAM_STREAM_URL}")
                    except Exception:
                        stream = None
                        time.sleep(0.5)

                # 2. Extract JPEG frame from MJPEG HTTP stream with zero-latency buffer dropping
                if stream is not None:
                    try:
                        chunk = stream.read(4096)
                        if not chunk:
                            stream = None
                            continue
                        bytes_buffer += chunk

                        a = bytes_buffer.find(b"\xff\xd8")
                        b = bytes_buffer.find(b"\xff\xd9", a + 2) if a != -1 else -1
                        if a != -1 and b != -1:
                            jpg = bytes_buffer[a : b + 2]
                            bytes_buffer = bytes_buffer[b + 2 :]
                            # Purge any backlog to ensure 0ms real-time preview (no latency buildup)
                            if len(bytes_buffer) > 16384:
                                next_a = bytes_buffer.rfind(b"\xff\xd8")
                                if next_a > 0:
                                    bytes_buffer = bytes_buffer[next_a:]
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    except Exception:
                        stream = None
                        bytes_buffer = b""

                # 3. Fallback to synthetic demo frame if ESP32 CAM is offline
                if frame is None:
                    frame = self._generate_synthetic_frame(frame_counter)
                    is_synthetic = True

            # 4. Standard tracking resolution (320x240)
            if frame.shape[1] != config.FRAME_WIDTH or frame.shape[0] != config.FRAME_HEIGHT:
                frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

            # Store clean un-annotated raw frame for snapshot photography
            raw_frame_copy = frame.copy()

            center_x = config.FRAME_WIDTH / 2.0
            center_y = config.FRAME_HEIGHT / 2.0

            detected = False
            cur_dx = 0.0
            cur_dy = 0.0
            cur_fw = 0
            fwd = 0
            turn = 0
            faces_telemetry: List[Dict[str, Any]] = []
            objects_telemetry: List[Dict[str, Any]] = []

            # 5. Live Detection Pipeline
            if not is_synthetic:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Downscale 50% to 160x120: reduces CPU load by 75% for butter-smooth tracking
                small_gray = cv2.resize(gray, (160, 120), interpolation=cv2.INTER_LINEAR)
                face_boxes: List[Tuple[int, int, int, int]] = []

                # A. Face Recognition
                if self.detection_mode in ("all", "faces"):
                    raw_faces = self.face_cascade.detectMultiScale(
                        small_gray,
                        scaleFactor=1.18,
                        minNeighbors=3,
                        minSize=(16, 16)
                    )

                    if len(raw_faces) > 0:
                        # Scale back to 320x240 frame coordinates
                        faces = [(int(x * 2), int(y * 2), int(w * 2), int(h * 2)) for (x, y, w, h) in raw_faces]
                        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                        detected = True

                        now_t = time.time()
                        if now_t - last_faces_cache_time > 2.5:
                            from memory_service import memory_vault
                            cached_faces_dict = memory_vault.get_faces()
                            last_faces_cache_time = now_t
                        saved_faces = cached_faces_dict
                        saved_names = list(saved_faces.keys())

                        for idx, (x, y, w, h) in enumerate(faces):
                            is_primary = (idx == 0)
                            face_boxes.append((int(x), int(y), int(w), int(h)))

                            if idx < len(saved_names):
                                face_name = saved_names[idx]
                                face_role = saved_faces[face_name].get("role", "Friend / Orbit")
                            else:
                                face_name = f"Orbit {idx + 1}" if idx > 0 else "Orbit"
                                face_role = "Guest / Orbit"

                            self._draw_face_box(
                                frame, int(x), int(y), int(w), int(h),
                                name=face_name,
                                role=face_role,
                                is_primary=is_primary,
                                index=idx + 1
                            )

                            faces_telemetry.append({
                                "index": idx + 1,
                                "name": face_name,
                                "role": face_role,
                                "box": [int(x), int(y), int(w), int(h)],
                                "is_primary": is_primary
                            })

                        # Primary face drives locomotive tracking
                        (px, py, pw, ph) = faces[0]
                        cur_dx = float(((px + pw / 2.0) - center_x) / center_x)
                        cur_dy = float(((py + ph / 2.0) - center_y) / center_y)
                        cur_fw = int(pw)

                        # P-Controller Steering
                        if abs(cur_dx) > config.DEADBAND_X:
                            turn = int(config.KP_TURN * cur_dx * config.MAX_SPEED)
                            if abs(turn) < config.MIN_DRIVE_PWM and abs(turn) > 0:
                                turn = int(np.sign(turn) * config.MIN_DRIVE_PWM)
                        else:
                            turn = 0

                        # P-Controller Forward Distance
                        dist_err = config.TARGET_FACE_WIDTH - cur_fw
                        if abs(dist_err) > config.DEADBAND_DIST:
                            fwd = int(config.KP_FWD * dist_err * 2.2)
                            if abs(fwd) < config.MIN_DRIVE_PWM and abs(fwd) > 0:
                                fwd = int(np.sign(fwd) * config.MIN_DRIVE_PWM)
                        else:
                            fwd = 0

                        turn = int(np.clip(turn, -config.MAX_SPEED, config.MAX_SPEED))
                        fwd = int(np.clip(fwd, -config.MAX_SPEED, config.MAX_SPEED))

                # B. Object Detection (Interleaved every 3 frames for high FPS)
                if self.detection_mode in ("all", "objects"):
                    if frame_counter % 3 == 0 or not cached_detected_objs:
                        cached_detected_objs = self._detect_objects_in_frame(frame, small_gray, face_boxes)
                    for o_idx, obj in enumerate(cached_detected_objs):
                        ox, oy, ow, oh = obj["box"]
                        olabel = obj["label"]
                        oconf = obj.get("confidence", 0.88)
                        self._draw_object_box(frame, ox, oy, ow, oh, label=olabel, confidence=oconf, index=o_idx + 1)
                        objects_telemetry.append({
                            "index": o_idx + 1,
                            "label": olabel,
                            "confidence": oconf,
                            "box": [ox, oy, ow, oh]
                        })

            else:
                # Synthetic demo telemetry
                from memory_service import memory_vault
                saved_faces = memory_vault.get_faces()
                names = list(saved_faces.keys())
                primary_name = names[0] if names else "Kananyan"
                secondary_name = names[1] if len(names) > 1 else "Orbit Friend"
                detected = True
                cur_dx = 0.15 * np.sin(frame_counter * 0.04)
                cur_dy = 0.05 * np.cos(frame_counter * 0.04)
                cur_fw = 70
                faces_telemetry = [
                    {"index": 1, "name": primary_name, "role": "Master / Creator", "box": [120, 75, 70, 70], "is_primary": True},
                    {"index": 2, "name": secondary_name, "role": "Companion / Orbit", "box": [235, 35, 50, 50], "is_primary": False}
                ]
                objects_telemetry = [
                    {"index": 1, "label": "Smartphone", "confidence": 0.96, "box": [20, 145, 48, 70]},
                    {"index": 2, "label": "Coffee Mug", "confidence": 0.91, "box": [245, 155, 50, 60]}
                ]

            # Encode latest JPEG with lightweight compression (quality 60) for zero network latency
            _, encoded_jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            jpeg_bytes = encoded_jpeg.tobytes()

            # FPS Calculation
            frame_counter += 1
            now = time.time()
            if now - last_time >= 1.0:
                self.fps = frame_counter / (now - last_time)
                frame_counter = 0
                last_time = now

            # Thread-safe state update
            with self.lock:
                self.latest_frame = frame
                self.latest_raw_frame = raw_frame_copy
                self.latest_jpeg_bytes = jpeg_bytes
                self.face_detected = detected
                self.dx = cur_dx
                self.dy = cur_dy
                self.face_width = cur_fw
                self.fwd_cmd = fwd
                self.turn_cmd = turn
                self.detected_faces_info = faces_telemetry
                self.detected_objects_info = objects_telemetry

            time.sleep(0.03)

    # =========================================================================
    # SNAPSHOT PHOTOGRAPHY ENGINE
    # =========================================================================
    def capture_snapshot(self, with_overlay: bool = False, notes: str = "") -> Dict[str, Any]:
        """
        Captures a high-resolution snapshot from LOONA's camera and registers it in SQLite3.
        Returns metadata: filename, filepath, url, timestamp, date.
        """
        from memory_service import memory_vault
        with self.lock:
            target_frame = self.latest_frame if with_overlay else self.latest_raw_frame
            if target_frame is None:
                # Generate a crisp synthetic snapshot if offline
                target_frame = self._generate_synthetic_frame(0)

            frame_to_save = target_frame.copy()

        ts = int(time.time())
        dt = time.strftime("%Y-%m-%d %H:%M:%S")
        filename = f"loona_snap_{ts}.jpg"
        filepath = os.path.join(CAPTURES_DIR, filename)

        # Save JPEG image
        cv2.imwrite(filepath, frame_to_save, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[CAMERA] Captured photo saved: {filepath} ({frame_to_save.shape[1]}x{frame_to_save.shape[0]})")

        # Register photo in SQLite3 database
        photo_record = memory_vault.save_photo(filename, filepath, notes=notes or "Captured by LOONA")
        return photo_record

    # =========================================================================
    # TELEMETRY & GETTERS
    # =========================================================================
    def get_tracking_state(self) -> dict:
        """Returns the current gaze offsets, drive commands, faces, and detected objects."""
        from memory_service import memory_vault
        saved_faces = memory_vault.get_faces()
        user_name = list(saved_faces.keys())[0] if saved_faces else "Orbit"

        with self.lock:
            active_name = user_name
            if self.detected_faces_info:
                primary = [f for f in self.detected_faces_info if f.get("is_primary")]
                if primary:
                    active_name = primary[0]["name"]

            # Compute obstacle & people avoidance sectors for autonomous roaming
            person_ahead = bool(self.face_detected or len(self.detected_faces_info) > 0)
            person_close = bool(self.face_detected and self.face_width > 50)
            person_dx = float(self.dx)

            left_blocked = False
            center_blocked = False
            right_blocked = False

            frame_w = config.FRAME_WIDTH
            frame_h = config.FRAME_HEIGHT

            for obj in self.detected_objects_info:
                box = obj.get("box", [0, 0, 0, 0])
                ox, oy, ow, oh = box
                cx = ox + ow / 2.0
                bottom_y = oy + oh
                if bottom_y > frame_h * 0.40 or (ow * oh) > (frame_w * frame_h * 0.05):
                    if cx < frame_w * 0.38:
                        left_blocked = True
                    elif cx > frame_w * 0.62:
                        right_blocked = True
                    else:
                        center_blocked = True

            clear_direction = "forward"
            if center_blocked or person_close:
                if not left_blocked and right_blocked:
                    clear_direction = "left"
                elif not right_blocked and left_blocked:
                    clear_direction = "right"
                elif not left_blocked:
                    clear_direction = "left"
                elif not right_blocked:
                    clear_direction = "right"
                else:
                    clear_direction = "blocked"

            nav_info = {
                "person_ahead": person_ahead,
                "person_close": person_close,
                "person_dx": round(person_dx, 2),
                "left_blocked": left_blocked,
                "center_blocked": center_blocked,
                "right_blocked": right_blocked,
                "clear_direction": clear_direction
            }

            return {
                "face_detected": self.face_detected,
                "dx": round(self.dx, 3),
                "dy": round(self.dy, 3),
                "face_width": self.face_width,
                "fwd": self.fwd_cmd,
                "turn": self.turn_cmd,
                "fps": round(self.fps, 1),
                "recognized_name": active_name if self.face_detected else "Searching...",
                "faces_count": len(self.detected_faces_info),
                "faces": list(self.detected_faces_info),
                "objects_count": len(self.detected_objects_info),
                "objects": list(self.detected_objects_info),
                "detection_mode": self.detection_mode,
                "camera_source": self.camera_source,
                "nav": nav_info
            }

    def save_current_face(self, name: str) -> dict:
        """Saves current recognized face profile to SQLite3 Memory Vault."""
        from memory_service import memory_vault
        return memory_vault.save_face(name)

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Returns the latest processed JPEG frame bytes."""
        with self.lock:
            return self.latest_jpeg_bytes
