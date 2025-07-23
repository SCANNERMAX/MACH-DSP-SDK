import math
import numpy as np
import matplotlib.pyplot as plt

class cycloid_func_generator():
    def __init__(self, A, T, TrampCV, TrackingDelay, sample_rate, num_points=1000, num_cycles=1):
        """
        Generate multiple cycles of a triangle waveform with rounded edges (sine transitions).
    
        Parameters:
        A: Amplitude (peak-to-peak) of the waveform in degrees
        T: Total time period for one complete cycle in seconds
        TrampCV: Time for the constant velocity (linear ramp) portion in seconds
        TrackingDelay: Delay between input command and output position in seconds
        num_points: Number of points per cycle
        num_cycles: Number of complete cycles to generate
        
        Returns:
        Tuple of (time_array, command_signal_array)
        """
        # integrator attributes
        self.A = A
        self.T = T
        self.TrampCV = TrampCV
        self.TrackingDelay = TrackingDelay
        self.num_points = num_points
        self.num_cycles = num_cycles
        self.TwoPi = 2 * math.pi
        self.sample_rate = sample_rate

    def get_triangle_cycliod(self):
        
    
        # Calculate derived parameters for one cycle
        A0 = -self.A / 2  # Starting position of ramp portion
        A1 = self.A / 2   # Ending position of ramp portion
        Ts = 2 * self.TrackingDelay  # Settling time
        
        # Time for each transition (half of remaining time after ramps and settling)
        Trs = (self.T / 2) - self.TrampCV - Ts
        
        # Slope of the ramp portion (degrees per second)
        W = self.A / self.TrampCV
        
        # Frequency of the sine transition portion
        f_rise = 1 / (2 * Trs) if Trs > 0 else 0
        
        # Amplitude of the sine transition portion
        A2 = W / (self.TwoPi * f_rise) if f_rise > 0 else 0
        
        # Position error is slope of the command multiplied by tracking delay time
        PositionError = W * self.TrackingDelay
        
        # Adjust start and end positions by position error
        A1OffsetByPositionError = A1 + PositionError
        A0OffsetByPositionError = A0 - PositionError
        
        # Time for one complete cycle (rise + transition + fall + transition)
        TotalTimeForOneCycle = self.TrampCV + Ts + Trs + self.TrampCV + Ts + Trs
        #print('triangle time')
        #print(TotalTimeForOneCycle)
        # Initialize arrays for all cycles
        #total_points = self.num_points * self.num_cycles
        total_points = int(self.sample_rate * TotalTimeForOneCycle * self.num_cycles)
        time_array = np.linspace(0, TotalTimeForOneCycle * self.num_cycles, total_points)
        command_signal = np.zeros(total_points)
        
        for i, t in enumerate(time_array):
            # Get time within current cycle
            cycle_time = t % TotalTimeForOneCycle
            
            if cycle_time <= (self.TrampCV + Ts):
                # Rising ramp portion
                command_signal[i] = A0OffsetByPositionError + (W * cycle_time)
                
            elif cycle_time <= (self.TrampCV + Ts + Trs):
                # Rising transition (sine portion)
                if Trs > 0:
                    transition_time = cycle_time - (self.TrampCV + Ts)
                    command_signal[i] = A1OffsetByPositionError + (A2 * math.sin(self.TwoPi * f_rise * transition_time))
                
            elif cycle_time <= (self.TrampCV + Ts + Trs + self.TrampCV + Ts):
                # Falling ramp portion
                ramp_time = cycle_time - (self.TrampCV + Ts + Trs)
                command_signal[i] = A1OffsetByPositionError - (W * ramp_time)
                
            else:
                # Falling transition (sine portion)
                if Trs > 0:
                    transition_time = cycle_time - (self.TrampCV + Ts + Trs + self.TrampCV + Ts)
                    command_signal[i] = A0OffsetByPositionError - (A2 * math.sin(self.TwoPi * f_rise * transition_time))
        data_out = [Trs, f_rise]
        return time_array[:-1], command_signal[:-1],data_out
    
    def get_sawtooth_cycliod(self):
        """
        Generate multiple cycles of a sawtooth waveform with rounded edges (cycloid retrace).
        
        Parameters:
            A: Amplitude (peak-to-peak) of the waveform in degrees
            T: Total time period for one complete cycle in seconds
            TrampCV: Time for the constant velocity (linear ramp) portion in seconds
            TrackingDelay: Delay between input command and output position in seconds
            num_points: Number of points per cycle
            num_cycles: Number of complete cycles to generate
            
        Returns:
            Tuple of (time_array, command_signal_array)
        """
        # Constants
        
        # Calculate derived parameters for one cycle
        A0 = -self.A / 2                        # Starting position of ramp portion
        A1 = self.A / 2                         # Ending position of ramp portion
        Ts = 2 * self.TrackingDelay             # Settling time
        Tf = self.T - self.TrampCV - Ts              # Flyback time
        W = self.A / self.TrampCV                    # Slope of the ramp portion
        A2 = -(self.A + W * (Tf + Ts))          # Flyback amplitude
        W2 = self.TwoPi / Tf                    # Flyback frequency
        PositionError = W * self.TrackingDelay  # Position error
        A1OffsetByPositionError = A1 + PositionError
        A0OffsetByPositionError = A0 - PositionError
        TotalTimeForOneCycle = self.TrampCV + Ts + Tf
        #print('sawtooth time')
        #print(TotalTimeForOneCycle)
        # Initialize arrays for all cycles
        #total_points = self.num_points * self.num_cycles
        total_points = int(self.sample_rate * TotalTimeForOneCycle * self.num_cycles)
        time_array = np.linspace(0, TotalTimeForOneCycle * self.num_cycles, total_points)
        command_signal = np.zeros(total_points)
        
        for i, t in enumerate(time_array):
            # Get time within current cycle
            cycle_time = t % TotalTimeForOneCycle
            
            if cycle_time <= (self.TrampCV + Ts):
                # Linear ramp portion
                command_signal[i] = (W * cycle_time) + A0OffsetByPositionError
            else:
                # Flyback (cycloid retrace) portion
                InstantaneousFlybackTime = cycle_time - (self.TrampCV + Ts)
                
                # Cycloid retrace formula
                command_signal[i] = (A2 / self.TwoPi) * (
                    (W2 * InstantaneousFlybackTime) - 
                    math.sin(W2 * InstantaneousFlybackTime)
                ) + (W * InstantaneousFlybackTime) + A1OffsetByPositionError
        
        data_out = [Tf, 1/Tf]
        return time_array[:-1], command_signal[:-1], data_out
