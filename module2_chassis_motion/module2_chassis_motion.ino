/*
 * ====================================================================================================
 * PROJECT L.O.O.N.A. (Locomotive Optical Operative for Navigation and Assistance)
 * MODULE 2: CHASSIS & MOTION CONTROLLER FIRMWARE (STANDALONE WEB CONTROLLER & UDP/REST)
 * Hardware Target: ESP32-S3 DevKitC (4WD BTS7960 Matrix + 5x Servos + WebServer + WiFi UDP)
 * ====================================================================================================
 * Features:
 *   1. Embedded Web Controller (HTTP Port 80):
 *      - Connect directly from any smartphone, tablet, or browser to http://<CHASSIS_IP>/
 *      - Zero external internet or CDN required (works on home Wi-Fi and fallback SoftAP).
 *      - Full Virtual Touch D-Pad (Forward, Reverse, Pivot, Diagonals, Emergency Brake).
 *      - Keyboard controls (WASD, Arrow Keys, Space = Stop).
 *      - 5-Axis Servo Matrix Sliders (Pan, Tilt, Left Ear, Right Ear, Tail).
 *      - Real-time telemetry HUD (Left/Right speeds, RSSI, Failsafe, Uptime, Free Heap).
 *   2. High-Speed Direct UDP Datagram Listener (Port 8888):
 *      - Receives 25 Hz motion packets directly from Python Brain with <1ms latency.
 *   3. REST API with full CORS support:
 *      - /api/status, /api/drive, /api/servos, /api/stop, /api/cmd, /api/pin_cmd, /api/custom_servo.
 *   4. Locomotive 4WD BTS7960 Matrix:
 *      - 8 LEDC PWM channels at 20 kHz (ultrasonic, zero motor whine).
 *      - FL (4, 5), RL (6, 7), FR (15, 16), RR (17, 18).
 *   5. Operative 5-Axis Servo Matrix:
 *      - Pan (GPIO 8), Tilt (GPIO 11), Left Ear (GPIO 12), Right Ear (GPIO 13), Tail (GPIO 14).
 *   6. Dynamic Expansion GPIO & Autonomous Line Follower Subsystem.
 *   7. Auxiliary Serial/UART Fallback for backward compatibility.
 *   8. Safety Watchdog Failsafe (Brakes if signal lost).
 *
 * Dependencies (Arduino IDE Library Manager):
 *   - "ArduinoJson" by Benoit Blanchon (v6.x or v7.x)
 *   - "ESP32Servo" by Kevin Harrington (v1.x or v3.x)
 *   - "WiFi", "WebServer", "WiFiUdp" (Built-in with ESP32 board package)
 * ====================================================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include "config.h"

// --- Global Networking & Server Handles ---
WebServer server(WEB_SERVER_PORT);
WiFiUDP udpMotor;
static char udpBuffer[512];

// --- Watchdog & Safety Failsafe ---
static unsigned long lastCommandTime = 0;
static bool failsafeActive = false;

// Serial Line Accumulator Buffer (Fallback)
#define SERIAL_BUFFER_LEN 384
static char serialBuffer[SERIAL_BUFFER_LEN];
static size_t bufferIndex = 0;

// Motor state telemetry
struct MotorSpeeds {
    float left;
    float right;
};
static MotorSpeeds currentSpeeds = {0.0f, 0.0f};

// 5-Axis Built-in Servo Handles
static Servo servoHeadPan;
static Servo servoHeadTilt;
static Servo servoLeftEar;
static Servo servoRightEar;
static Servo servoTail;

static int currentServoAngles[5] = {SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE};

// Dynamic Auxiliary Servos Pool (up to 4 custom servos on arbitrary pins)
#define MAX_DYNAMIC_SERVOS 4
struct DynamicServoSlot {
    int pin;
    Servo servo;
    bool attached;
    int currentAngle;
};
static DynamicServoSlot dynamicServos[MAX_DYNAMIC_SERVOS] = {
    {-1, Servo(), false, 90},
    {-1, Servo(), false, 90},
    {-1, Servo(), false, 90},
    {-1, Servo(), false, 90}
};

// Autonomous Line Follower Subsystem State
static bool lineFollowerActive = false;
static int linePinLeft = -1;
static int linePinRight = -1;
static int lineFollowerSpeed = 140;
static bool lineSensorInvert = false;

// Forward Declarations
void processDriveCommand(float fwd, float turn);
void stopMotors();
void setServoAngles(int pan, int tilt, int leftEar, int rightEar, int tail);
void handleDynamicServo(int pin, int angle);
void handleExpansionPin(int pin, int state, int pwm);
void configureLineFollower(bool enable, int leftPin, int rightPin, int speed, bool invert);
void parseMotionJson(const char* jsonString);

// ============================================================================
// EMBEDDED RETRO CYBERPUNK WEB CONTROLLER UI (PROGMEM)
// ============================================================================
const char index_html[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>LOONA • ROVER CHASSIS CONTROLLER</title>
<style>
:root {
  --bg: #0b0416;
  --card: #18092e;
  --cyan: #00f0ff;
  --pink: #ff007f;
  --yellow: #ffe600;
  --green: #00ff88;
  --border: #3d1b6d;
  --text: #f0e6ff;
  --muted: #a38bc4;
}
* { box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-user-select: none; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  padding: 12px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}
header {
  width: 100%;
  max-width: 600px;
  background: var(--card);
  border: 2px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 20px rgba(0, 240, 255, 0.15);
}
.brand {
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--cyan);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}
.brand span { color: var(--pink); }
.status-pill {
  font-size: 11px;
  font-weight: bold;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid var(--green);
  color: var(--green);
}
.container {
  width: 100%;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.card {
  background: var(--card);
  border: 2px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.4);
}
.card-title {
  font-size: 11px;
  font-weight: bold;
  letter-spacing: 1.5px;
  color: var(--yellow);
  margin-bottom: 12px;
  text-transform: uppercase;
  display: flex;
  justify-content: space-between;
}
/* D-PAD GRID */
.dpad-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-width: 320px;
  margin: 0 auto;
}
.btn-pad {
  aspect-ratio: 1;
  background: #250f44;
  border: 2px solid var(--border);
  border-radius: 12px;
  color: #ffffff;
  font-size: 22px;
  font-weight: bold;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  touch-action: manipulation;
  transition: all 0.08s;
  box-shadow: 0 4px 0 #120524;
}
.btn-pad span {
  font-size: 9px;
  color: var(--muted);
  margin-top: 2px;
}
.btn-pad:active, .btn-pad.active {
  transform: translateY(3px);
  box-shadow: 0 1px 0 #120524;
  background: var(--cyan);
  color: #000000;
  border-color: #ffffff;
}
.btn-pad:active span, .btn-pad.active span { color: #000000; }
.btn-stop {
  background: #7a0c32;
  border-color: var(--pink);
  color: #ffffff;
}
.btn-stop:active, .btn-stop.active {
  background: var(--pink);
  color: #ffffff;
}
/* SPEED SLIDER */
.slider-group {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.slider-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
}
.slider-header b { color: var(--cyan); }
input[type=range] {
  width: 100%;
  accent-color: var(--cyan);
  height: 8px;
  border-radius: 4px;
  background: #250f44;
  outline: none;
}
/* SERVO SLIDERS GRID */
.servo-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.servo-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.servo-label {
  font-size: 11px;
  width: 90px;
  color: var(--muted);
}
.servo-val {
  font-size: 11px;
  width: 40px;
  text-align: right;
  color: var(--yellow);
  font-weight: bold;
}
.btn-action {
  width: 100%;
  padding: 10px;
  background: #250f44;
  border: 1.5px solid var(--cyan);
  border-radius: 8px;
  color: var(--cyan);
  font-weight: bold;
  font-size: 11px;
  cursor: pointer;
  margin-top: 10px;
  transition: all 0.1s;
}
.btn-action:active {
  background: var(--cyan);
  color: #000000;
}
/* TELEMETRY */
.telemetry-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  font-size: 11px;
}
.telemetry-item {
  background: #250f44;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
}
.telemetry-item .label { color: var(--muted); }
.telemetry-item .val { color: var(--green); font-weight: bold; }
footer {
  margin-top: 14px;
  font-size: 10px;
  color: var(--muted);
  text-align: center;
}
</style>
</head>
<body>

