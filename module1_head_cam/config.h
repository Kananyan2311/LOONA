#pragma once

// ============================================================================
// LOONA ROBOT - MODULE 1: HEAD CONTROLLER CONFIGURATION
// ============================================================================

// --- WiFi Settings ---
#define WIFI_SSID         "realme C30s"
#define WIFI_PASSWORD     "hatdogniivan"

// --- Host PC / Server Brain Network Configuration ---
#define SERVER_HOST       "192.168.100.228"    // IP address of Host PC running FastAPI (Detected on Wi-Fi)
#define SERVER_WS_PORT    8000                 // FastAPI WebSocket Port
#define SERVER_WS_PATH    "/ws/audio"          // Bidirectional Audio Streaming Endpoint
#define MOTOR_UDP_PORT    8888                 // Port for UDP Motor Control Datagrams
#define HTTP_STREAM_PORT  80                   // HTTP Port for Camera MJPEG Stream (/stream)

// --- Pin Configurations (ESP32-S3 CAM matching your schematic) ---
#define UART_BAUD_RATE    115200

// Hardware UART Link to Chassis MCU (ESP32-S3)
#define CAM_UART_TX_PIN   36                   // Pin 30: GPIO36 -> TX1 (relays commands to Chassis RX)
#define CAM_UART_RX_PIN   35                   // Pin 29: GPIO35 -> RX1 (receives telemetry from Chassis TX)

// I2S Microphone (INMP441) [I2S Port 0 RX]
#define I2S_MIC_SD_PIN    39                   // Pin 33: GPIO39-SD -> SD (Serial Data)
#define I2S_MIC_SCK_PIN   38                   // Pin 32: GPIO38-SD -> SCK (Serial Clock)
#define I2S_MIC_WS_PIN    37                   // Pin 31: GPIO37-PSRAM -> WS (Word Select)

// I2S Speaker Amplifier (MAX98357A) [I2S Port 1 TX]
#define I2S_SPK_BCLK_PIN  1                    // Pin 38: GPIO1 -> BLK / BCLK (Bit Clock)
#define I2S_SPK_LRC_PIN   2                    // Pin 37: GPIO2 -> LRC (Left/Right Clock)
#define I2S_SPK_DIN_PIN   42                   // Pin 36: GPIO42 -> DIN (Data In)

// I2C Peripheral Bus (OLED Display / Sensors)
#define I2C_SCL_PIN       41                   // Pin 35: GPIO41 -> SCL (I2C Clock)
#define I2C_SDA_PIN       40                   // Pin 34: GPIO40-SD -> SDA (I2C Data)

#define I2S_MIC_SAMPLE_RATE 16000              // 16 kHz for Whisper Speech Recognition
#define I2S_MIC_BUFFER_SIZE 1024               // Audio chunk size (bytes) - optimized 31 pkts/sec
#define I2S_SPK_SAMPLE_RATE 24000              // 24 kHz for High-Quality TTS Playback
#define I2S_SPK_BUFFER_SIZE 1024

// --- Camera Streaming Configuration (Minimized Bandwidth & Zero Congestion) ---
#define CAMERA_JPEG_QUALITY  32                // 10-63 (32 = ultra-lightweight ~2-3KB frames, zero WiFi congestion)
#define CAMERA_FRAME_SIZE    FRAMESIZE_QVGA    // 320x240 for crisp tracking with minimal data
#define CAMERA_FB_COUNT      2                 // Double buffering with PSRAM
