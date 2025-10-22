#!/usr/bin/env python3
from gpiozero import DigitalOutputDevice
import time
import math
from enum import Enum

# Pin Definitions (using BCM numbering)
FS_PIN = 17      # Frame Sync (GPIO17) - Physical Pin 11
SCLK_PIN = 27    # Serial Clock (GPIO27) - Physical Pin 13
XYDATA_PIN = 22  # Combined X and Y Data (GPIO22) - Physical Pin 15

# Protocol Constants
PACKET_LENGTH = 31     # 32 bits per frame (16-bit X + 16-bit Y)
DATA_MIDPOINT = 32768  # Center value for 16-bit data (2^15)

# INDEPENDENT CHANNEL SETTINGS
DATA_AMPLITUDE_X = 16384  # X channel amplitude (50% of 32768)
DATA_AMPLITUDE_Y = 16384  # Y channel amplitude (50% of 32768)
FREQ_X = 20               # X channel frequency (Hz)
FREQ_Y = 20               # Y channel frequency (Hz)

# WAVEFORM CONSTANTS
SAMPLE_RATE = 2000       # Samples per second
SAMPLE_DELAY_US = 1000000 / SAMPLE_RATE  # 200 us period

# Independent points per cycle for each channel
POINTS_PER_CYCLE_X = int(SAMPLE_RATE / FREQ_X)
POINTS_PER_CYCLE_Y = int(SAMPLE_RATE / FREQ_Y)

# WAVEFORM SELECTION ENUMS
class WaveformType(Enum):
    WAVE_SINE = 0
    WAVE_SQUARE = 1
    WAVE_TRIANGLE = 2
    WAVE_RISING_SAW = 3
    WAVE_FALLING_SAW = 4
    WAVE_DC = 5
    WAVE_NONE = 6

# CONFIGURATION - Set your desired waveforms here
X_WAVEFORM = WaveformType.WAVE_TRIANGLE
Y_WAVEFORM = WaveformType.WAVE_SQUARE

