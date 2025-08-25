#include <Arduino.h>

// Pin Definitions
const int FS_PIN = 2;    // Frame Sync
const int SCLK_PIN = 9;  // Serial Clock (We control this manually)
const int XDATA_PIN = 8; // X Data (We control this manually)
const int YDATA_PIN = 7; // Y Data

// Protocol Constants
#define PACKET_LENGTH   19     // C2 control bit + 18 bits data
#define DATA_MIDPOINT   131072L // Center value for 18-bit data (2^17)

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// INDEPENDENT CHANNEL SETTINGS
#define DATA_AMPLITUDE_X  41071L  // X channel amplitude
#define DATA_AMPLITUDE_Y  41071L  // Y channel amplitude
#define FREQ_X           20       // X channel frequency (Hz)
#define FREQ_Y           20       // Y channel frequency (Hz)
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// WAVEFORM CONSTANTS
const int SAMPLE_RATE = 5000;    // Samples per second (Adjustable)
const int SAMPLE_DELAY_US = 1000000 / SAMPLE_RATE; // 500 us period

// Independent points per cycle for each channel
const int POINTS_PER_CYCLE_X = SAMPLE_RATE / FREQ_X;
const int POINTS_PER_CYCLE_Y = SAMPLE_RATE / FREQ_Y;

// WAVEFORM SELECTION ENUMS
enum WaveformType {
  WAVE_SINE = 0,
  WAVE_SQUARE = 1,
  WAVE_TRIANGLE = 2,
  WAVE_RISING_SAW = 3,
  WAVE_FALLING_SAW = 4,
  WAVE_DC = 5,
  WAVE_NONE = 6
};

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// CONFIGURATION - Set your desired waveforms here [WAVE_SINE , WAVE_SQUARE , WAVE_TRIANGLE , WAVE_RISING_SAW , WAVE_FALLING_SAW]
const WaveformType X_WAVEFORM = WAVE_TRIANGLE;
const WaveformType Y_WAVEFORM = WAVE_SQUARE;
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Global Variables - Separate tables for X and Y with their own sizes
uint32_t xSineTable[POINTS_PER_CYCLE_X];
int32_t xSquareTable[POINTS_PER_CYCLE_X];
int32_t xTriangleTable[POINTS_PER_CYCLE_X];
int32_t xRisingSawTable[POINTS_PER_CYCLE_X];
int32_t xFallingSawTable[POINTS_PER_CYCLE_X];

uint32_t ySineTable[POINTS_PER_CYCLE_Y];
int32_t ySquareTable[POINTS_PER_CYCLE_Y];
int32_t yTriangleTable[POINTS_PER_CYCLE_Y];
int32_t yRisingSawTable[POINTS_PER_CYCLE_Y];
int32_t yFallingSawTable[POINTS_PER_CYCLE_Y];

// Function pointer type for waveform access
typedef uint32_t (*WaveformGetter)(int index);

// Function pointers for X and Y channels
WaveformGetter xWaveformGetter = nullptr;
WaveformGetter yWaveformGetter = nullptr;

// Separate indices for X and Y channels
int xCurrentIndex = 0;
int yCurrentIndex = 0;
unsigned long lastSampleTime = 0;

// Waveform getter functions for X channel
uint32_t getXSineValue(int index) {
    return xSineTable[index % POINTS_PER_CYCLE_X];
}

uint32_t getXSquareValue(int index) {
    return xSquareTable[index % POINTS_PER_CYCLE_X];
}

uint32_t getXTriangleValue(int index) {
    return xTriangleTable[index % POINTS_PER_CYCLE_X];
}

uint32_t getXRisingSawValue(int index) {
    return xRisingSawTable[index % POINTS_PER_CYCLE_X];
}

uint32_t getXFallingSawValue(int index) {
    return xFallingSawTable[index % POINTS_PER_CYCLE_X];
}

uint32_t getXDCValue(int index) {
    return DATA_MIDPOINT;
}

uint32_t getXNoneValue(int index) {
    return 0;
}