<header>
  <div class="brand">L.O.O.N.A. <span>CHASSIS</span></div>
  <div class="status-pill" id="connStatus">ONLINE</div>
</header>

<div class="container">
  <!-- D-PAD ROVER CONTROLLER -->
  <div class="card">
    <div class="card-title">
      <span>4WD BTS7960 DRIVE CONTROLLER</span>
      <span id="driveState" style="color: var(--cyan);">STOPPED</span>
    </div>

    <div class="dpad-grid">
      <button class="btn-pad" id="btnFL" data-fwd="1" data-turn="-0.6">↖<span>FL</span></button>
      <button class="btn-pad" id="btnFWD" data-fwd="1" data-turn="0">⬆<span>FWD</span></button>
      <button class="btn-pad" id="btnFR" data-fwd="1" data-turn="0.6">↗<span>FR</span></button>

      <button class="btn-pad" id="btnLEFT" data-fwd="0" data-turn="-1">⬅<span>LEFT</span></button>
      <button class="btn-pad btn-stop" id="btnSTOP" data-fwd="0" data-turn="0">🛑<span>STOP</span></button>
      <button class="btn-pad" id="btnRIGHT" data-fwd="0" data-turn="1">➡<span>RIGHT</span></button>

      <button class="btn-pad" id="btnBL" data-fwd="-1" data-turn="-0.6">↙<span>BL</span></button>
      <button class="btn-pad" id="btnREV" data-fwd="-1" data-turn="0">⬇<span>REV</span></button>
      <button class="btn-pad" id="btnBR" data-fwd="-1" data-turn="0.6">↘<span>BR</span></button>
    </div>

    <div class="slider-group">
      <div class="slider-header">
        <span>MAX DRIVE SPEED (PWM)</span>
        <b id="speedVal">180</b>
      </div>
      <input type="range" id="speedSlider" min="60" max="255" value="180">
    </div>
  </div>

  <!-- 5-AXIS SERVO MATRIX -->
  <div class="card">
    <div class="card-title">
      <span>5-AXIS SERVO MATRIX</span>
      <span style="color: var(--pink);">50 HZ</span>
    </div>
    <div class="servo-grid">
      <div class="servo-row">
        <span class="servo-label">HEAD PAN</span>
        <input type="range" class="servo-slider" id="servoPan" min="0" max="180" value="90">
        <span class="servo-val" id="valPan">90°</span>
      </div>
      <div class="servo-row">
        <span class="servo-label">HEAD TILT</span>
        <input type="range" class="servo-slider" id="servoTilt" min="0" max="180" value="90">
        <span class="servo-val" id="valTilt">90°</span>
      </div>
      <div class="servo-row">
        <span class="servo-label">LEFT EAR</span>
        <input type="range" class="servo-slider" id="servoLEar" min="0" max="180" value="90">
        <span class="servo-val" id="valLEar">90°</span>
      </div>
      <div class="servo-row">
        <span class="servo-label">RIGHT EAR</span>
        <input type="range" class="servo-slider" id="servoREar" min="0" max="180" value="90">
        <span class="servo-val" id="valREar">90°</span>
      </div>
      <div class="servo-row">
        <span class="servo-label">TAIL WAG</span>
        <input type="range" class="servo-slider" id="servoTail" min="0" max="180" value="90">
        <span class="servo-val" id="valTail">90°</span>
      </div>
    </div>
    <button class="btn-action" onclick="centerAllServos()">CENTER ALL SERVOS (90°)</button>
  </div>

  <!-- TELEMETRY -->
  <div class="card">
    <div class="card-title">CHASSIS HARDWARE TELEMETRY</div>
    <div class="telemetry-grid">
      <div class="telemetry-item"><span class="label">LEFT SPEED:</span><span class="val" id="telemL">0</span></div>
      <div class="telemetry-item"><span class="label">RIGHT SPEED:</span><span class="val" id="telemR">0</span></div>
      <div class="telemetry-item"><span class="label">FAILSAFE:</span><span class="val" id="telemFail">ARMED</span></div>
      <div class="telemetry-item"><span class="label">WI-FI RSSI:</span><span class="val" id="telemRssi">- dBm</span></div>
      <div class="telemetry-item"><span class="label">FREE HEAP:</span><span class="val" id="telemHeap">- KB</span></div>
      <div class="telemetry-item"><span class="label">UPTIME:</span><span class="val" id="telemUp">- s</span></div>
    </div>
  </div>
