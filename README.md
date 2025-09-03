# Pangolin Control System SDK

![Pangolin Logo](scanner_max.png)

This repository provides specialized libraries and templates for Pangolin Mach-DSP and galvanometer control. The Python and LabVIEW libraries offer comprehensive functionality, including analog input waveform generation and serial communication for system control and health monitoring. For embedded projects, the Arduino library implements the core XY2-100 and FB4 communication protocols.
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
  - cycloids waveform generation
  - National Instruments DAQ hardware integration
  - LabJack hardware integration

- **Serial Comunication**:
  - VISA serial communication interface
  - Servo status monitoring
  - Power supply voltage reading
  - Tuning number configuration
  - Function generator control
    
### Arduino
  - XY2-100 comunication protocol
  - FB4 comunication protocol
    
## System Requirements

### Hardware
- National Instruments DAQ device (e.g., NI USB-6003, NI USB-6211) - (analog input)
- Mach-DSP controller
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