// Waveform getter functions for Y channel
uint32_t getYSineValue(int index) {
    return ySineTable[index % POINTS_PER_CYCLE_Y];
}

uint32_t getYSquareValue(int index) {
    return ySquareTable[index % POINTS_PER_CYCLE_Y];
}

uint32_t getYTriangleValue(int index) {
    return yTriangleTable[index % POINTS_PER_CYCLE_Y];
}

uint32_t getYRisingSawValue(int index) {
    return yRisingSawTable[index % POINTS_PER_CYCLE_Y];
}

uint32_t getYFallingSawValue(int index) {
    return yFallingSawTable[index % POINTS_PER_CYCLE_Y];
}

uint32_t getYDCValue(int index) {
    return DATA_MIDPOINT;
}

uint32_t getYNoneValue(int index) {
    return 0;
}

void setupWaveformGetters() {
    // Set X waveform getter
    switch(X_WAVEFORM) {
        case WAVE_SINE: xWaveformGetter = getXSineValue; break;
        case WAVE_SQUARE: xWaveformGetter = getXSquareValue; break;
        case WAVE_TRIANGLE: xWaveformGetter = getXTriangleValue; break;
        case WAVE_RISING_SAW: xWaveformGetter = getXRisingSawValue; break;
        case WAVE_FALLING_SAW: xWaveformGetter = getXFallingSawValue; break;
        case WAVE_DC: xWaveformGetter = getXDCValue; break;
        case WAVE_NONE: xWaveformGetter = getXNoneValue; break;
        default: xWaveformGetter = getXNoneValue; break;
    }
    
    // Set Y waveform getter
    switch(Y_WAVEFORM) {
        case WAVE_SINE: yWaveformGetter = getYSineValue; break;
        case WAVE_SQUARE: yWaveformGetter = getYSquareValue; break;
        case WAVE_TRIANGLE: yWaveformGetter = getYTriangleValue; break;
        case WAVE_RISING_SAW: yWaveformGetter = getYRisingSawValue; break;
        case WAVE_FALLING_SAW: yWaveformGetter = getYFallingSawValue; break;
        case WAVE_DC: yWaveformGetter = getYDCValue; break;
        case WAVE_NONE: yWaveformGetter = getYNoneValue; break;
        default: yWaveformGetter = getYNoneValue; break;
    }
}