</div>

<footer>
  Project L.O.O.N.A. • ESP32-S3 Standalone Motion Controller • Dual WebServer & UDP 8888
</footer>

<script>
let currentFwd = 0;
let currentTurn = 0;
let driveInterval = null;
const speedSlider = document.getElementById('speedSlider');
const speedVal = document.getElementById('speedVal');
const driveState = document.getElementById('driveState');

speedSlider.oninput = (e) => { speedVal.innerText = e.target.value; };

function sendDrive(fwd, turn) {
  const maxSpd = parseInt(speedSlider.value);
  const actualFwd = Math.round(fwd * maxSpd);
  const actualTurn = Math.round(turn * maxSpd);

  if (actualFwd === 0 && actualTurn === 0) {
    driveState.innerText = "STOPPED";
    driveState.style.color = "var(--cyan)";
  } else {
    driveState.innerText = `DRIVING [${actualFwd}, ${actualTurn}]`;
    driveState.style.color = "var(--green)";
  }

  fetch(`/api/drive?fwd=${actualFwd}&turn=${actualTurn}`).catch(()=>{});
}

function startDriveLoop(fwd, turn) {
  currentFwd = fwd;
  currentTurn = turn;
  sendDrive(currentFwd, currentTurn);
  if (driveInterval) clearInterval(driveInterval);
  driveInterval = setInterval(() => {
    sendDrive(currentFwd, currentTurn);
  }, 100);
}

function stopDriveLoop() {
  if (driveInterval) clearInterval(driveInterval);
  driveInterval = null;
  currentFwd = 0;
  currentTurn = 0;
  sendDrive(0, 0);
  document.querySelectorAll('.btn-pad').forEach(b => b.classList.remove('active'));
}

// Bind D-Pad touch & mouse events
document.querySelectorAll('.btn-pad').forEach(btn => {
  const fwd = parseFloat(btn.getAttribute('data-fwd'));
  const turn = parseFloat(btn.getAttribute('data-turn'));

  const start = (e) => {
    e.preventDefault();
    btn.classList.add('active');
    startDriveLoop(fwd, turn);
  };
  const end = (e) => {
    e.preventDefault();
    btn.classList.remove('active');
    stopDriveLoop();
  };

  btn.addEventListener('pointerdown', start);
  btn.addEventListener('pointerup', end);
  btn.addEventListener('pointercancel', end);
  btn.addEventListener('contextmenu', e => e.preventDefault());
});

// Keyboard driving controls
window.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  const k = e.key.toLowerCase();
  if (k === 'w' || k === 'arrowup') { startDriveLoop(1, 0); document.getElementById('btnFWD').classList.add('active'); }
  else if (k === 's' || k === 'arrowdown') { startDriveLoop(-1, 0); document.getElementById('btnREV').classList.add('active'); }
  else if (k === 'a' || k === 'arrowleft') { startDriveLoop(0, -1); document.getElementById('btnLEFT').classList.add('active'); }
  else if (k === 'd' || k === 'arrowright') { startDriveLoop(0, 1); document.getElementById('btnRIGHT').classList.add('active'); }
  else if (k === 'q') { startDriveLoop(1, -0.6); document.getElementById('btnFL').classList.add('active'); }
  else if (k === 'e') { startDriveLoop(1, 0.6); document.getElementById('btnFR').classList.add('active'); }
  else if (k === ' ') { stopDriveLoop(); }
});

