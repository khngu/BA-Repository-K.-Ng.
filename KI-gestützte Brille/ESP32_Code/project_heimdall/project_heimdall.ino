#include <WiFi.h>
#include <WiFiClient.h>
#include "esp_camera.h"
#include "ESP32_OV5640_AF.h"

// WiFi credentials
const char *ssid = "***************";
const char *password = "***************";

// Server URL
const char* serverName = "YOUR_IP_ADRESS";
const int serverPort = 5000;
const char* serverPath = "/upload";

// Camera setup
#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM
#include "camera_pins.h"
OV5640 ov5640 = OV5640();

// Touch sensor pin
const int touchPin = 4;  // GPIO pin connected to SIG pin of TTP223B

unsigned long touchStartTime = 0;
bool touchActive = false;
bool modeChanged = false;
enum Mode { ANALYZE_TEXT, ANALYZE_OBJECT, CHATBOT };
Mode currentMode = ANALYZE_TEXT;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  pinMode(touchPin, INPUT);  // Set touch pin as input

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  // Initialize the camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;           // Set XCLK to 20 MHz
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_HD;         // Set resolution to HD (1280x720)
  config.jpeg_quality = 4;                  // Set quality to 4 (as per the screenshot)
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.fb_count = 2;                      // Use 2 frame buffers

  // Check for PSRAM
  if (psramFound()) {
      Serial.println("PSRAM found\n");
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
      Serial.println("PSRAM not found\n");
      config.frame_size = FRAMESIZE_SVGA;    // Set frame size to SVGA (800x600)
      config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Attempt to initialize the camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Initialize camera sensor and autofocus
  sensor_t *s = esp_camera_sensor_get();
  ov5640.start(s);
  
  // Apply the image adjustments
  s->set_hmirror(s,0);
  s->set_vflip(s, 0);   // flip vertical back (de-mirror)
  s->set_brightness(s, 3);  
  s->set_contrast(s, -1);     
  s->set_saturation(s, 4);   
  s->set_sharpness(s, 3); 

  // Enable automatic gain and exposure controls
  s->set_gain_ctrl(s, 1);     // Enable gain control
  s->set_exposure_ctrl(s, 1); // Enable exposure control
  s->set_whitebal(s, 1);      // Enable auto white balance

  if (ov5640.focusInit() == 0) {
    Serial.println("OV5640_Focus_Init Successful!");
  } else {
    Serial.println("OV5640_Focus_Init Failed!");
  }

  if (ov5640.autoFocusMode() == 0) {
    Serial.println("OV5640_Auto_Focus Successful!");
  } else {
    Serial.println("OV5640_Auto_Focus Failed!");
  }
}

void loop() {
  uint8_t rc = ov5640.getFWStatus();
  if (rc == -1) {
    Serial.println("Check your OV5640");
  } else if (rc == FW_STATUS_S_FOCUSED) {
    Serial.println("Focused!");
  } else if (rc == FW_STATUS_S_FOCUSING) {
    Serial.println("Focusing!");
  } else {
  }

  int touchState = digitalRead(touchPin);

  if (touchState == HIGH) {
    if (!touchActive) {
      touchStartTime = millis();
      touchActive = true;
      modeChanged = false;
    } else {
      unsigned long touchDuration = millis() - touchStartTime;
      if (touchDuration >= 1000 && !modeChanged) { // exactly 1 second
        handleLongPress();
        modeChanged = true;  // Ensure the mode only changes once per long press
      }
    }
  } else {
    if (touchActive) {
      if (!modeChanged) {
        handleShortPress();
      }
      touchActive = false;
    }
  }

  delay(100); // Check touch sensor every 100 ms
}

void handleShortPress() {

  if (currentMode == CHATBOT) {
    sendData("Chatbot", nullptr);
    return; 
  }

  // Focus the camera before capturing
  if (focusCamera()) {
    // Capture and send the image
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      return;
    }

    switch (currentMode) {
      case ANALYZE_TEXT:
        sendData("Analyze_Text", fb);
        break;
      case ANALYZE_OBJECT:
        sendData("Analyze_Object", fb);
        break;
    }

    // Return the frame buffer back to the driver for reuse
    esp_camera_fb_return(fb);
  } else {
    Serial.println("Autofocus failed, not capturing image.");
  }
}


bool focusCamera() {
  Serial.println("Starting autofocus...");

  // Initialize autofocus if it hasn't been initialized already
  if (ov5640.focusInit() != 0) {
    Serial.println("Focus initialization failed.");
    return false;
  }

  // Start the autofocus mode
  if (ov5640.autoFocusMode() != 0) {
    Serial.println("Autofocus mode start failed.");
    return false;
  }

  // Poll the focus status
  unsigned long focusStartTime = millis();
  while (true) {
    uint8_t focusStatus = ov5640.getFWStatus();
    if (focusStatus == FW_STATUS_S_FOCUSED) {
      Serial.println("Autofocus successful!");
      return true;
    } else if (focusStatus == FW_STATUS_S_FOCUSING) {
      if (millis() - focusStartTime > 5000) { // Timeout after 5 seconds
        Serial.println("Autofocus timeout.");
        return false;
      }
      delay(100); // Check focus status every 100ms
    } else {
      Serial.println("Autofocus failed.");
      return false;
    }
  }
}


