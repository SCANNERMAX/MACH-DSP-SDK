#include <Arduino.h>

// Pin Definitions
const int FS_PIN = 2;    // Frame Sync
const int SCLK_PIN = 9;  // Serial Clock (We control this manually)
const int XDATA_PIN = 8; // X Data (We control this manually)
const int YDATA_PIN = 7; // Y Data

// Protocol Constants
#define PACKET_LENGTH   20     // 20 bits per frame
#define DATA_MIDPOINT   131072L // Center value for 18-bit data (2^17)
#define DATA_AMPLITUDE  41071L // Maximum safe amplitude

// WAVEFORM CONSTANTS
const int SAMPLE_RATE = 2000;    // Samples per second (Adjustable)
const int SAMPLE_DELAY_US = 1000000 / SAMPLE_RATE; // 500 us period
const int SINE_FREQ = 10;        // Hz
const int POINTS_PER_CYCLE = SAMPLE_RATE / SINE_FREQ; // 200 points

// Global Variables
uint32_t sineTable[POINTS_PER_CYCLE];
int currentIndex = 0;
unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);

  // Configure all pins as manual outputs
  pinMode(FS_PIN, OUTPUT);
  digitalWrite(FS_PIN, LOW);
  
  pinMode(SCLK_PIN, OUTPUT);
  digitalWrite(SCLK_PIN, LOW);
  
  pinMode(XDATA_PIN, OUTPUT);
  digitalWrite(XDATA_PIN, LOW);
  
  pinMode(YDATA_PIN, OUTPUT);
  digitalWrite(YDATA_PIN, LOW);

  // Precompute the sine wave table for X axis
  for (int i = 0; i < POINTS_PER_CYCLE; i++) {
    float angle = 2.0 * PI * i / POINTS_PER_CYCLE;
    int32_t sineValue = DATA_MIDPOINT + (sin(angle) * DATA_AMPLITUDE);
    sineTable[i] = sineValue; // Data is already constrained by calculation
  }

  lastSampleTime = micros();
  Serial.println("Sine wave generator started.");
  Serial.print("Sample Rate: "); Serial.print(SAMPLE_RATE); Serial.println(" Hz");
  Serial.print("Points per Cycle: "); Serial.println(POINTS_PER_CYCLE);
}

void loop() {
  // Precise timing loop
  unsigned long currentTime = micros();
  if (currentTime - lastSampleTime >= SAMPLE_DELAY_US) {
    lastSampleTime += SAMPLE_DELAY_US; // Schedule the next sample precisely

    // Get the next data point
    uint32_t xData = sineTable[currentIndex];
    uint32_t yData = sineTable[currentIndex]; // Keep Y stationary for now

    // Build the packet for 18-bit mode:
    // Format: [C2=1] [D17] [D16] ... [D0] [Unused]
    // Achieved by shifting data left by 1 bit and setting bit 19
    uint32_t xPacket = (1UL << 19) | ((xData & 0x3FFFF) << 1);
    uint32_t yPacket = (1UL << 19) | ((yData & 0x3FFFF) << 1);

    sendXYFramePrecise(xPacket, yPacket);

    // Move to the next point
    currentIndex = (currentIndex + 1) % POINTS_PER_CYCLE;

    // Print a debug message every 100 points
    if (currentIndex % 100 == 0) {
      Serial.print("Index: "); Serial.println(currentIndex);
    }
  }
  // The loop runs as fast as possible, checking the time
}

void sendXYFramePrecise(uint32_t xPacket, uint32_t yPacket) {
  // 1. Start Frame: Bring FS HIGH
  digitalWrite(FS_PIN, HIGH);

  // 2. Send all 20 bits, MSB first (bit 19 down to bit 0)
  for (int8_t i = (PACKET_LENGTH - 1); i >= 0; i--) {
    // 2a. Set the data pins BEFORE the clock rises
    uint8_t yBit = (yPacket >> i) & 0x01;
    digitalWrite(YDATA_PIN, yBit);
    
    uint8_t xBit = (xPacket >> i) & 0x01;
    digitalWrite(XDATA_PIN, xBit);

    // 2b. Short delay for signal stability (setup time)
    delayMicroseconds(1);

    // 2c. Generate Clock Rising Edge
    digitalWrite(SCLK_PIN, HIGH);
    delayMicroseconds(1); // Clock high pulse width

    // 2d. Generate Clock Falling Edge (DSP latches data here)
    digitalWrite(SCLK_PIN, LOW);
    delayMicroseconds(1); // Clock low time

    // 2e. End Frame after the 19th bit (before the 20th bit is sent)
    if (i == 1) {
      digitalWrite(FS_PIN, LOW);
    }
  }
  
  // 3. Ensure all pins are in idle state
  digitalWrite(FS_PIN, LOW);
  digitalWrite(SCLK_PIN, LOW);
}