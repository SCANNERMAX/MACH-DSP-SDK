# Pangolin Control System SDK

![Pangolin Logo](scanner_max.png)

This repository contains SDKs for controlling and interfacing with the Pangolin Match-DSP system through both LabVIEW and Python implementations. The SDKs support analog waveform generation and serial communication for comprehensive control of the DSP system.

## Features

### Python SDK
- **Analog Input Waveform Generation**:
  - Standard, cycloid, and custom waveform generation
  - Real-time waveform visualization
  - NI-DAQmx hardware integration

- **Serial**:
  - PySerial interface for Match-DSP
  - Servo status monitoring
  - Power supply voltage reading
  - Tuning number and function generator control

### LabVIEW SDK
- **Analog Input Waveform Generation**:
  - Standard waveform generation (sine, square, triangle, sawtooth)
  - Custom waveform generation from text files inputs
  - National Instruments DAQ hardware integration

- **Serial Comunication**:
  - VISA serial communication interface
  - Servo status monitoring
  - Power supply voltage reading
  - Tuning number configuration
  - Function generator control

## System Requirements

### Hardware
- National Instruments DAQ device (e.g., NI USB-6003, NI USB-6211) - (analog input)
- Match-DSP controller
- USB-to-serial adapter (serial communication)

### Software
#### LabVIEW Programs:
- LabVIEW 2018 or later
- NI-DAQmx driver software
- NI-VISA drivers (for serial communication)

#### Python Programs:
- Python 3.7 or later
- Required packages:
  ```bash
  pip install pyqt5 numpy scipy matplotlib nidaqmx pyserial