window.addEventListener('keyup', (e) => {
  const k = e.key.toLowerCase();
  if (['w','s','a','d','q','e','arrowup','arrowdown','arrowleft','arrowright',' '].includes(k)) {
    stopDriveLoop();
  }
});

// Servo Controls
function bindServo(sliderId, valId, paramName) {
  const slider = document.getElementById(sliderId);
  const val = document.getElementById(valId);
  slider.oninput = (e) => {
    val.innerText = e.target.value + '°';
    fetch(`/api/servos?${paramName}=${e.target.value}`).catch(()=>{});
  };
}
bindServo('servoPan', 'valPan', 'pan');
bindServo('servoTilt', 'valTilt', 'tilt');
bindServo('servoLEar', 'valLEar', 'lear');
bindServo('servoREar', 'valREar', 'rear');
bindServo('servoTail', 'valTail', 'tail');

function centerAllServos() {
  ['servoPan','servoTilt','servoLEar','servoREar','servoTail'].forEach(id => {
    document.getElementById(id).value = 90;
  });
  ['valPan','valTilt','valLEar','valREar','valTail'].forEach(id => {
    document.getElementById(id).innerText = '90°';
  });
  fetch('/api/servos?pan=90&tilt=90&lear=90&rear=90&tail=90').catch(()=>{});
}

// Telemetry Poller
setInterval(() => {
  fetch('/api/status')
    .then(r => r.json())
    .then(data => {
      document.getElementById('connStatus').innerText = 'CONNECTED';
      document.getElementById('connStatus').style.borderColor = 'var(--green)';
      document.getElementById('telemL').innerText = data.speed_left || 0;
      document.getElementById('telemR').innerText = data.speed_right || 0;
      document.getElementById('telemFail').innerText = data.failsafe ? 'BRAKED' : 'CLEAR';
      document.getElementById('telemFail').style.color = data.failsafe ? 'var(--pink)' : 'var(--green)';
      document.getElementById('telemRssi').innerText = (data.rssi || 0) + ' dBm';
      document.getElementById('telemHeap').innerText = Math.round((data.free_heap || 0) / 1024) + ' KB';
      document.getElementById('telemUp').innerText = Math.round((data.uptime_ms || 0) / 1000) + ' s';
    })
    .catch(() => {
      document.getElementById('connStatus').innerText = 'STANDBY';
      document.getElementById('connStatus').style.borderColor = 'var(--pink)';
    });
}, 450);
</script>
</body>
</html>
)rawliteral";

