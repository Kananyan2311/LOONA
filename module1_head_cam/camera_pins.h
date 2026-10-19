#pragma once

// ============================================================================
// CAMERA PIN CONFIGURATIONS FOR ESP32-CAM & ESP32-S3 CAM
// ============================================================================
// Supports standard default AI-Thinker ESP32-CAM as well as ESP32-S3 boards.
// ============================================================================

// Select your board model below (Default is ESP32-S3 CAM matching your schematic):
#define CAMERA_MODEL_ESP32S3_CAM
// #define CAMERA_MODEL_AI_THINKER

#if defined(CAMERA_MODEL_ESP32S3_CAM) || defined(CAMERA_MODEL_FREENOVE_ESP32S3_CAM)
  // ESP32-S3 CAM (OV2640 with onboard camera ribbon - Pins match "ESP32S3 CAM COPY" schematic)
  #define PWDN_GPIO_NUM     -1
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM     15                   // GPIO15-CAM
  #define SIOD_GPIO_NUM      4                   // GPIO4-CAM
  #define SIOC_GPIO_NUM      5                   // GPIO5-CAM

  #define Y9_GPIO_NUM       16                   // GPIO16-CAM
  #define Y8_GPIO_NUM       17                   // GPIO17-CAM
  #define Y7_GPIO_NUM       18                   // GPIO18-CAM
  #define Y6_GPIO_NUM       12                   // GPIO12-CAM
  #define Y5_GPIO_NUM       10                   // GPIO10-CAM
  #define Y4_GPIO_NUM        8                   // GPIO8-CAM
  #define Y3_GPIO_NUM        9                   // GPIO9-CAM
  #define Y2_GPIO_NUM       11                   // GPIO11-CAM
  #define VSYNC_GPIO_NUM     6                   // GPIO6-CAM
  #define HREF_GPIO_NUM      7                   // GPIO7-CAM
  #define PCLK_GPIO_NUM     13                   // GPIO13-CAM

#elif defined(CAMERA_MODEL_AI_THINKER)
  // Standard Default AI-Thinker ESP32-CAM (Classic OV2640)
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27

  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22

#elif defined(CAMERA_MODEL_FREENOVE_ESP32S3_CAM)
  #define PWDN_GPIO_NUM     -1
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM     15
  #define SIOD_GPIO_NUM      4
  #define SIOC_GPIO_NUM      5

  #define Y9_GPIO_NUM       16
  #define Y8_GPIO_NUM       17
  #define Y7_GPIO_NUM       18
  #define Y6_GPIO_NUM       12
  #define Y5_GPIO_NUM       10
  #define Y4_GPIO_NUM        8
  #define Y3_GPIO_NUM        9
  #define Y2_GPIO_NUM       11
  #define VSYNC_GPIO_NUM     6
  #define HREF_GPIO_NUM      7
  #define PCLK_GPIO_NUM     13

#elif defined(CAMERA_MODEL_AI_THINKER_ESP32S3_CAM)
  #define PWDN_GPIO_NUM     -1
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM     10
  #define SIOD_GPIO_NUM     21
  #define SIOC_GPIO_NUM     14

  #define Y9_GPIO_NUM       11
  #define Y8_GPIO_NUM        9
  #define Y7_GPIO_NUM        8
  #define Y6_GPIO_NUM        6
  #define Y5_GPIO_NUM        4
  #define Y4_GPIO_NUM        2
  #define Y3_GPIO_NUM        3
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    13
  #define HREF_GPIO_NUM     12
  #define PCLK_GPIO_NUM      7

#elif defined(CAMERA_MODEL_ESP32S3_EYE)
  #define PWDN_GPIO_NUM     -1
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM     15
  #define SIOD_GPIO_NUM      4
  #define SIOC_GPIO_NUM      5

  #define Y9_GPIO_NUM       16
  #define Y8_GPIO_NUM       17
  #define Y7_GPIO_NUM       18
  #define Y6_GPIO_NUM       12
  #define Y5_GPIO_NUM       10
  #define Y4_GPIO_NUM        8
  #define Y3_GPIO_NUM        9
  #define Y2_GPIO_NUM       11
  #define VSYNC_GPIO_NUM     6
  #define HREF_GPIO_NUM      7
  #define PCLK_GPIO_NUM     13

#else
  #error "Camera model not selected! Please define a camera model in camera_pins.h"
#endif