void precomputeWaveforms() {
    // Precompute X channel waveforms
    for (int i = 0; i < POINTS_PER_CYCLE_X; i++) {
        // X Sine wave
        float angle = 2.0 * PI * i / POINTS_PER_CYCLE_X;
        xSineTable[i] = DATA_MIDPOINT + (sin(angle) * DATA_AMPLITUDE_X);
        
        // X Square wave
        xSquareTable[i] = (i < POINTS_PER_CYCLE_X / 2) ? (DATA_MIDPOINT + DATA_AMPLITUDE_X) : (DATA_MIDPOINT - DATA_AMPLITUDE_X);
        
        // X Triangle wave
        float position = (float)i / POINTS_PER_CYCLE_X;
        if (position < 0.5) {
            xTriangleTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_X * (4.0 * position - 1.0);
        } else {
            xTriangleTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_X * (3.0 - 4.0 * position);
        }
        
        // X Rising sawtooth
        xRisingSawTable[i] = DATA_MIDPOINT - DATA_AMPLITUDE_X + (2 * DATA_AMPLITUDE_X * i / POINTS_PER_CYCLE_X);
        
        // X Falling sawtooth
        xFallingSawTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_X - (2 * DATA_AMPLITUDE_X * i / POINTS_PER_CYCLE_X);
    }
    
    // Precompute Y channel waveforms
    for (int i = 0; i < POINTS_PER_CYCLE_Y; i++) {
        // Y Sine wave
        float angle = 2.0 * PI * i / POINTS_PER_CYCLE_Y;
        ySineTable[i] = DATA_MIDPOINT + (sin(angle) * DATA_AMPLITUDE_Y);
        
        // Y Square wave
        ySquareTable[i] = (i < POINTS_PER_CYCLE_Y / 2) ? (DATA_MIDPOINT + DATA_AMPLITUDE_Y) : (DATA_MIDPOINT - DATA_AMPLITUDE_Y);
        
        // Y Triangle wave
        float position = (float)i / POINTS_PER_CYCLE_Y;
        if (position < 0.5) {
            yTriangleTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_Y * (4.0 * position - 1.0);
        } else {
            yTriangleTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_Y * (3.0 - 4.0 * position);
        }
        
        // Y Rising sawtooth
        yRisingSawTable[i] = DATA_MIDPOINT - DATA_AMPLITUDE_Y + (2 * DATA_AMPLITUDE_Y * i / POINTS_PER_CYCLE_Y);
        
        // Y Falling sawtooth
        yFallingSawTable[i] = DATA_MIDPOINT + DATA_AMPLITUDE_Y - (2 * DATA_AMPLITUDE_Y * i / POINTS_PER_CYCLE_Y);
    }
    
    Serial.println("All waveform tables precomputed");
}

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

    // Precompute all waveforms
    precomputeWaveforms();
    
    // Setup waveform getters
    setupWaveformGetters();

    // Print configuration
    Serial.println("Configuration:");
    Serial.print("X Waveform: "); Serial.println(X_WAVEFORM);
    Serial.print("Y Waveform: "); Serial.println(Y_WAVEFORM);
    Serial.print("X Frequency: "); Serial.print(FREQ_X); Serial.println(" Hz");
    Serial.print("Y Frequency: "); Serial.print(FREQ_Y); Serial.println(" Hz");
    Serial.print("X Points per Cycle: "); Serial.println(POINTS_PER_CYCLE_X);
    Serial.print("Y Points per Cycle: "); Serial.println(POINTS_PER_CYCLE_Y);
    Serial.print("X Amplitude: "); Serial.println(DATA_AMPLITUDE_X);
    Serial.print("Y Amplitude: "); Serial.println(DATA_AMPLITUDE_Y);
    Serial.print("Sample Rate: "); Serial.print(SAMPLE_RATE); Serial.println(" Hz");

    lastSampleTime = micros();
}

void loop() {
    // Precise timing loop
    unsigned long currentTime = micros();
    if (currentTime - lastSampleTime >= SAMPLE_DELAY_US) {
        lastSampleTime += SAMPLE_DELAY_US; // Schedule the next sample precisely

        // Get the waveform values by directly indexing precomputed tables
        uint32_t xData = xWaveformGetter(xCurrentIndex);
        uint32_t yData = yWaveformGetter(yCurrentIndex);

        // Build the packet for 18-bit mode:
        uint32_t xPacket = (1UL << 19) | ((xData & 0x3FFFF) << 1);
        uint32_t yPacket = (1UL << 19) | ((yData & 0x3FFFF) << 1);

        sendXYFramePrecise(xPacket, yPacket);

        // Move to the next point for each channel independently
        xCurrentIndex = (xCurrentIndex + 1) % POINTS_PER_CYCLE_X;
        yCurrentIndex = (yCurrentIndex + 1) % POINTS_PER_CYCLE_Y;

        // Print a debug message every 100 points
        if (xCurrentIndex % 100 == 0) {
            Serial.print("X Index: "); Serial.print(xCurrentIndex);
            Serial.print(" Y Index: "); Serial.print(yCurrentIndex);
            Serial.print(" X Value: "); Serial.print(xData);
            Serial.print(" Y Value: "); Serial.println(yData);
        }
    }
}

void sendXYFramePrecise(uint32_t xPacket, uint32_t yPacket) {
    // 1. Start Frame: Bring FS HIGH
    digitalWrite(FS_PIN, HIGH);

    // 2. Send all 20 bits, MSB first (bit 19 down to bit 0)
    for (int8_t i = (PACKET_LENGTH); i >= 0; i--) {
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