// ============================================================================
// HARDWARE LEDC PWM COMPATIBILITY WRAPPERS (Core v2.x and v3.x)
// ============================================================================
void initPwmPin(int pin, int channel) {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcAttach(pin, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
#else
    ledcSetup(channel, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
    ledcAttachPin(pin, channel);
#endif
}

void writePwmDuty(int pin, int channel, uint32_t duty) {
    duty = constrain(duty, 0, PWM_MAX_DUTY);
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcWrite(pin, duty);
#else
    ledcWrite(channel, duty);
#endif
}

// ============================================================================
// 5-AXIS BUILT-IN SERVO INITIALIZATION & ANGLE CONTROLLER
// ============================================================================
void initServos() {
    Serial.println("[SERVO] Initializing 5-Channel Servo Matrix on ESP32-S3...");

    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    servoHeadPan.setPeriodHertz(50);
    servoHeadTilt.setPeriodHertz(50);
    servoLeftEar.setPeriodHertz(50);
    servoRightEar.setPeriodHertz(50);
    servoTail.setPeriodHertz(50);

    servoHeadPan.attach(SERVO_HEAD_PAN_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    servoHeadTilt.attach(SERVO_HEAD_TILT_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    servoLeftEar.attach(SERVO_LEFT_EAR_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    servoRightEar.attach(SERVO_RIGHT_EAR_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    servoTail.attach(SERVO_TAIL_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);

    setServoAngles(SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE, SERVO_DEFAULT_ANGLE);
    Serial.printf("[SERVO] 5 Servos attached: Pan(GPIO %d), Tilt(GPIO %d), LEar(GPIO %d), REar(GPIO %d), Tail(GPIO %d)\n",
                  SERVO_HEAD_PAN_PIN, SERVO_HEAD_TILT_PIN, SERVO_LEFT_EAR_PIN, SERVO_RIGHT_EAR_PIN, SERVO_TAIL_PIN);
}

void setServoAngles(int pan, int tilt, int leftEar, int rightEar, int tail) {
    currentServoAngles[0] = constrain(pan, 0, 180);
    currentServoAngles[1] = constrain(tilt, 0, 180);
    currentServoAngles[2] = constrain(leftEar, 0, 180);
    currentServoAngles[3] = constrain(rightEar, 0, 180);
    currentServoAngles[4] = constrain(tail, 0, 180);

    servoHeadPan.write(currentServoAngles[0]);
    servoHeadTilt.write(currentServoAngles[1]);
    servoLeftEar.write(currentServoAngles[2]);
    servoRightEar.write(currentServoAngles[3]);
    servoTail.write(currentServoAngles[4]);
}

// ============================================================================
// DYNAMIC EXPANSION PIN SAFETY GUARD
// ============================================================================
bool isPinSafeForExpansion(int pin) {
    if (pin == CHASSIS_RX_PIN || pin == CHASSIS_TX_PIN) return false;
    if (pin == FL_RPWM_PIN || pin == FL_LPWM_PIN) return false;
    if (pin == FR_RPWM_PIN || pin == FR_LPWM_PIN) return false;
    if (pin == RL_RPWM_PIN || pin == RL_LPWM_PIN) return false;
    if (pin == RR_RPWM_PIN || pin == RR_LPWM_PIN) return false;
    if (pin == SERVO_HEAD_PAN_PIN || pin == SERVO_HEAD_TILT_PIN) return false;
    if (pin == SERVO_LEFT_EAR_PIN || pin == SERVO_RIGHT_EAR_PIN || pin == SERVO_TAIL_PIN) return false;
    if (pin < 0 || pin > 48) return false;
    return true;
}

// ============================================================================
// DYNAMIC CUSTOM SERVO CONTROLLER (Any safe expansion GPIO)
// ============================================================================
void handleDynamicServo(int pin, int angle) {
    if (!isPinSafeForExpansion(pin)) {
        Serial.printf("[CUSTOM-SERVO] Warning: Pin %d is reserved for chassis!\n", pin);
        return;
    }

    angle = constrain(angle, 0, 180);

    for (int i = 0; i < MAX_DYNAMIC_SERVOS; i++) {
        if (dynamicServos[i].attached && dynamicServos[i].pin == pin) {
            dynamicServos[i].servo.write(angle);
            dynamicServos[i].currentAngle = angle;
            return;
        }
    }

    for (int i = 0; i < MAX_DYNAMIC_SERVOS; i++) {
        if (!dynamicServos[i].attached) {
            dynamicServos[i].pin = pin;
            dynamicServos[i].servo.setPeriodHertz(50);
            dynamicServos[i].servo.attach(pin, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
            dynamicServos[i].servo.write(angle);
            dynamicServos[i].currentAngle = angle;
            dynamicServos[i].attached = true;
            return;
        }
    }

    dynamicServos[0].servo.detach();
    dynamicServos[0].pin = pin;
    dynamicServos[0].servo.setPeriodHertz(50);
    dynamicServos[0].servo.attach(pin, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    dynamicServos[0].servo.write(angle);
    dynamicServos[0].currentAngle = angle;
    dynamicServos[0].attached = true;
}

// ============================================================================
// DYNAMIC EXPANSION GPIO CONTROLLER (Digital & PWM)
// ============================================================================
void handleExpansionPin(int pin, int state, int pwm) {
    if (!isPinSafeForExpansion(pin)) {
        Serial.printf("[EXPANSION-GPIO] Warning: Pin %d is reserved for chassis/servos!\n", pin);
        return;
    }

    pinMode(pin, OUTPUT);
    if (pwm >= 0) {
        int duty = constrain(pwm, 0, 255);
        analogWrite(pin, duty);
    } else {
        digitalWrite(pin, state ? HIGH : LOW);
    }
}

// ============================================================================
// INDIVIDUAL MOTOR CONTROLLER (BTS7960 H-BRIDGE)
// ============================================================================
void driveBTS7960(int rpwmPin, int lpwmPin, int rpwmCh, int lpwmCh, float speed) {
    if (speed > 0.0f) {
        uint32_t duty = (uint32_t)speed;
        writePwmDuty(rpwmPin, rpwmCh, duty);
        writePwmDuty(lpwmPin, lpwmCh, 0);
    } else if (speed < 0.0f) {
        uint32_t duty = (uint32_t)(-speed);
        writePwmDuty(rpwmPin, rpwmCh, 0);
        writePwmDuty(lpwmPin, lpwmCh, duty);
    } else {
        writePwmDuty(rpwmPin, rpwmCh, 0);
        writePwmDuty(lpwmPin, lpwmCh, 0);
    }
}

// ============================================================================
// 4WD MOTION CONTROL MATRIX
// ============================================================================
void applyChassisSpeeds(float leftSpeed, float rightSpeed) {
    driveBTS7960(FL_RPWM_PIN, FL_LPWM_PIN, FL_RPWM_CH, FL_LPWM_CH, leftSpeed);
    driveBTS7960(RL_RPWM_PIN, RL_LPWM_PIN, RL_RPWM_CH, RL_LPWM_CH, leftSpeed);
    driveBTS7960(FR_RPWM_PIN, FR_LPWM_PIN, FR_RPWM_CH, FR_LPWM_CH, rightSpeed);
    driveBTS7960(RR_RPWM_PIN, RR_LPWM_PIN, RR_RPWM_CH, RR_LPWM_CH, rightSpeed);

    currentSpeeds.left = leftSpeed;
    currentSpeeds.right = rightSpeed;
}

void stopMotors() {
    applyChassisSpeeds(0.0f, 0.0f);
}

// ============================================================================
// DIFFERENTIAL STEERING (TANK DRIVE) MIXER ALGORITHM
// ============================================================================
void processDriveCommand(float fwd, float turn) {
    if (lineFollowerActive && (fwd != 0 || turn != 0)) {
        lineFollowerActive = false;
        Serial.println("[LINE-FOLLOWER] Suspended by manual override.");
    }

    float rawLeft  = fwd + turn;
    float rawRight = fwd - turn;

    float maxMagnitude = max(abs(rawLeft), abs(rawRight));
    float left = rawLeft;
    float right = rawRight;

    if (maxMagnitude > 255.0f) {
        left  = (rawLeft  / maxMagnitude) * 255.0f;
        right = (rawRight / maxMagnitude) * 255.0f;
    }

    if (abs(left) < MOTOR_DEADBAND)   left = 0.0f;
    if (abs(right) < MOTOR_DEADBAND)  right = 0.0f;

    applyChassisSpeeds(left, right);

    lastCommandTime = millis();
    failsafeActive = false;
}

// ============================================================================
// AUTONOMOUS LINE FOLLOWER SUBSYSTEM
// ============================================================================
void configureLineFollower(bool enable, int leftPin, int rightPin, int speed = 140, bool invert = false) {
    if (enable) {
        if (leftPin >= 0 && isPinSafeForExpansion(leftPin)) {
            linePinLeft = leftPin;
            pinMode(linePinLeft, INPUT_PULLUP);
        }
        if (rightPin >= 0 && isPinSafeForExpansion(rightPin)) {
            linePinRight = rightPin;
            pinMode(linePinRight, INPUT_PULLUP);
        }
        lineFollowerSpeed = constrain(speed, 60, 255);
        lineSensorInvert = invert;
        lineFollowerActive = true;
        Serial.printf("[LINE-FOLLOWER] Activated! Left Pin: %d, Right Pin: %d, Speed: %d\n",
                      linePinLeft, linePinRight, lineFollowerSpeed);
    } else {
        lineFollowerActive = false;
        stopMotors();
        Serial.println("[LINE-FOLLOWER] Deactivated.");
    }
}

void processLineFollower() {
    if (!lineFollowerActive || linePinLeft < 0 || linePinRight < 0) return;

    int rawLeft = digitalRead(linePinLeft);
    int rawRight = digitalRead(linePinRight);

    bool leftOnLine = lineSensorInvert ? (rawLeft == HIGH) : (rawLeft == LOW);
    bool rightOnLine = lineSensorInvert ? (rawRight == HIGH) : (rawRight == LOW);

    float fwd = 0.0f;
    float turn = 0.0f;

    if (leftOnLine && rightOnLine) {
        fwd = (float)lineFollowerSpeed;
        turn = 0.0f;
    } else if (leftOnLine && !rightOnLine) {
        fwd = (float)(lineFollowerSpeed * 0.70f);
        turn = -170.0f;
    } else if (!leftOnLine && rightOnLine) {
        fwd = (float)(lineFollowerSpeed * 0.70f);
        turn = 170.0f;
    } else {
        fwd = (float)(lineFollowerSpeed * 0.45f);
        turn = 0.0f;
    }

    applyChassisSpeeds(fwd + turn, fwd - turn);
    lastCommandTime = millis();
    failsafeActive = false;
}

// ============================================================================
// JSON COMMAND PARSER (Shared by HTTP, UDP, and UART)
// ============================================================================
void parseMotionJson(const char* jsonString) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        return;
    }

    // 1. Locomotive Drive Commands: {"fwd": 120, "turn": 50}
    if (doc.containsKey("fwd") && doc.containsKey("turn")) {
        float fwd  = doc["fwd"].as<float>();
        float turn = doc["turn"].as<float>();
        processDriveCommand(fwd, turn);
    }

    // 2. Operative 5-Axis Servo Commands: {"servos": [pan, tilt, leftEar, rightEar, tail]}
    if (doc.containsKey("servos")) {
        JsonArray sArr = doc["servos"].as<JsonArray>();
        if (sArr.size() >= 5) {
            setServoAngles(sArr[0].as<int>(), sArr[1].as<int>(), sArr[2].as<int>(), sArr[3].as<int>(), sArr[4].as<int>());
        }
    }

    // 3. Dynamic Custom Servo on ANY GPIO Pin: {"custom_servo": {"pin": 21, "angle": 90}}
    if (doc.containsKey("custom_servo")) {
        JsonObject cs = doc["custom_servo"].as<JsonObject>();
        int pin = cs["pin"].as<int>();
        int angle = cs.containsKey("angle") ? cs["angle"].as<int>() : 90;
        handleDynamicServo(pin, angle);
    }

    // 4. Autonomous Line Follower Subsystem
    if (doc.containsKey("line_follower")) {
        JsonObject lf = doc["line_follower"].as<JsonObject>();
        bool enable = lf["enable"].as<bool>();
        int leftPin = lf.containsKey("left_pin") ? lf["left_pin"].as<int>() : linePinLeft;
        int rightPin = lf.containsKey("right_pin") ? lf["right_pin"].as<int>() : linePinRight;
        int spd = lf.containsKey("speed") ? lf["speed"].as<int>() : 140;
        bool inv = lf.containsKey("invert") ? lf["invert"].as<bool>() : false;
        configureLineFollower(enable, leftPin, rightPin, spd, inv);
    }

    // 5. Dynamic Expansion GPIO Commands
    if (doc.containsKey("pin_cmd")) {
        JsonObject p = doc["pin_cmd"].as<JsonObject>();
        int pin = p["pin"].as<int>();
        
        if (p.containsKey("angle") || (p.containsKey("role") && p["role"].as<String>() == "SERVO")) {
            int angle = p.containsKey("angle") ? p["angle"].as<int>() : 90;
            handleDynamicServo(pin, angle);
        } else {
            int val = 0;
            if (p.containsKey("val")) {
                val = p["val"].as<int>();
            } else if (p.containsKey("state")) {
                String s = p["state"].as<String>();
                s.toUpperCase();
                val = (s == "HIGH" || s == "1" || s == "ON" || s == "TRUE") ? 1 : 0;
            }
            int pwm = p.containsKey("pwm") ? p["pwm"].as<int>() : -1;
            handleExpansionPin(pin, val, pwm);
        }
    }
}

// ============================================================================
// REST API & HTTP SERVER ROUTES
// ============================================================================
void setupWebServer() {
    // 1. Root: Serves Standalone Web Controller
    server.on("/", HTTP_GET, []() {
        server.sendHeader("Connection", "close");
        server.send_P(200, "text/html", index_html);
    });

    // 2. Telemetry Status
    server.on("/api/status", HTTP_GET, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        StaticJsonDocument<384> doc;
        doc["status"] = failsafeActive ? "failsafe_braked" : "active";
        doc["failsafe"] = failsafeActive;
        doc["speed_left"] = (int)currentSpeeds.left;
        doc["speed_right"] = (int)currentSpeeds.right;
        JsonArray sArr = doc.createNestedArray("servos");
        for (int i = 0; i < 5; i++) sArr.add(currentServoAngles[i]);
        doc["uptime_ms"] = millis();
        doc["free_heap"] = ESP.getFreeHeap();
        doc["rssi"] = WiFi.RSSI();
        doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
        String json;
        serializeJson(doc, json);
        server.send(200, "application/json", json);
    });

    // 3. Drive Command API: /api/drive?fwd=120&turn=40
    server.on("/api/drive", HTTP_ANY, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.method() == HTTP_OPTIONS) { server.send(204); return; }

        float fwd = 0.0f;
        float turn = 0.0f;
        if (server.hasArg("fwd")) fwd = server.arg("fwd").toFloat();
        if (server.hasArg("turn")) turn = server.arg("turn").toFloat();

        processDriveCommand(fwd, turn);
        server.send(200, "application/json", "{\"status\":\"ok\"}");
    });

    // 4. Emergency Stop: /api/stop
    server.on("/api/stop", HTTP_ANY, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.method() == HTTP_OPTIONS) { server.send(204); return; }
        stopMotors();
        server.send(200, "application/json", "{\"status\":\"stopped\"}");
    });

    // 5. Servos API: /api/servos?pan=90&tilt=90&lear=90&rear=90&tail=90
    server.on("/api/servos", HTTP_ANY, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.method() == HTTP_OPTIONS) { server.send(204); return; }

        int pan = server.hasArg("pan") ? server.arg("pan").toInt() : currentServoAngles[0];
        int tilt = server.hasArg("tilt") ? server.arg("tilt").toInt() : currentServoAngles[1];
        int lear = server.hasArg("lear") ? server.arg("lear").toInt() : currentServoAngles[2];
        int rear = server.hasArg("rear") ? server.arg("rear").toInt() : currentServoAngles[3];
        int tail = server.hasArg("tail") ? server.arg("tail").toInt() : currentServoAngles[4];

        setServoAngles(pan, tilt, lear, rear, tail);
        server.send(200, "application/json", "{\"status\":\"ok\"}");
    });

    // 6. Generic JSON Command: /api/cmd (POST body)
    server.on("/api/cmd", HTTP_POST, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.hasArg("plain")) {
            parseMotionJson(server.arg("plain").c_str());
            server.send(200, "application/json", "{\"status\":\"ok\"}");
        } else {
            server.send(400, "application/json", "{\"error\":\"missing_body\"}");
        }
    });

    // 7. Dynamic Custom Servo: /api/custom_servo?pin=21&angle=90
    server.on("/api/custom_servo", HTTP_ANY, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.method() == HTTP_OPTIONS) { server.send(204); return; }

        if (server.hasArg("pin")) {
            int pin = server.arg("pin").toInt();
            int angle = server.hasArg("angle") ? server.arg("angle").toInt() : 90;
            handleDynamicServo(pin, angle);
            server.send(200, "application/json", "{\"status\":\"ok\"}");
        } else {
            server.send(400, "application/json", "{\"error\":\"missing_pin\"}");
        }
    });

    // 8. Dynamic Expansion Pin: /api/pin_cmd?pin=2&state=1&pwm=-1
    server.on("/api/pin_cmd", HTTP_ANY, []() {
        server.sendHeader("Access-Control-Allow-Origin", "*");
        if (server.method() == HTTP_OPTIONS) { server.send(204); return; }

        if (server.hasArg("pin")) {
            int pin = server.arg("pin").toInt();
            int state = server.hasArg("state") ? server.arg("state").toInt() : 0;
            int pwm = server.hasArg("pwm") ? server.arg("pwm").toInt() : -1;
            handleExpansionPin(pin, state, pwm);
            server.send(200, "application/json", "{\"status\":\"ok\"}");
        } else {
            server.send(400, "application/json", "{\"error\":\"missing_pin\"}");
        }
    });

    // CORS preflight fallback for any route
    server.onNotFound([]() {
        if (server.method() == HTTP_OPTIONS) {
            server.sendHeader("Access-Control-Allow-Origin", "*");
            server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
            server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
            server.send(204);
        } else {
            server.send(404, "text/plain", "Not Found");
        }
    });

    server.begin();
    Serial.println("[HTTP] Web Controller Server started on port 80");
}

