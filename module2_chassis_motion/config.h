#pragma once

// ============================================================================
// LOONA ROBOT - MODULE 2: CHASSIS & MOTION CONTROLLER CONFIGURATION
// Hardware Target: ESP32-S3 DevKitC (4WD BTS7960 H-Bridge Matrix)
// ============================================================================

// --- WiFi & Web Controller Configuration ---
#define WIFI_SSID           "realme C30s"
#define WIFI_PASSWORD       "hatdogniivan"
#define WEB_SERVER_PORT     80
#define MOTOR_UDP_PORT      8888

// Fallback SoftAP hotspot (connect directly if router is offline)
#define SOFTAP_SSID         "LOONA-CHASSIS-CONTROLLER"
#define SOFTAP_PASSWORD     "12345678"

// --- Hardware UART Configuration (Auxiliary / Backward Compatibility) ---
#define UART_BAUD_RATE      115200
#define CHASSIS_RX_PIN      21        // Auxiliary RX (relocated from 16 to avoid conflict with FR_LPWM)
#define CHASSIS_TX_PIN      1         // Auxiliary TX

// --- Watchdog & Safety Failsafe ---
#define FAILSAFE_TIMEOUT_MS 800       // Stop all motors if no command received within 800ms
#define MOTOR_DEADBAND      12        // Ignore noisy joystick inputs below threshold

// --- LEDC Hardware PWM Configuration ---
#define PWM_FREQ_HZ         20000     // 20 kHz ultrasonic frequency (eliminates audible motor whine)
#define PWM_RESOLUTION_BITS 8         // 8-bit resolution (0 - 255)
#define PWM_MAX_DUTY        255       // Max duty cycle

// --- BTS7960 Motor Driver Pin Assignments ---
// Note: All R_EN and L_EN pins on the 4x BTS7960 modules are hardwired to 3.3V

// 1. FRONT LEFT (BTS7960 Module 1)
#define FL_RPWM_PIN         4         // Forward PWM
#define FL_LPWM_PIN         5         // Reverse PWM

// 2. FRONT RIGHT (BTS7960 Module 2)
#define FR_RPWM_PIN         15        // Forward PWM
#define FR_LPWM_PIN         16        // Reverse PWM

// 3. REAR LEFT (BTS7960 Module 3)
#define RL_RPWM_PIN         6         // Forward PWM
#define RL_LPWM_PIN         7         // Reverse PWM

// 4. REAR RIGHT (BTS7960 Module 4)
#define RR_RPWM_PIN         17        // Forward PWM
#define RR_LPWM_PIN         18        // Reverse PWM

// --- LEDC PWM Channels (For Arduino ESP32 Core v2.x channel-based allocation) ---
#define FL_RPWM_CH          10
#define FL_LPWM_CH          11
#define FR_RPWM_CH          12
#define FR_LPWM_CH          13
#define RL_RPWM_CH          14
#define RL_LPWM_CH          21
#define RR_RPWM_CH          20
#define RR_LPWM_CH          19

// ============================================================================
// 5-CHANNEL SERVO MATRIX CONFIGURATION (ESP32-S3 DEVKITC)
// ============================================================================
#define SERVO_HEAD_PAN_PIN    1         // Servo 1: Head Horizontal Pan (0 - 180 deg)
#define SERVO_HEAD_TILT_PIN   2        // Servo 2: Head Vertical Tilt (0 - 180 deg)
#define SERVO_LEFT_EAR_PIN    39        // Servo 3: Left Ear Wiggle / Perk (0 - 180 deg)
#define SERVO_RIGHT_EAR_PIN   9        // Servo 4: Right Ear Wiggle / Perk (0 - 180 deg)
#define SERVO_TAIL_PIN        14        // Servo 5: Tail / Aux Wag (0 - 180 deg)

#define SERVO_MIN_PULSE_US    500       // Standard SG90 / MG90S min pulse width (0 deg)
#define SERVO_MAX_PULSE_US    2400      // Standard SG90 / MG90S max pulse width (180 deg)
#define SERVO_DEFAULT_ANGLE   90        // Neutral center angle

// ============================================================================
// DYNAMIC EXPANSION GPIO LIST
// Supported pins for user expansion (LEDs, relays, buzzers, sensors, etc.):
// GPIO 2, 3, 21, 38, 47, 48 (Note: 4, 5, 6, 7, 15, 16, 17, 18 reserved for 4WD)
// ============================================================================