void handleLongPress() {
  // Change mode on long press
  if (currentMode == CHATBOT) {
    currentMode = ANALYZE_TEXT;
  } else {
    currentMode = static_cast<Mode>(currentMode + 1);
  }
  Serial.print("Mode changed to: ");
  switch (currentMode) {
    case ANALYZE_TEXT:
      Serial.println("Analyze_Text");
      break;
    case ANALYZE_OBJECT:
      Serial.println("Analyze_Object");
      break;
    case CHATBOT:
      Serial.println("Chatbot");
      break;
  }

  sendModeChange();
}

void sendModeChange() {
  WiFiClient client;
  if (!client.connect(serverName, serverPort)) {
    Serial.println("Connection to server failed");
    return;
  }

  String mode;
  switch (currentMode) {
    case ANALYZE_TEXT:
      mode = "Analyze_Text";
      break;
    case ANALYZE_OBJECT:
      mode = "Analyze_Object";
      break;
    case CHATBOT:
      mode = "Chatbot";
      break;
  }

  String boundary = "----ESP32Boundary";
  String bodyStart = "--" + boundary + "\r\n";
  bodyStart += "Content-Disposition: form-data; name=\"mode\"\r\n\r\n";
  bodyStart += mode + "\r\n";
  String bodyEnd = "--" + boundary + "--\r\n";

  int contentLength = bodyStart.length() + bodyEnd.length();

  client.print(String("POST ") + "/mode" + " HTTP/1.1\r\n");
  client.print(String("Host: ") + serverName + "\r\n");
  client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
  client.print("Content-Length: " + String(contentLength) + "\r\n");
  client.print("\r\n");
  client.print(bodyStart);
  client.print(bodyEnd);

  // Wait for server response
  while (client.connected() && !client.available()) delay(1);
  while (client.available()) {
    String line = client.readStringUntil('\n');
    Serial.println(line);
  }

  client.stop();
}

void sendData(String status, camera_fb_t *fb) {
  if (status != "Chatbot") {
    WiFiClient client;
    if (!client.connect(serverName, serverPort)) {
      Serial.println("Connection to server failed");
      esp_camera_fb_return(fb);
      return;
    }

    String boundary = "----ESP32Boundary";
    String bodyStart = "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"file\"; filename=\"image.jpg\"\r\n";
    bodyStart += "Content-Type: image/jpeg\r\n\r\n";
    String statusPart = "\r\n--" + boundary + "\r\n";
    statusPart += "Content-Disposition: form-data; name=\"status\"\r\n\r\n";
    statusPart += status + "\r\n";
    String bodyEnd = "--" + boundary + "--\r\n";

    int contentLength = bodyStart.length() + fb->len + statusPart.length() + bodyEnd.length();

    client.print(String("POST ") + serverPath + " HTTP/1.1\r\n");
    client.print(String("Host: ") + serverName + "\r\n");
    client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
    client.print("Content-Length: " + String(contentLength) + "\r\n");
    client.print("\r\n");
    client.print(bodyStart);

    // Send the image buffer
    client.write(fb->buf, fb->len);

    // Send the status part
    client.print(statusPart);

    // Finish the request
    client.print(bodyEnd);

    // Wait for server response
    while (client.connected() && !client.available()) delay(1);
    while (client.available()) {
      String line = client.readStringUntil('\n');
      Serial.println(line);
    }

    client.stop();
  } else {
    // Handle the chatbot case without using the frame buffer
    WiFiClient client;
    if (!client.connect(serverName, serverPort)) {
      Serial.println("Connection to server failed");
      return;
    }

    String boundary = "----ESP32Boundary";
    String bodyStart = "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n";
    bodyStart += "Content-Type: image/jpeg\r\n\r\n";
    String statusPart = "\r\n--" + boundary + "\r\n";
    statusPart += "Content-Disposition: form-data; name=\"status\"\r\n\r\n";
    statusPart += status + "\r\n";
    String bodyEnd = "--" + boundary + "--\r\n";

    int contentLength = bodyStart.length() + statusPart.length() + bodyEnd.length();

    client.print(String("POST ") + serverPath + " HTTP/1.1\r\n");
    client.print(String("Host: ") + serverName + "\r\n");
    client.print("Content-Type: multipart/form-data; boundary=" + boundary + "\r\n");
    client.print("Content-Length: " + String(contentLength) + "\r\n");
    client.print("\r\n");
    client.print(bodyStart);

    // Send the status part
    client.print(statusPart);

    // Finish the request
    client.print(bodyEnd);

    // Wait for server response
    while (client.connected() && !client.available()) delay(1);
    while (client.available()) {
      String line = client.readStringUntil('\n');
      Serial.println(line);
    }

    client.stop();
  }
}