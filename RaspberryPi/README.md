# Raspberry Pi Galvo Controller

Python implementations for controlling Pangolin Laser Systems galvanometers using XY2-100 and FB4 laser industry standards using Raspberry Pi GPIO.

## Overview

This repository contains two Python scripts that demonstrate how to control galvo systems using Raspberry Pi GPIO:

- **xy200_18_bits_python.py** - For XY2-100 compatible systems (18-bit resolution, separate X/Y data lines)
- **fb4_galvo.py** - For FB4 compatible systems (16-bit resolution, combined X/Y data on single line)

Both scripts generate various waveforms (sine, square, triangle, sawtooth) with independent frequency and amplitude control for X and Y channels.

## Requirements

### Hardware
- Raspberry Pi (Tested on Raspberry Pi 5, compatible with Pi 3/4)
- Cambridge Technology XY2-100 or FB4 compatible galvo system
- Basic wiring: 3-4 GPIO pins to galvo controller

### Software
- Raspberry Pi OS (Bullseye or newer)
- Python 3.7+
- Required libraries:
  ```bash
  sudo apt update
  sudo apt install python3-gpiozero
  ```
  
### Installation
Clone this repository:

```bash
git clone <https://github.com/SCANNERMAX/MACH-DSP-SDK.git>
cd RaspberryPi_Galvo
```
Ensure required libraries are installed (see Requirements above)

### Pin Configuration
XY2-100 Configuration (xy200_18_bits_python.py)

- FS_PIN: GPIO17 (Physical Pin 11) - Frame Sync
- SCLK_PIN: GPIO27 (Physical Pin 13) - Serial Clock
- XDATA_PIN: GPIO22 (Physical Pin 15) - X Data
- YDATA_PIN: GPIO23 (Physical Pin 16) - Y Data

FB4 Configuration (fb4_galvo.py)
- FS_PIN: GPIO17 (Physical Pin 11) - Frame Sync
- SCLK_PIN: GPIO27 (Physical Pin 13) - Serial Clock
- XYDATA_PIN: GPIO22 (Physical Pin 15) - Combined X/Y Data

### Usage
Running the Scripts
XY2-100 System:

```bash
python3 xy200_18_bits_python.py
```
Press Ctrl+C to stop the script gracefully.

FB4 System:
```bash
python3 fb4_galvo.py
```
Press Ctrl+C to stop the script gracefully.

### Configuration
Modify these constants at the top of each script to customize behavior:

# Channel Settings
```python
DATA_AMPLITUDE_X = 41071    # X channel waveform amplitude
DATA_AMPLITUDE_Y = 41071    # Y channel waveform amplitude
FREQ_X = 20                 # X channel frequency (Hz)
FREQ_Y = 20                 # Y channel frequency (Hz)
SAMPLE_RATE = 2000          # Samples per second

# Waveform Selection
X_WAVEFORM = WaveformType.WAVE_TRIANGLE
Y_WAVEFORM = WaveformType.WAVE_SQUARE

# Available Waveforms
'''
WAVE_SINE - Sine wave
WAVE_SQUARE - Square wave
WAVE_TRIANGLE - Triangle wave
WAVE_RISING_SAW - Rising sawtooth
WAVE_FALLING_SAW - Falling sawtooth
WAVE_DC - Constant output
WAVE_NONE - No output
'''
```
# Protocol Details
XY2-100 Protocol
18-bit resolution per channel
Separate data lines for X and Y
1 control bit + 18 data bits 
Data midpoint: 131072 (2^17)

FB4 Protocol
16-bit resolution per channel
Combined X and Y data on single line
32-bit packets (16-bit X + 16-bit Y)
Data midpoint: 32768 (2^15)
Special frame sync timing (first bit with FS low)

# Performance Notes
- The scripts are optimized for Raspberry Pi 5 but work on other models.
- For best performance, consider running without desktop environment. System load may affect timing precision - optimize Raspberry Pi resources if critical.
- Actual achieved frequencies may vary slightly from commanded values due to timing overhead.

# Troubleshooting

GPIO Busy Errors:
- Some GPIO pins may be used by system functions
- Check available pins with: gpioinfo
- Modify pin assignments in script if needed

Timing Issues:
- Reduce sample rate if timing is inconsistent
- Close other applications to free system resources

Safety Notes
- Always verify galvo system compatibility before connecting
- Start with low amplitudes to prevent damage
- Ensure proper grounding and electrical isolation
- Monitor galvo temperature during extended operation