class FB4GalvoController:
    def __init__(self):
        self.x_sine_table = []
        self.x_square_table = []
        self.x_triangle_table = []
        self.x_rising_saw_table = []
        self.x_falling_saw_table = []
        
        self.y_sine_table = []
        self.y_square_table = []
        self.y_triangle_table = []
        self.y_rising_saw_table = []
        self.y_falling_saw_table = []
        
        self.x_waveform_getter = None
        self.y_waveform_getter = None
        
        self.x_current_index = 0
        self.y_current_index = 0
        self.last_sample_time = 0
        self.frame_count = 0
        self.start_time = 0
        
        print("Initializing GPIO with pins:")
        print(f"FS_PIN: GPIO{FS_PIN} (Physical Pin 11)")
        print(f"SCLK_PIN: GPIO{SCLK_PIN} (Physical Pin 13)")
        print(f"XYDATA_PIN: GPIO{XYDATA_PIN} (Physical Pin 15)")
        
        # Initialize GPIO devices
        try:
            self.fs_pin = DigitalOutputDevice(FS_PIN, initial_value=True)  # Start HIGH for FB4
            self.sclk_pin = DigitalOutputDevice(SCLK_PIN, initial_value=False)
            self.xydata_pin = DigitalOutputDevice(XYDATA_PIN, initial_value=False)
            print("GPIO initialized successfully!")
        except Exception as e:
            print(f"GPIO initialization failed: {e}")
            print("Please check your wiring and try different GPIO pins")
            exit(1)
        
        self.precompute_waveforms()
        self.setup_waveform_getters()
        
    def precompute_waveforms(self):
        """Precompute all waveform tables for X and Y channels"""
        # Precompute X channel waveforms
        self.x_sine_table = [0] * POINTS_PER_CYCLE_X
        self.x_square_table = [0] * POINTS_PER_CYCLE_X
        self.x_triangle_table = [0] * POINTS_PER_CYCLE_X
        self.x_rising_saw_table = [0] * POINTS_PER_CYCLE_X
        self.x_falling_saw_table = [0] * POINTS_PER_CYCLE_X
        
        for i in range(POINTS_PER_CYCLE_X):
            # X Sine wave
            angle = 2.0 * math.pi * i / POINTS_PER_CYCLE_X
            self.x_sine_table[i] = int(DATA_MIDPOINT + (math.sin(angle) * DATA_AMPLITUDE_X))
            
            # X Square wave
            self.x_square_table[i] = DATA_MIDPOINT + DATA_AMPLITUDE_X if i < POINTS_PER_CYCLE_X / 2 else DATA_MIDPOINT - DATA_AMPLITUDE_X
            
            # X Triangle wave
            position = float(i) / POINTS_PER_CYCLE_X
            if position < 0.5:
                self.x_triangle_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_X * (4.0 * position - 1.0))
            else:
                self.x_triangle_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_X * (3.0 - 4.0 * position))
            
            # X Rising sawtooth
            self.x_rising_saw_table[i] = int(DATA_MIDPOINT - DATA_AMPLITUDE_X + (2 * DATA_AMPLITUDE_X * i / POINTS_PER_CYCLE_X))
            
            # X Falling sawtooth
            self.x_falling_saw_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_X - (2 * DATA_AMPLITUDE_X * i / POINTS_PER_CYCLE_X))
        
        # Precompute Y channel waveforms
        self.y_sine_table = [0] * POINTS_PER_CYCLE_Y
        self.y_square_table = [0] * POINTS_PER_CYCLE_Y
        self.y_triangle_table = [0] * POINTS_PER_CYCLE_Y
        self.y_rising_saw_table = [0] * POINTS_PER_CYCLE_Y
        self.y_falling_saw_table = [0] * POINTS_PER_CYCLE_Y
        
        for i in range(POINTS_PER_CYCLE_Y):
            # Y Sine wave
            angle = 2.0 * math.pi * i / POINTS_PER_CYCLE_Y
            self.y_sine_table[i] = int(DATA_MIDPOINT + (math.sin(angle) * DATA_AMPLITUDE_Y))
            
            # Y Square wave
            self.y_square_table[i] = DATA_MIDPOINT + DATA_AMPLITUDE_Y if i < POINTS_PER_CYCLE_Y / 2 else DATA_MIDPOINT - DATA_AMPLITUDE_Y
            
            # Y Triangle wave
            position = float(i) / POINTS_PER_CYCLE_Y
            if position < 0.5:
                self.y_triangle_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_Y * (4.0 * position - 1.0))
            else:
                self.y_triangle_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_Y * (3.0 - 4.0 * position))
            
            # Y Rising sawtooth
            self.y_rising_saw_table[i] = int(DATA_MIDPOINT - DATA_AMPLITUDE_Y + (2 * DATA_AMPLITUDE_Y * i / POINTS_PER_CYCLE_Y))
            
            # Y Falling sawtooth
            self.y_falling_saw_table[i] = int(DATA_MIDPOINT + DATA_AMPLITUDE_Y - (2 * DATA_AMPLITUDE_Y * i / POINTS_PER_CYCLE_Y))
        
        print("All waveform tables precomputed")
        print(f"X Points per cycle: {POINTS_PER_CYCLE_X}")
        print(f"Y Points per cycle: {POINTS_PER_CYCLE_Y}")
    
    def setup_waveform_getters(self):
        """Setup function pointers for waveform access"""
        # Set X waveform getter
        if X_WAVEFORM == WaveformType.WAVE_SINE:
            self.x_waveform_getter = self.get_x_sine_value
        elif X_WAVEFORM == WaveformType.WAVE_SQUARE:
            self.x_waveform_getter = self.get_x_square_value
        elif X_WAVEFORM == WaveformType.WAVE_TRIANGLE:
            self.x_waveform_getter = self.get_x_triangle_value
        elif X_WAVEFORM == WaveformType.WAVE_RISING_SAW:
            self.x_waveform_getter = self.get_x_rising_saw_value
        elif X_WAVEFORM == WaveformType.WAVE_FALLING_SAW:
            self.x_waveform_getter = self.get_x_falling_saw_value
        elif X_WAVEFORM == WaveformType.WAVE_DC:
            self.x_waveform_getter = self.get_x_dc_value
        else:  # WAVE_NONE or default
            self.x_waveform_getter = self.get_x_none_value
        
        # Set Y waveform getter
        if Y_WAVEFORM == WaveformType.WAVE_SINE:
            self.y_waveform_getter = self.get_y_sine_value
        elif Y_WAVEFORM == WaveformType.WAVE_SQUARE:
            self.y_waveform_getter = self.get_y_square_value
        elif Y_WAVEFORM == WaveformType.WAVE_TRIANGLE:
            self.y_waveform_getter = self.get_y_triangle_value
        elif Y_WAVEFORM == WaveformType.WAVE_RISING_SAW:
            self.y_waveform_getter = self.get_y_rising_saw_value
        elif Y_WAVEFORM == WaveformType.WAVE_FALLING_SAW:
            self.y_waveform_getter = self.get_y_falling_saw_value
        elif Y_WAVEFORM == WaveformType.WAVE_DC:
            self.y_waveform_getter = self.get_y_dc_value
        else:  # WAVE_NONE or default
            self.y_waveform_getter = self.get_y_none_value
    
    # Waveform getter functions for X channel
    def get_x_sine_value(self, index: int) -> int:
        return self.x_sine_table[index % POINTS_PER_CYCLE_X]
    
    def get_x_square_value(self, index: int) -> int:
        return self.x_square_table[index % POINTS_PER_CYCLE_X]
    
    def get_x_triangle_value(self, index: int) -> int:
        return self.x_triangle_table[index % POINTS_PER_CYCLE_X]
    
    def get_x_rising_saw_value(self, index: int) -> int:
        return self.x_rising_saw_table[index % POINTS_PER_CYCLE_X]
    
    def get_x_falling_saw_value(self, index: int) -> int:
        return self.x_falling_saw_table[index % POINTS_PER_CYCLE_X]
    
    def get_x_dc_value(self, index: int) -> int:
        return DATA_MIDPOINT
    
    def get_x_none_value(self, index: int) -> int:
        return 0
    
    # Waveform getter functions for Y channel
    def get_y_sine_value(self, index: int) -> int:
        return self.y_sine_table[index % POINTS_PER_CYCLE_Y]
    
    def get_y_square_value(self, index: int) -> int:
        return self.y_square_table[index % POINTS_PER_CYCLE_Y]
    
    def get_y_triangle_value(self, index: int) -> int:
        return self.y_triangle_table[index % POINTS_PER_CYCLE_Y]
    
    def get_y_rising_saw_value(self, index: int) -> int:
        return self.y_rising_saw_table[index % POINTS_PER_CYCLE_Y]
    
    def get_y_falling_saw_value(self, index: int) -> int:
        return self.y_falling_saw_table[index % POINTS_PER_CYCLE_Y]
    
    def get_y_dc_value(self, index: int) -> int:
        return DATA_MIDPOINT
    
    def get_y_none_value(self, index: int) -> int:
        return 0
    
    def send_fb4_frame_precise(self, xy_packet: int):
        """Send FB4 frame using precise timing - 32-bit data on single pin"""
        # 1. Start Frame: Bring FS LOW for first clock cycle only
        self.fs_pin.off()
        
        # Send first bit (X MSB - bit 31) with FS LOW
        self.xydata_pin.value = (xy_packet >> 31) & 0x01
        
        self.sclk_pin.on()
        
        self.sclk_pin.off()
        
        
        # 2. Bring FS HIGH after first clock cycle
        self.fs_pin.on()
        
        # 3. Send remaining 31 bits (bits 30 down to 0) with FS HIGH
        for i in range(30, -1, -1):
            self.xydata_pin.value = (xy_packet >> i) & 0x01
            
            
            self.sclk_pin.on()
            
            
            self.sclk_pin.off()
            
        
        # 4. Ensure all pins are in idle state
        self.fs_pin.on()
        self.sclk_pin.off()
        self.xydata_pin.off()
    
    def run(self):
        """Main execution loop with precise timing"""
        print("Configuration:")
        print(f"X Waveform: {X_WAVEFORM}")
        print(f"Y Waveform: {Y_WAVEFORM}")
        print(f"X Frequency: {FREQ_X} Hz (DESIRED)")
        print(f"Y Frequency: {FREQ_Y} Hz (DESIRED)")
        print(f"Sample Rate: {SAMPLE_RATE} Hz")
        print(f"Sample Period: {SAMPLE_DELAY_US:.1f} us")
        print(f"X Points per Cycle: {POINTS_PER_CYCLE_X}")
        print(f"Y Points per Cycle: {POINTS_PER_CYCLE_Y}")
        print(f"X Amplitude: {DATA_AMPLITUDE_X}")
        print(f"Y Amplitude: {DATA_AMPLITUDE_Y}")
        print(f"Data MIDPOINT: {DATA_MIDPOINT}")
        print("FB4 Mode: 32-bit data (16-bit X + 16-bit Y) on single pin")
        
        self.last_sample_time = time.perf_counter()
        self.start_time = time.perf_counter()
        self.frame_count = 0
        
        try:
            while True:
                current_time = time.perf_counter()
                elapsed_us = (current_time - self.last_sample_time) * 1e6
                
                if elapsed_us >= SAMPLE_DELAY_US:
                    # Calculate exact next sample time to maintain precise timing
                    self.last_sample_time += SAMPLE_DELAY_US / 1e6
                    
                    # Get the waveform values
                    x_data = self.x_waveform_getter(self.x_current_index)
                    y_data = self.y_waveform_getter(self.y_current_index)
                    
                    # Build the 32-bit packet for FB4 mode:
                    # Format: [X15] [X14] ... [X0] [Y15] [Y14] ... [Y0]
                    # X data in bits 31-16, Y data in bits 15-0
                    xy_packet = ((x_data & 0xFFFF) << 16) | (y_data & 0xFFFF)
                    
                    self.send_fb4_frame_precise(xy_packet)
                    
                    # Move to the next point for each channel independently
                    self.x_current_index = (self.x_current_index + 1) % POINTS_PER_CYCLE_X
                    self.y_current_index = (self.y_current_index + 1) % POINTS_PER_CYCLE_Y
                    
                    self.frame_count += 1
                    
                    # Print debug message every 100 points
                    #if self.x_current_index % 100 == 0:
                    #    print(f"X Index: {self.x_current_index} Y Index: {self.y_current_index}")
                    #    print(f"X Value: {x_data} Y Value: {y_data}")
                    #    print(f"XY Packet: 0x{xy_packet:08X}")
                        
        except KeyboardInterrupt:
            print("\nStopping FB4 galvo controller...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO resources"""
        self.fs_pin.close()
        self.sclk_pin.close()
        self.xydata_pin.close()
        print("GPIO cleaned up")

if __name__ == "__main__":
    controller = FB4GalvoController()
    controller.run()
