#include <ESP32Servo360.h>
#include <Adafruit_NeoPixel.h>

// Pin and pixel configuration
#define PIN        33       // Pin where the NeoPixel is connected
#define NUMPIXELS  8        // Number of NeoPixels (forming a circle)
#define DELAYVAL   60       // Delay between updates, in milliseconds
#define ERROR_DELAY 1000    // Duration to show orange light on error (in milliseconds)

ESP32Servo360 servo1, servo2;
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

String incomingData;
float pos1; // horizontal rotation
float pos2; // vertical rotation

unsigned long previousMillis = 0; // Stores the last time the pixels were updated
int currentPixel = 0;             // Current leading pixel index

uint8_t currentR = 0, currentG = 255, currentB = 0; // Default green color

void setup() {
  Serial.begin(9600);

  servo1.attach(27, 14); // Control pin (white), signal pin (yellow).
  servo2.attach(25, 26);

  servo1.setSpeed(500);
  servo2.setSpeed(500);

  pixels.begin();                 // Initialize the NeoPixel strip
  pixels.clear();                 // Clear all pixels to start with
  pixels.show();                  // Make sure the strip is off initially
  
  rotateServo(15, 15);

  Serial.println("Setup complete!");
}

void loop() {
  // Continuously run the chase lights animation
  chaseLightsWithFade(currentR, currentG, currentB, DELAYVAL);

  // Check for incoming data to update servos or lights
  if (Serial.available() > 0) {
    incomingData = Serial.readStringUntil('\n');

    Serial.print("Incoming data: ");
    Serial.println(incomingData);

    incomingData.trim();  // Remove leading and trailing whitespaces

    int commaIndex = incomingData.indexOf(',');

    if (commaIndex != -1) {
      String pos1_str = incomingData.substring(0, commaIndex);
      String pos2_str = incomingData.substring(commaIndex + 1);

      pos1 = atof(pos1_str.c_str());
      pos2 = atof(pos2_str.c_str());

      //pos1 = (pos1 <= 350) ? pos1 : 0;
      //pos2 = (pos2 <= 350) ? pos2 : 0;

      // Rotate servos and update lights
      rotateServo(pos1, pos2);
      Serial.print("Position ");
      Serial.print(pos1_str);
      Serial.print(" and ");
      Serial.print(pos2_str);
      Serial.println(" reached!");

    } else {
      // Handle faulty input
      setChaseLightsColor(255, 150, 0); // Orange light
      Serial.println("Faulty input!");

      // Keep the lights orange for 0.5 seconds
      unsigned long startTime = millis();
      while (millis() - startTime < ERROR_DELAY) {
        chaseLightsWithFade(255, 150, 0, DELAYVAL); // Update the lights to orange
        // Optionally include other tasks here if needed
      }

      // Revert to green light
      setChaseLightsColor(0, 255, 0); // Green light
    }
  }
}

// Function to rotate servos
void rotateServo(int angle1, int angle2) {
  // Set the LEDs to red while the servos are rotating
  setChaseLightsColor(255, 0, 0); // Red light

  // Ensure angles are in the range 0-360
  angle1 = normalizeAngle(angle1);
  angle2 = normalizeAngle(angle2);

  // Get current servo angles
  int currentAngle1 = normalizeAngle(servo1.getOrientation());
  int currentAngle2 = normalizeAngle(servo2.getOrientation());

  // Calculate the shortest paths for both servos
  int path1 = shortestPath(currentAngle1, angle1);
  int path2 = shortestPath(currentAngle2, angle2);

  // Set target positions with the shortest path
  servo1.rotateTo(currentAngle1 + path1);
  servo2.rotateTo(currentAngle2 + path2);

  // Define a deadband tolerance around the target position
  const float DEAD_BAND = 2.0; // Adjust this value as needed (in degrees)

  bool servo1Moving = true;
  bool servo2Moving = true;

  while (servo1Moving || servo2Moving) {
    // Update the LED animation
    chaseLightsWithFade(currentR, currentG, currentB, DELAYVAL);

    // Check if servo1 has reached its target position within the deadband
    if (abs(normalizeAngle(servo1.getOrientation()) - angle1) <= DEAD_BAND) {
      servo1Moving = false;
    }

    // Check if servo2 has reached its target position within the deadband
    if (abs(normalizeAngle(servo2.getOrientation()) - angle2) <= DEAD_BAND) {
      servo2Moving = false;
    }

    // Optional: yield to prevent blocking (especially for ESP32)
    yield(); 
  }

  // Once servos have stopped, switch the LEDs to green
  setChaseLightsColor(0, 255, 0); // Green light
}

// Normalize the angle to the 0-360 range
int normalizeAngle(int angle) {
  angle = angle % 360;
  if (angle < 0) angle += 360;
  return angle;
}

// Calculate the shortest path between two angles
int shortestPath(int current, int target) {
  int diff = (target - current) % 360;
  if (diff > 180) {
    diff -= 360;
  }
  return diff;
}



// Function to update the chase light color
void setChaseLightsColor(uint8_t R, uint8_t G, uint8_t B) {
  currentR = R;
  currentG = G;
  currentB = B;
}

// Chase lights with fade effect
void chaseLightsWithFade(uint8_t R, uint8_t G, uint8_t B, int delayTime) {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= delayTime) {
    previousMillis = currentMillis; // Save the last time the pixels were updated

    pixels.clear(); // Turn off all pixels

    pixels.setPixelColor(currentPixel, pixels.Color(R, G, B));

    for (int j = 1; j <= 4; j++) {
      int fadePixel = (currentPixel - j + NUMPIXELS) % NUMPIXELS; // Wrap around
      uint8_t r = reduceBrightness(R, j);
      uint8_t g = reduceBrightness(G, j);
      uint8_t b = reduceBrightness(B, j);
      pixels.setPixelColor(fadePixel, pixels.Color(r, g, b));
    }

    pixels.show(); // Update the pixels to the hardware

    currentPixel++;
    if (currentPixel >= NUMPIXELS) {
      currentPixel = 0; // Wrap around if we've reached the last pixel
    }
  }
}

uint8_t reduceBrightness(uint8_t in_color, int in_j) {
  int reducedColor = in_color - in_j * 50; // Adjust this multiplier for smoother fading
  if (reducedColor < 0) {
    reducedColor = 0; // Ensure the color value doesn't go below 0
  }
  return (uint8_t)reducedColor;
}