// ============================================================================
// HIGH-SPEED DIRECT UDP COMMAND LISTENER (PORT 8888)
// ============================================================================
void readUdpCommands() {
    int packetSize = udpMotor.parsePacket();
    if (packetSize > 0) {
        int len = udpMotor.read(udpBuffer, sizeof(udpBuffer) - 1);
        if (len > 0) {
            udpBuffer[len] = '\0';
            parseMotionJson(udpBuffer);
        }
    }
}

// ============================================================================
// AUXILIARY UART PACKET LISTENER (BACKWARD COMPATIBILITY)
// ============================================================================
void readSerialCommands() {
    while (Serial1.available() > 0) {
        char c = (char)Serial1.read();
        if (c == '\n' || c == '\r') {
            if (bufferIndex > 0) {
                serialBuffer[bufferIndex] = '\0';
                parseMotionJson(serialBuffer);
                bufferIndex = 0;
            }
        } else {
            if (bufferIndex < SERIAL_BUFFER_LEN - 1) {
                serialBuffer[bufferIndex++] = c;
            } else {
                bufferIndex = 0;
            }
        }
    }
}

// ============================================================================
// ARDUINO SETUP
// ============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n==========================================================");
    Serial.println("  PROJECT L.O.O.N.A. - CHASSIS & MOTION CONTROLLER        ");
    Serial.println("  Standalone Web Controller + High-Speed UDP Matrix       ");
    Serial.println("==========================================================");

    // 1. Auxiliary Hardware UART (Serial1)
    Serial1.begin(UART_BAUD_RATE, SERIAL_8N1, CHASSIS_RX_PIN, CHASSIS_TX_PIN);
    Serial.printf("[UART] Auxiliary Serial1 listening on RX: GPIO %d\n", CHASSIS_RX_PIN);

    // 2. Initialize 8 LEDC Hardware PWM Channels for 4x BTS7960 H-Bridges
    Serial.println("[PWM] Initializing 8-Channel LEDC Matrix (20 kHz, 8-Bit)...");
    initPwmPin(FL_RPWM_PIN, FL_RPWM_CH);
    initPwmPin(FL_LPWM_PIN, FL_LPWM_CH);
    initPwmPin(FR_RPWM_PIN, FR_RPWM_CH);
    initPwmPin(FR_LPWM_PIN, FR_LPWM_CH);
    initPwmPin(RL_RPWM_PIN, RL_RPWM_CH);
    initPwmPin(RL_LPWM_PIN, RL_LPWM_CH);
    initPwmPin(RR_RPWM_PIN, RR_RPWM_CH);
    initPwmPin(RR_LPWM_PIN, RR_LPWM_CH);

    // 3. Initialize 5-Axis Built-in Servo Matrix
    initServos();

    // 4. Initial Safe State: All Motors Stopped
    stopMotors();
    lastCommandTime = millis();

    // 5. Connect to Wi-Fi Station
    Serial.printf("[WiFi] Connecting to %s ...\n", WIFI_SSID);
    WiFi.mode(WIFI_AP_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long startWifi = millis();
    bool wifiConnected = false;
    while (millis() - startWifi < 8000) {
        if (WiFi.status() == WL_CONNECTED) {
            wifiConnected = true;
            break;
        }
        delay(250);
        Serial.print(".");
    }
    Serial.println();

    if (wifiConnected) {
        Serial.printf("[WiFi] Connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf(">>> OPEN IN PHONE/BROWSER: http://%s/ <<<\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("[WiFi] Station connection timed out. Starting fallback SoftAP hotspot...");
        WiFi.softAP(SOFTAP_SSID, SOFTAP_PASSWORD);
        Serial.printf("[WiFi-AP] Hotspot '%s' active! Connect to: http://%s/\n",
                      SOFTAP_SSID, WiFi.softAPIP().toString().c_str());
    }

    // 6. Start Web Controller HTTP Server
    setupWebServer();

    // 7. Start Direct High-Speed UDP Listener
    if (udpMotor.begin(MOTOR_UDP_PORT)) {
        Serial.printf("[UDP] Direct Motor Listener active on Port %d\n", MOTOR_UDP_PORT);
    }

    Serial.println("[SYS] Chassis Controller Ready. Watchdog Armed (800ms timeout).\n");
}

// ============================================================================
// ARDUINO MAIN LOOP
// ============================================================================
void loop() {
    // 1. Handle incoming HTTP Web Controller clients & REST API requests
    server.handleClient();

    // 2. Handle incoming high-speed UDP datagrams from Python Brain
    readUdpCommands();

    // 3. Handle incoming auxiliary UART commands
    readSerialCommands();

    // 4. Autonomous Line Follower Routine (if activated)
    if (lineFollowerActive) {
        processLineFollower();
    } else {
        // Safety Watchdog Check (automatically halts motors if signal is lost)
        if (!failsafeActive && (millis() - lastCommandTime > FAILSAFE_TIMEOUT_MS)) {
            stopMotors();
            failsafeActive = true;
        }
    }

    delay(2);
}
