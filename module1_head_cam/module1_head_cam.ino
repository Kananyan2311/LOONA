/*
 * ====================================================================================================
 * LOONA ROBOT - MODULE 1: HEAD CONTROLLER FIRMWARE
 * Hardware Target: ESP32-S3 CAM (OV2640 + INMP441 + MAX98357A + UART Link)
 * ====================================================================================================
 * Architecture:
 *   1. OV2640 Camera: Native HTTP MJPEG multipart video streaming (/stream) @ 320x240 (QVGA) 20+ FPS.
 *   2. INMP441 MEMS Mic: I2S Port 0 (RX), 16-bit 16kHz Mono -> WebSocket client streaming to Python brain.
 *   3. MAX98357A I2S Amp: I2S Port 1 (TX), 16-bit 24kHz Stereo/Mono <- WebSocket PCM audio from TTS engine.
 *   4. UDP Command Listener: Port 8888 captures JSON drive datagrams {"fwd": 120, "turn": 50}.
 *   5. Hardware UART (Serial1): Instantly relays movement commands to Chassis MCU (ESP32-S3 DevKitC).
 *
 * Dependencies (Arduino IDE Library Manager):
 *   - "WebSockets" by Markus Sattler (v2.4.0+)
 *   - "esp32" board package by Espressif (v2.0.x or v3.0.x)
 * ====================================================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebSocketsClient.h>
#include <driver/i2s.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "camera_pins.h"
#include "config.h"

// --- Global Handles & Objects ---
static httpd_handle_t camera_httpd = NULL;
WebSocketsClient wsAudio;
WiFiUDP udpMotor;

// Task Handles
TaskHandle_t audioTaskHandle = NULL;
TaskHandle_t motionRelayTaskHandle = NULL;

// Buffer for UDP motor and expansion commands
static char udpBuffer[512];

// ============================================================================
// CAMERA INITIALIZATION & MJPEG HTTP STREAM HANDLER
// ============================================================================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY     = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART         = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t *_jpg_buf = NULL;
    char part_buf[128];

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[CAM] Camera capture failed");
            res = ESP_FAIL;
            break;
        }

        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;

        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 128, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }

        esp_camera_fb_return(fb);
        fb = NULL;
        _jpg_buf = NULL;

        if (res != ESP_OK) {
            break;
        }
        // Pace camera stream to ~12 FPS to eliminate WiFi buffer congestion and free radio bandwidth
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    return res;
}

static esp_err_t capture_handler(httpd_req_t *req) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return res;
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = HTTP_STREAM_PORT;
    config.ctrl_port = HTTP_STREAM_PORT + 1;
    config.max_open_sockets = 4;

    httpd_uri_t stream_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t capture_uri = {
        .uri       = "/capture",
        .method    = HTTP_GET,
        .handler   = capture_handler,
        .user_ctx  = NULL
    };

    Serial.printf("[HTTP] Starting MJPEG Stream Server on port %d...\n", config.server_port);
    if (httpd_start(&camera_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &stream_uri);
        httpd_register_uri_handler(camera_httpd, &capture_uri);
        Serial.printf("[HTTP] Camera Stream ready at: http://%s:%d/stream\n",
                      WiFi.localIP().toString().c_str(), HTTP_STREAM_PORT);
    } else {
        Serial.println("[HTTP] Failed to start HTTP server!");
    }
}

bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = CAMERA_FRAME_SIZE;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;
    config.fb_count     = CAMERA_FB_COUNT;
    config.fb_location  = CAMERA_FB_IN_PSRAM;
    config.grab_mode    = CAMERA_GRAB_LATEST;

    // Check PSRAM presence
    if (!psramFound()) {
        Serial.println("[CAM] WARNING: PSRAM not found! Falling back to DRAM and lower buffer count.");
        config.fb_location = CAMERA_FB_IN_DRAM;
        config.fb_count = 1;
        config.jpeg_quality = 16;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[CAM] Camera init failed with error 0x%x\n", err);
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_vflip(s, 0);       // Adjust 1 or 0 depending on physical mount orientation
        s->set_hmirror(s, 0);
        s->set_brightness(s, 1);
        s->set_contrast(s, 1);
    }
    Serial.println("[CAM] OV2640 initialized successfully.");
    return true;
}

// ============================================================================
// I2S DUAL BUS CONFIGURATION (PORT 0: INMP441 MIC, PORT 1: MAX98357A SPEAKER)
// ============================================================================
void initI2SMicrophone() {
    i2s_config_t i2s_mic_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = I2S_MIC_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT, // INMP441 L/R pin tied to GND = Left
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t mic_pins = {
        .bck_io_num = I2S_MIC_SCK_PIN,
        .ws_io_num = I2S_MIC_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_MIC_SD_PIN
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_mic_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("[I2S-0] Failed to install Mic driver: 0x%x\n", err);
        return;
    }
    err = i2s_set_pin(I2S_NUM_0, &mic_pins);
    if (err != ESP_OK) {
        Serial.printf("[I2S-0] Failed to set Mic pins: 0x%x\n", err);
        return;
    }
    i2s_zero_dma_buffer(I2S_NUM_0);
    Serial.println("[I2S-0] INMP441 Mic (16kHz 16-bit Mono) initialized.");
}

static volatile unsigned long lastSpeakerAudioMillis = 0;

void initI2SSpeaker() {
    i2s_config_t i2s_spk_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = I2S_SPK_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // Stereo / Mono downmix supported
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 1024,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t spk_pins = {
        .bck_io_num = I2S_SPK_BCLK_PIN,
        .ws_io_num = I2S_SPK_LRC_PIN,
        .data_out_num = I2S_SPK_DIN_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_1, &i2s_spk_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("[I2S-1] Failed to install Speaker driver: 0x%x\n", err);
        return;
    }
    err = i2s_set_pin(I2S_NUM_1, &spk_pins);
    if (err != ESP_OK) {
        Serial.printf("[I2S-1] Failed to set Speaker pins: 0x%x\n", err);
        return;
    }
    i2s_zero_dma_buffer(I2S_NUM_1);
    Serial.println("[I2S-1] MAX98357A Amp (24kHz 16-bit, 16KB DMA Buffer) initialized.");
}

// ============================================================================
// WEBSOCKET AUDIO CLIENT (BIDIRECTIONAL AUDIO LINK)
// ============================================================================
void webSocketAudioEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS-AUDIO] Disconnected from Brain Server.");
            break;
        case WStype_CONNECTED:
            Serial.printf("[WS-AUDIO] Connected to: %s\n", payload);
            break;
        case WStype_TEXT:
            // Control/metadata frames from brain (e.g. state changes)
            Serial.printf("[WS-AUDIO] Text payload: %.*s\n", (int)length, (char*)payload);
            if (strstr((const char*)payload, "\"spk_start\"") != NULL) {
                lastSpeakerAudioMillis = millis();
            } else if (strstr((const char*)payload, "\"spk_done\"") != NULL) {
                lastSpeakerAudioMillis = millis() + 350; // Keep mic muted for 350ms while DMA finishes
            }
            break;
        case WStype_BIN:
            // Incoming TTS / Music audio stream from Python server (Raw PCM 24kHz 16-bit, 1024-byte chunks)
            if (length > 0) {
                lastSpeakerAudioMillis = millis();
                size_t totalWritten = 0;
                while (totalWritten < length) {
                    size_t written = 0;
                    esp_err_t err = i2s_write(I2S_NUM_1, payload + totalWritten, length - totalWritten, &written, pdMS_TO_TICKS(40));
                    if (err != ESP_OK || written == 0) break;
                    totalWritten += written;
                }
            }
            break;
        case WStype_ERROR:
            Serial.printf("[WS-AUDIO] Error: %s\n", payload);
            break;
        default:
            break;
    }
}

// ============================================================================
// FREERTOS REAL-TIME AUDIO TASK (CORE 1)
// ============================================================================
void audioTask(void *pvParameters) {
    uint8_t micBuffer[I2S_MIC_BUFFER_SIZE];
    size_t bytesRead = 0;
    unsigned long speechHangoverMillis = 0;
    unsigned long lastKeepAliveMic = 0;

    Serial.println("[TASK] Audio Task started on Core 1.");

    while (true) {
        // Poll WebSocket connection
        wsAudio.loop();

        // Check if robot is actively outputting sound to speaker (within 400ms)
        bool isSpeakerActive = (millis() - lastSpeakerAudioMillis < 400);

        if (wsAudio.isConnected() && !isSpeakerActive) {
            // Read mic data with 40ms FreeRTOS timeout so buffer fills properly
            esp_err_t res = i2s_read(I2S_NUM_0, micBuffer, sizeof(micBuffer), &bytesRead, pdMS_TO_TICKS(40));
            if ((res == ESP_OK || res == ESP_ERR_TIMEOUT) && bytesRead >= 128) {
                // Compute energy (RMS) on raw microphone samples
                int16_t *samples = (int16_t *)micBuffer;
                size_t numSamples = bytesRead / 2;
                int64_t sumSquares = 0;
                for (size_t i = 0; i < numSamples; i++) {
                    int32_t s = samples[i];
                    sumSquares += s * s;
                }
                int32_t rms = (int32_t)sqrt(sumSquares / numSamples);

                // High-sensitivity speech detection (RMS > 35) + 600ms hangover
                // keeps words and syllables intact without clipping
                if (rms > 35) {
                    speechHangoverMillis = millis() + 600;
                }

                // Send when speaking OR send 1 keep-alive packet every 1.5s during silence
                if (millis() < speechHangoverMillis || (millis() - lastKeepAliveMic > 1500)) {
                    wsAudio.sendBIN(micBuffer, bytesRead);
                    lastKeepAliveMic = millis();
                }
            }
        } else {
            // Task sleeps when speaker is playing to preserve WiFi bandwidth
            vTaskDelay(pdMS_TO_TICKS(10));
        }

        // Delay to allow WiFi stack and other tasks to breathe
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}

// ============================================================================
// FREERTOS UDP MOTOR COMMAND LISTENER & UART RELAY TASK (CORE 1)
// ============================================================================
void motionRelayTask(void *pvParameters) {
    Serial.println("[TASK] Motion Relay Task started on Core 1.");

    while (true) {
        int packetSize = udpMotor.parsePacket();
        if (packetSize > 0) {
            int len = udpMotor.read(udpBuffer, sizeof(udpBuffer) - 1);
            if (len > 0) {
                udpBuffer[len] = '\0';
                // Instantly relay over Hardware Serial1 to Chassis MCU
                Serial1.println(udpBuffer);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(5)); // Low latency polling (200Hz check)
    }
}

// ============================================================================
// ARDUINO SETUP & MAIN LOOP
// ============================================================================
void setup() {
    // 1. Initialize USB Debug Console
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=========================================");
    Serial.println("  LOONA HEAD CONTROLLER (ESP32-S3 CAM)   ");
    Serial.println("=========================================");

    // 2. Initialize Inter-MCU Hardware UART Link to Chassis MCU
    // Physical Link: CAM_TX (GPIO 17) -> DEVKIT_RX (GPIO 16)
    //                CAM_RX (GPIO 16) <- DEVKIT_TX (GPIO 17)
    Serial1.begin(UART_BAUD_RATE, SERIAL_8N1, CAM_UART_RX_PIN, CAM_UART_TX_PIN);
    Serial.printf("[UART] Inter-MCU Serial1 initialized at %d baud (TX: %d, RX: %d)\n",
                  UART_BAUD_RATE, CAM_UART_TX_PIN, CAM_UART_RX_PIN);

    // 3. Connect to Local WiFi Network
    Serial.printf("[WIFI] Connecting to SSID: %s", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false); // Disable WiFi power saving for minimum latency
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int wifiRetry = 0;
    while (WiFi.status() != WL_CONNECTED && wifiRetry < 30) {
        delay(1000);
        Serial.print(".");
        wifiRetry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[WIFI] Connected! Assigned IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[WIFI] Failed to connect! Continuing offline mode...");
    }

    // 4. Initialize OV2640 Camera & Start HTTP MJPEG Streaming
    if (initCamera()) {
        startCameraServer();
    } else {
        Serial.println("[CAM] Camera initialization failed!");
    }

    // 5. Initialize I2S Audio Subsystems
    initI2SMicrophone();
    initI2SSpeaker();

    // 6. Initialize UDP Motor Listener
    if (udpMotor.begin(MOTOR_UDP_PORT)) {
        Serial.printf("[UDP] Motor listener active on UDP port %d\n", MOTOR_UDP_PORT);
    } else {
        Serial.printf("[UDP] Failed to bind to UDP port %d\n", MOTOR_UDP_PORT);
    }

    // 7. Initialize Audio WebSocket Client to Brain Server
    Serial.printf("[WS-AUDIO] Connecting to ws://%s:%d%s\n", SERVER_HOST, SERVER_WS_PORT, SERVER_WS_PATH);
    wsAudio.begin(SERVER_HOST, SERVER_WS_PORT, SERVER_WS_PATH);
    wsAudio.onEvent(webSocketAudioEvent);
    wsAudio.setReconnectInterval(1500);
    wsAudio.enableHeartbeat(30000, 15000, 4);

    // 8. Launch Real-time Audio and Motion Tasks on FreeRTOS Core 1
    xTaskCreatePinnedToCore(
        audioTask,
        "AudioStreamTask",
        8192,
        NULL,
        3,          // High priority for audio streaming
        &audioTaskHandle,
        1           // Pinned to Core 1
    );

    xTaskCreatePinnedToCore(
        motionRelayTask,
        "MotionRelayTask",
        4096,
        NULL,
        2,          // Medium priority for motion datagram relay
        &motionRelayTaskHandle,
        1           // Pinned to Core 1
    );

    Serial.println("[SYS] Head Controller Initialization Complete.\n");
}

void loop() {
    // Core 0 handles Camera HTTP Server and background WiFi tasks.
    // Core 1 handles real-time I2S Audio and UDP -> UART Motor relay.
    vTaskDelay(pdMS_TO_TICKS(2));
}
