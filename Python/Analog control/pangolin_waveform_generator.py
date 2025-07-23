import sys
import os
from front_panel import Ui_MainWindow
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5.QtCore import QThread, Qt
import threading
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt5.QtCore import QStandardPaths, QDir
from cycloid_generator import cycloid_func_generator
# this set up matplotlib so we can embeded plot inside widget from qt builder
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
from scipy.signal import sawtooth, square

# National Instrument library
import nidaqmx
from nidaqmx.constants import AcquisitionType

class Pangolin_waveform_generator(qtw.QMainWindow):
    def __init__(self, * args, **kwargs):
        super().__init__(*args,**kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.update_graph('setup')
        self.X_axis_data = np.zeros((0, 2))
        self.Y_axis_data = np.zeros((0, 2))
        self.X_axis_parameters = None
        self.Y_axis_parameters = None
        self.X_axis_cycloid_parameters = None
        self.Y_axis_cycloid_parameters = None
        self.axis_selected= None
        self.waveform_selected = None
        self.cycloid_waveform_selected = None
        self.duration = self.ui.duration_doubleSpinBox
        self.sampling_rate = self.ui.sample_rate_spinBox
        self.number_of_points = self.ui.number_points_spinBox
        self.duration = self.ui.duration_doubleSpinBox
        self.amplitude =  self.ui.voltage_doubleSpinBox
        self.waveform_frequency  = self.ui.waveform_frequency_doubleSpinBox
        self.scale_factor = None
        self.width = self.ui.width_doubleSpinBox
        self.waveform_time = ([])
        self.sine_waveform_data = ([])
        self.square_waveform_data = ([])
        self.triangle_waveform_data = ([])
        self.sawtooth_waveform_data = ([])
        self.text_file_Waveform = ([])
        self.A = self.ui.doubleSpinBox_4
        self.T = self.ui.doubleSpinBox
        self.TrampCV = self.ui.doubleSpinBox_2
        self.TrackingDelay = self.ui.doubleSpinBox_3
        self.num_points = self.ui.spinBox_2
        self.sample_rate_cycloid = self.ui.sample_rate_spinBox

        self.ui.width_doubleSpinBox.setEnabled(False) # disable width from sawtooth when not selected
        self.ui.standard_waveform_comboBox.currentTextChanged.connect(self.update_sawtooth_width_state)
        self.ui.path_to_file_pushButton.clicked.connect(self.browse_for_txt_file)
        self.ui.duration_doubleSpinBox.setEnabled(False) # disable width from sawtooth when not selected
        self.ui.spinBox_2.setValue(int(self.T.value() * self.sampling_rate.value()))
        self.ui.spinBox_2.setEnabled(False)

        # Get the desktop path
        desktop_path = self.get_desktop_path()
        # Set the path to your QLineEdit
        self.ui.path_to_file_lineEdit.setText(desktop_path)
        self.ui.path_to_file_lineEdit.setEnabled(False) # disable line edit when text file input is  not selected

        self.cycloid_func = cycloid_func_generator(self.A.value(), self.T.value(), self.TrampCV.value(), 
                                                 self.TrackingDelay.value(), self.sampling_rate.value() ,self.num_points.value(), num_cycles=1)
        # send to axis
        self.ui.send_to_axis_standard.clicked.connect(self.send_to_axis_standar_waveform)
        # Set up the colored combo box
        self.setup_colored_combobox()
        # Connect the combo box signal
        self.ui.axis_comboBox.currentIndexChanged.connect(self.on_axis_changed)

        # send to axis cycloid
        self.ui.send_to_axis_cycloid.clicked.connect(self.send_to_axis_cycloid_waveform)
        # update graph
        self.ui.update_graph.clicked.connect(lambda: self.update_graph('update'))
        self.ui.clear_graph.clicked.connect(lambda: self.update_graph('clear'))
        self.ui.send_to_daq.clicked.connect(self.run_ni_daq)

        #ypdate cycloid labels
        self.ui.doubleSpinBox.valueChanged.connect(self.update_cycloid_frequency_label)
        self.update_cycloid_frequency_label(self.ui.doubleSpinBox.value())
        
        
        self.NI_DAQ_thread = NI_DAQ(self.X_axis_data[:, 1],self.Y_axis_data[:, 1],self.sampling_rate.value())
        self.ui.stop_daq.clicked.connect(self.NI_DAQ_thread.stop)
        self.NI_DAQ_thread.finished.connect(self.on_daq_finished)
        self.ui.stop_daq.setEnabled(False)
        
    def get_desktop_path(self):
        """Returns the path to the user's desktop"""
        # Platform-independent method using Qt
        desktop = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
        
        # Alternative using pure Python (cross-platform)
        # desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        
        # Make sure the path uses correct slashes for the current OS
        return os.path.normpath(desktop)

    def browse_for_txt_file(self):
        """Opens a file dialog to select a .txt file and sets the path to lineEdit"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Text File",
            QDir.homePath(),  # Start at user's home directory
            "Text Files (*.txt);;All Files (*)"  # File filter
        )
        
        if file_path:  # If user selected a file (didn't cancel)
            self.ui.path_to_file_lineEdit.setText(file_path)

    def on_axis_changed(self):
        """Handler for axis combo box changes"""
        # Get the current text
        selected_axis = self.ui.axis_comboBox.currentText()
        
        # You can perform different actions based on the selection
        if selected_axis == "X-Axis" and self.X_axis_parameters is not None:
            
            self.amplitude.setValue(float(self.X_axis_parameters[0,0]))  # Convert to float
            self.amplitude.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            
            self.waveform_frequency.setValue(int(self.X_axis_parameters[0,1]))  # Convert to int
            self.waveform_frequency.setStyleSheet("background-color: #C0C0FF;")  # Light blue

            self.number_of_points.setValue(int(self.X_axis_parameters[0,2]))
            self.number_of_points.setStyleSheet("background-color: #C0C0FF;")  # Light blue

            self.width.setValue(float(self.X_axis_parameters[0,3]))
            self.width.setStyleSheet("background-color: #C0C0FF;")  # Light blue

            self.sampling_rate.setValue(int(self.X_axis_parameters[0,4]))  # Convert to int
            self.sampling_rate.setStyleSheet("background-color: #C0C0FF;")  # Light blue

            self.duration.setValue(float(self.X_axis_parameters[0,5]))
            self.duration.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.ui.standard_waveform_comboBox.setCurrentText(self.X_axis_parameters[0,6])

            self.ui.path_to_file_lineEdit.setText(self.X_axis_parameters[0,7])
            self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #C0C0FF;")

            self.T.setStyleSheet("background-color: #FFFFFF;") 
            self.TrampCV.setStyleSheet("background-color:#FFFFFF;") 
            self.TrackingDelay.setStyleSheet("background-color: #FFFFFF;")  
            self.A.setStyleSheet("background-color: #FFFFFF;")  
            self.num_points.setStyleSheet("background-color: #FFFFFF;")  
            self.sample_rate_cycloid.setStyleSheet("background-color: #FFFFFF;")

        elif selected_axis == "X-Axis" and self.X_axis_parameters == None:
            if self.X_axis_cycloid_parameters is not None:
                self.amplitude.setStyleSheet("background-color: #FFFFFF;")  # white
                self.waveform_frequency.setStyleSheet("background-color: #FFFFFF;")  # white
                self.number_of_points.setStyleSheet("background-color: #FFFFFF;")  # white
                self.width.setStyleSheet("background-color: #FFFFFF;")  # white
                self.sampling_rate.setStyleSheet("background-color: #FFFFFF;")  # white
                self.duration.setStyleSheet("background-color: #FFFFFF;")  # white
                self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFFFFF;") #white

                self.T.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                self.T.setValue(float(self.X_axis_cycloid_parameters[0,0]))
                self.TrampCV.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                self.TrampCV.setValue(float(self.X_axis_cycloid_parameters[0,1]))
                self.TrackingDelay.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                self.TrackingDelay.setValue(float(self.X_axis_cycloid_parameters[0,2]))
                self.A.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                self.A.setValue(float(self.X_axis_cycloid_parameters[0,3]))
                self.num_points.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                self.num_points.setValue(int(self.X_axis_cycloid_parameters[0,4]))
                #self.sample_rate_cycloid.setStyleSheet("background-color: #C0C0FF;")  # Light blue
                #self.sample_rate_cycloid.setValue(int(self.X_axis_cycloid_parameters[0,5]))
                
                self.ui.cycloid_waveform_comboBox.setCurrentText(self.X_axis_cycloid_parameters[0,5])
            else:
                self.amplitude.setStyleSheet("background-color: #FFFFFF;")  # white
                self.waveform_frequency.setStyleSheet("background-color: #FFFFFF;")  # white
                self.number_of_points.setStyleSheet("background-color: #FFFFFF;")  # white
                self.width.setStyleSheet("background-color: #FFFFFF;")  # white
                self.sampling_rate.setStyleSheet("background-color: #FFFFFF;")  # white
                self.duration.setStyleSheet("background-color: #FFFFFF;")  # white
                self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFFFFF;") #white

                self.T.setStyleSheet("background-color: #FFFFFF;") 
                self.TrampCV.setStyleSheet("background-color:#FFFFFF;") 
                self.TrackingDelay.setStyleSheet("background-color: #FFFFFF;")  
                self.A.setStyleSheet("background-color: #FFFFFF;")  
                self.num_points.setStyleSheet("background-color: #FFFFFF;")  
                self.sample_rate_cycloid.setStyleSheet("background-color: #FFFFFF;") 
                
                



        if selected_axis == "Y-Axis" and self.Y_axis_parameters is not None:
            self.amplitude.setValue(float(self.Y_axis_parameters[0,0]))
            self.amplitude.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.waveform_frequency.setValue(int(self.Y_axis_parameters[0,1]))
            self.waveform_frequency.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.number_of_points.setValue(int(self.Y_axis_parameters[0,2]))
            self.number_of_points.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.width.setValue(float(self.Y_axis_parameters[0,3]))
            self.width.setStyleSheet("background-color: #FFC0C0;")  # red
            self.sampling_rate.setValue(int(self.Y_axis_parameters[0,4]))
            self.sampling_rate.setStyleSheet("background-color: #FFC0C0;")  # red
            self.duration.setValue(float(self.Y_axis_parameters[0,5]))
            self.duration.setStyleSheet("background-color: #FFC0C0;")  # red
            self.ui.standard_waveform_comboBox.setCurrentText(self.Y_axis_parameters[0,6])
            self.ui.path_to_file_lineEdit.setText(self.Y_axis_parameters[0,7])
            self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFC0C0;")

            self.T.setStyleSheet("background-color: #FFFFFF;") 
            self.TrampCV.setStyleSheet("background-color:#FFFFFF;") 
            self.TrackingDelay.setStyleSheet("background-color: #FFFFFF;")  
            self.A.setStyleSheet("background-color: #FFFFFF;")  
            self.num_points.setStyleSheet("background-color: #FFFFFF;")  
            #self.sample_rate_cycloid.setStyleSheet("background-color: #FFFFFF;")

        elif selected_axis == "Y-Axis" and self.Y_axis_parameters == None:
            if self.Y_axis_cycloid_parameters is not None:
                self.amplitude.setStyleSheet("background-color: #FFFFFF;")  # white
                self.waveform_frequency.setStyleSheet("background-color: #FFFFFF;")  # white
                self.number_of_points.setStyleSheet("background-color: #FFFFFF;")  # white
                self.width.setStyleSheet("background-color: #FFFFFF;")  # white
                self.sampling_rate.setStyleSheet("background-color: #FFFFFF;")  # white
                self.duration.setStyleSheet("background-color: #FFFFFF;")  # white
                self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFFFFF;") #white

                self.T.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                self.T.setValue(float(self.Y_axis_cycloid_parameters[0,0]))
                self.TrampCV.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                self.TrampCV.setValue(float(self.Y_axis_cycloid_parameters[0,1]))
                self.TrackingDelay.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                self.TrackingDelay.setValue(float(self.Y_axis_cycloid_parameters[0,2]))
                self.A.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                self.A.setValue(float(self.Y_axis_cycloid_parameters[0,3]))
                self.num_points.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                self.num_points.setValue(int(self.Y_axis_cycloid_parameters[0,4]))
                #self.sample_rate_cycloid.setStyleSheet("background-color: #FFC0C0;")  # Light blue
                #self.sample_rate_cycloid.setValue(int(self.Y_axis_cycloid_parameters[0,5]))
                
                self.ui.cycloid_waveform_comboBox.setCurrentText(self.Y_axis_cycloid_parameters[0,5])
            else:
                self.amplitude.setStyleSheet("background-color: #FFFFFF;")  # white
                self.waveform_frequency.setStyleSheet("background-color: #FFFFFF;")  # white
                self.number_of_points.setStyleSheet("background-color: #FFFFFF;")  # white
                self.width.setStyleSheet("background-color: #FFFFFF;")  # white
                self.sampling_rate.setStyleSheet("background-color: #FFFFFF;")  # white
                self.duration.setStyleSheet("background-color: #FFFFFF;")  # white
                self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFFFFF;") #white

                self.T.setStyleSheet("background-color: #FFFFFF;") 
                self.TrampCV.setStyleSheet("background-color:#FFFFFF;") 
                self.TrackingDelay.setStyleSheet("background-color: #FFFFFF;")  
                self.A.setStyleSheet("background-color: #FFFFFF;")  
                self.num_points.setStyleSheet("background-color: #FFFFFF;")  
                self.sample_rate_cycloid.setStyleSheet("background-color: #FFFFFF;") 
                
                

    def run_ni_daq(self):
        # Stop any running task first
        if self.NI_DAQ_thread.isRunning():
            self.NI_DAQ_thread.stop()

        self.NI_DAQ_thread.x_selected = self.ui.x_axis_checkBox.isChecked()
        self.NI_DAQ_thread.y_selected = self.ui.y_axis_checkBox.isChecked()
        self.NI_DAQ_thread.mirror_mode = self.ui.checkBox.isChecked()

        # Pass the data directly (let thread handle empty arrays)
        self.NI_DAQ_thread.X_axis_data = self.X_axis_data[:, 1] if len(self.X_axis_data) > 0 else np.array([])
        self.NI_DAQ_thread.Y_axis_data = self.Y_axis_data[:, 1] if len(self.Y_axis_data) > 0 else np.array([])
            
        self.NI_DAQ_thread.sampling_rate = self.sampling_rate.value()
        # Start new acquisition
        self.NI_DAQ_thread.start()
        self.ui.send_to_daq.setEnabled(False)  # Disable while running
        self.ui.stop_daq.setEnabled(True)

    def on_daq_finished(self):
        """Connect this to the NI_DAQ_thread's finished signal"""
        self.ui.send_to_daq.setEnabled(True)
        self.ui.stop_daq.setEnabled(False)

    def get_waveform(self,axis_selected):
        self.waveform_selected = self.ui.standard_waveform_comboBox.currentText()

        if self.waveform_selected == 'Input text':
            file_data = self.read_text_file_to_array()
            if file_data is not None:
                self.text_file_Waveform = file_data * self.amplitude.value()  # First column
                #print(self.text_file_Waveform)
                duration = len(self.text_file_Waveform)/self.sampling_rate.value()
                self.number_of_points.setValue(int(len(self.text_file_Waveform)))
                self.waveform_frequency.setValue(1/duration)
            self.waveform_time = np.linspace(0, duration, len(self.text_file_Waveform), endpoint=False)
            new_data = np.column_stack((self.waveform_time, self.text_file_Waveform))
        else:
            self.waveform_time = np.linspace(0, int(self.number_of_points.value())/self.sampling_rate.value(), int(self.number_of_points.value()), endpoint=True)

        if self.waveform_selected == 'Sine':
            self.sine_waveform_data = self.amplitude.value() * np.sin(2 * np.pi * self.waveform_frequency.value() * self.waveform_time)  # Sine wave
            new_data = np.column_stack((self.waveform_time[:-1], self.sine_waveform_data[:-1]))
        if self.waveform_selected == 'Square':
            self.square_waveform_data = self.amplitude.value() * square(2 * np.pi * self.waveform_frequency.value() * self.waveform_time)  # Sine wave
            new_data = np.column_stack((self.waveform_time[:-1], self.square_waveform_data[:-1]))
        if self.waveform_selected == 'Triangle':
            self.triangle_waveform_data = self.amplitude.value() * sawtooth(2 * np.pi * self.waveform_frequency.value() * self.waveform_time, width=0.5)  # Sine wave
            new_data = np.column_stack((self.waveform_time[:-1], self.triangle_waveform_data[:-1]))
        if self.waveform_selected == 'Sawtooth':
            self.sawtooth_waveform_data = self.amplitude.value() * sawtooth(2 * np.pi * self.waveform_frequency.value() * self.waveform_time, width=self.width.value())  # Sine wave
            new_data = np.column_stack((self.waveform_time[:-1], self.sawtooth_waveform_data[:-1]))

        #self.sampling_rate = self.ui.sample_rate_spinBox
        self.number_of_points = self.ui.number_points_spinBox

        if axis_selected == 'X-Axis':
            self.X_axis_cycloid_parameters = None
            self.X_axis_data = new_data
            self.X_axis_parameters = np.array([
                [float(self.amplitude.value()),
                int(self.waveform_frequency.value()),
                int(self.number_of_points.value()),
                float(self.width.value()),
                int(self.sampling_rate.value()),
                float(int(self.number_of_points.value())/self.sampling_rate.value()),
                str(self.waveform_selected),
                str(self.ui.path_to_file_lineEdit.text())]
            ])
            
            if self.Y_axis_parameters is not None:
                self.Y_axis_parameters[0,4] = self.sampling_rate.value()

            self.amplitude.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.waveform_frequency.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.sampling_rate.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.width.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.number_of_points.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.duration.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #C0C0FF;")

        elif axis_selected == 'Y-Axis':
            self.Y_axis_cycloid_parameters = None
            self.Y_axis_data = new_data
            self.Y_axis_parameters = np.array([
                [float(self.amplitude.value()),
                int(self.waveform_frequency.value()),
                int(self.number_of_points.value()),
                float(self.width.value()),
                int(self.sampling_rate.value()),
                float(int(self.number_of_points.value())/self.sampling_rate.value()),
                str(self.waveform_selected),
                str(self.ui.path_to_file_lineEdit.text())]
            ])
            
            if self.X_axis_parameters is not None:
                self.X_axis_parameters[0,4] = self.sampling_rate.value()

            self.amplitude.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.waveform_frequency.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.number_of_points.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.width.setStyleSheet("background-color: #FFC0C0;")  # red
            self.sampling_rate.setStyleSheet("background-color: #FFC0C0;")  # red
            self.duration.setStyleSheet("background-color: #FFC0C0;")  # red
            self.ui.path_to_file_lineEdit.setStyleSheet("background-color: #FFC0C0;")
        self.on_axis_changed()

    def send_to_axis_standar_waveform(self):
        self.get_waveform(self.ui.axis_comboBox.currentText())

    def get_cycloid_waveform(self,axis_selected):
        self.cycloid_waveform_selected = self.ui.cycloid_waveform_comboBox.currentText()
        self.update_cycloid_parameters()
        
        if self.cycloid_waveform_selected == 'Triangle':
            self.triangle_cycloid_waveform_time, self.triangle_cycloid_waveform_data, data_output = self.cycloid_func.get_triangle_cycliod()   
            new_data = np.column_stack((self.triangle_cycloid_waveform_time, self.triangle_cycloid_waveform_data))
        if self.cycloid_waveform_selected == 'Sawtooth':
            self.sawtooth_cycloid_waveform_time, self.sawtooth_cycloid_waveform_data, data_output = self.cycloid_func.get_sawtooth_cycliod()   
            new_data = np.column_stack((self.sawtooth_cycloid_waveform_time, self.sawtooth_cycloid_waveform_data))
        if axis_selected == 'X-Axis':
            self.X_axis_parameters = None
            self.X_axis_data = new_data
            self.X_axis_cycloid_parameters = np.array([
                [float(self.T.value()),
                float(self.TrampCV.value()),
                float(self.TrackingDelay.value()),
                float(self.A.value()),
                int(self.num_points.value()),
                str(self.cycloid_waveform_selected)]
            ])

            if self.Y_axis_cycloid_parameters is not None:
                self.Y_axis_cycloid_parameters[0,4] = self.sampling_rate.value()

            self.T.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.TrampCV.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.TrackingDelay.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.A.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.num_points.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            self.sample_rate_cycloid.setStyleSheet("background-color: #C0C0FF;")  # Light blue
            
        elif axis_selected == 'Y-Axis':
            self.Y_axis_parameters = None
            self.Y_axis_data = new_data
            self.Y_axis_cycloid_parameters = np.array([
                [float(self.T.value()),
                float(self.TrampCV.value()),
                float(self.TrackingDelay.value()),
                float(self.A.value()),
                int(self.num_points.value()),
                str(self.cycloid_waveform_selected)]
            ])
            self.T.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.TrampCV.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.TrackingDelay.setStyleSheet("background-color: #FFC0C0;")  # Light red
            self.A.setStyleSheet("background-color: #FFC0C0;")  # red
            self.num_points.setStyleSheet("background-color: #FFC0C0;")  # red
            self.sample_rate_cycloid.setStyleSheet("background-color: #FFC0C0;")  # red
            
            if self.X_axis_cycloid_parameters is not None:
                self.X_axis_cycloid_parameters[0,4] = self.sampling_rate.value()
        
        self.update_stats_cycloids(data_output)
        self.on_axis_changed()

    def send_to_axis_cycloid_waveform(self):
        self.get_cycloid_waveform(self.ui.axis_comboBox.currentText())

    def update_cycloid_parameters(self):
        num_cycles = 1
        total_points = int(self.sampling_rate.value() * self.T.value() * num_cycles)
        self.num_points.setValue(total_points)
        self.cycloid_func.A = self.A.value()
        self.cycloid_func.T = self.T.value()
        self.cycloid_func.TrampCV = self.TrampCV.value()
        self.cycloid_func.TrackingDelay = self.TrackingDelay.value()
        self.cycloid_func.num_points = self.num_points.value()

    def update_stats_cycloids(self,data_output):
        self.ui.label_10.setText(f"Flyback Time  = {data_output[0]:.4f}" + ' s')
        self.ui.label_11.setText(f"Flyback Frequency = {data_output[1]:.2f}" + ' Hz')

    def update_cycloid_frequency_label(self,value):
        
        self.ui.cycloid_frequency_label.setText(f"Frequency =  {1/value:.2f}" + ' Hz')

    def update_graph(self,update_graph_state):
        if update_graph_state == 'setup':
            scope_space = self.ui.plot_widget
            self.fig, self.ax = plt.subplots()
            self.fig.set_facecolor((0, 0, 0, 0.7)) #make background black
            self.canvas = FigureCanvas(self.fig)
            layout = qtw.QVBoxLayout(scope_space)
            layout.addWidget(self.canvas)
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            self.ax.clear()
        
        # Add constant voltage horizontal lines
        self.ax.axhline(y=10, color='blue', linestyle='-', linewidth=1.5, alpha=0.7)
        self.ax.axhline(y=-10, color='red', linestyle='-', linewidth=1.5, alpha=0.7)
        #Plot data if it exists
        if update_graph_state == 'update':
            if self.ui.x_axis_checkBox.isChecked():
                if len(self.X_axis_data) > 0:
                    self.ax.plot(self.X_axis_data[:, 0], self.X_axis_data[:, 1],color='yellow', label='X-Axis')
                    self.ax.legend()
            if self.ui.y_axis_checkBox.isChecked():        
                if len(self.Y_axis_data) > 0:
                    self.ax.plot(self.Y_axis_data[:, 0], self.Y_axis_data[:, 1],color='green', label='Y-Axis')
                    self.ax.legend()
        self.ax.set_xlabel('time [seconds]', color='white')
        self.ax.set_ylabel('volts', color='white')
        self.ax.xaxis.set_tick_params(labelcolor='white')
        self.ax.yaxis.set_tick_params(labelcolor='white')
        self.ax.grid(True)
        # Force autoscaling
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()  # Auto-scale the view
        # Adjust subplot parameters to maximize plot space
        self.ax.figure.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
        self.ax.set_facecolor((0, 0, 0, 0.1))
        
        self.canvas.draw()

    
    def update_sawtooth_width_state(self):
        self.waveform_selected = self.ui.standard_waveform_comboBox.currentText()
        if self.waveform_selected == 'Sawtooth':
            self.ui.width_doubleSpinBox.setEnabled(True) # enable width from sawtooth when not selected
            self.ui.path_to_file_lineEdit.setEnabled(False) # enable textbox 
            self.ui.waveform_frequency_doubleSpinBox.setEnabled(True)
        elif self.waveform_selected == 'Input text':
            self.ui.path_to_file_lineEdit.setEnabled(True) # enable textbox 
            self.ui.width_doubleSpinBox.setEnabled(False) # disable width from sawtooth when not selected
            self.ui.waveform_frequency_doubleSpinBox.setEnabled(False)
        else:
            self.ui.width_doubleSpinBox.setEnabled(False) # disable width from sawtooth when not selected
            self.ui.path_to_file_lineEdit.setEnabled(False) # enable textbox 
            self.ui.waveform_frequency_doubleSpinBox.setEnabled(True)

    def setup_colored_combobox(self):
        # Create and set the delegate
        delegate = ColoredComboBoxDelegate(self.ui.axis_comboBox)
        self.ui.axis_comboBox.setItemDelegate(delegate)
        
        # Connect signals to handle dynamic updates
        self.ui.axis_comboBox.currentIndexChanged.connect(
            lambda: self.ui.axis_comboBox.view().update()
        )
        
        # Force initial update
        self.ui.axis_comboBox.view().update()

    def read_text_file_to_array(self):
        """Reads the text file path from lineEdit and returns data as numpy array"""
        try:
            # Get path from lineEdit
            file_path = self.ui.path_to_file_lineEdit.text().strip()
            
            # Verify path exists
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Error", "File does not exist!")
                return None
            
            # First read the file as text
            with open(file_path, 'r') as f:
                content = f.read()
        
            # Remove any 'F' suffixes that might be present
            content = content.replace('F', '')
        

            # Read file based on its content
            if file_path.endswith('.txt'):
                # For simple text files with numbers
                data = np.loadtxt(file_path)
            elif file_path.endswith('.csv'):
                # For CSV files (comma separated)
                data = np.genfromtxt(file_path, delimiter=',')
            else:
                # Try generic load (will work for space/tab delimited files)
                data = np.loadtxt(file_path)

            # Stack all columns vertically into a single column
            if data.ndim > 1:
                # Reshape to (n*m, 1) by stacking columns vertically
                data = data.T.reshape(-1, 1)[:, 0]  # Transpose, reshape, then flatten
            elif data.ndim == 1:
                # Already 1D, use as is
                pass
            else:
                raise ValueError("Unexpected data shape in file")
            
            return data
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read file:\n{str(e)}")
            return None
    
class NI_DAQ(QThread):
    def __init__(self,X_data,Y_data,sampling_rate):
        super().__init__()
        
        
        self._stop_event = threading.Event()
        self.X_axis_data = X_data
        self.Y_axis_data = Y_data
        self.sampling_rate = sampling_rate
        self.task = None  # Initialize task as None
        self._lock = threading.Lock()  # Add a lock for thread safety
        self._safe_to_stop = threading.Event()  # New event for safe stopping
        self.x_selected = False
        self.y_selected = False
        self.mirror_mode = False
    def stop(self):
        # Signal to stop
        self._stop_event.set()
        
        # Wait for thread to acknowledge it's safe to cleanup
        if not self._safe_to_stop.wait(1000):  # Wait up to 1 second
            print("Warning: Thread didn't stop gracefully")
        
        # Now do the cleanup
        with self._lock:
            if self.task:
                try:
                    if not self.task.is_task_done():
                        self.task.stop()
                    self.task.close()
                except Exception as e:
                    print(f"Cleanup error: {e}")
                finally:
                    self.task = None

        
        
    def run(self):
        self._stop_event.clear()
        self._safe_to_stop.clear()
        
        try:
            with self._lock:
                if self._stop_event.is_set():
                    return

                # Convert to numpy arrays and ensure proper shape
                x_data = np.array(self.X_axis_data, dtype=np.float64)
                y_data = np.array(self.Y_axis_data, dtype=np.float64)
                
                # Initialize variables
                min_len = 0
                output_data = None
                channels_to_add = []
                
                # Determine which channels to use based on UI selections
                use_x = self.x_selected and len(x_data) > 0
                use_y = self.y_selected and len(y_data) > 0 and not self.mirror_mode
                
                # Case 1: Both X and Y have data (and Y isn't mirroring X)
                if use_x and use_y:
                    min_len = min(len(x_data), len(y_data))
                    output_data = np.vstack((
                        x_data[:min_len],
                        y_data[:min_len]
                    ))
                    channels_to_add = ["Dev1/ao0", "Dev1/ao1"]
                
                # Case 2: Only X has data (or mirror mode)
                elif use_x:
                    min_len = len(x_data)
                    if self.mirror_mode:
                        output_data = np.vstack((
                            x_data,
                            x_data
                        ))
                        channels_to_add = ["Dev1/ao0", "Dev1/ao1"]
                    else:
                        output_data = x_data.reshape(1, -1)  # Shape (1, N)
                        channels_to_add = ["Dev1/ao0"]
                
                # Case 3: Only Y has data
                elif use_y:
                    min_len = len(y_data)
                    output_data = y_data.reshape(1, -1)  # Shape (1, N)
                    channels_to_add = ["Dev1/ao1"]
                
                else:
                    print("Error: No valid channels selected or no data available")
                    return
                
                # Before creating a new task, ensure old one is cleared
                if hasattr(self, 'task') and self.task:
                    self.task.close()
                    self.task = None  # Explicitly clear it

                # Now create a fresh task
                self.task = nidaqmx.Task()

                print('number of channels in task: {}'.format(channels_to_add))

                # Add the determined channels
                for channel in channels_to_add:
                    self.task.ao_channels.add_ao_voltage_chan(channel)
                print(f"Task channels: {self.task.ao_channels.channel_names}")

                # Configure for continuous output with regeneration
                self.task.timing.cfg_samp_clk_timing(
                    rate=self.sampling_rate,
                    sample_mode=AcquisitionType.CONTINUOUS,
                    samps_per_chan=min_len
                )
                self.task.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.ALLOW_REGENERATION
                
                
                # Ensure proper shape before writing
                if output_data.shape[0] == 1:
                    # Only one channel, reshape to 1D array
                    output_data = output_data.flatten()
                print('# channels on data: {}'.format(output_data.shape))

                self.task.write(output_data, auto_start=True)
                #self.task.start()
                
            # Main loop - runs outside the lock
            while not self._stop_event.is_set():
                self.msleep(10)  # Small sleep to keep UI responsive
                
        except Exception as e:
            print(f"DAQ Error: {e}")
        finally:
            # Signal that we're ready for cleanup
            self._safe_to_stop.set()
            
            # Quick cleanup if not already done
            if self.task and not self._stop_event.is_set():
                try:
                    self.task.stop()
                    self.task.close()
                except:
                    pass
                finally:
                    self.task = None

class ColoredComboBoxDelegate(qtw.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        
        # Get the text of the current item
        text = index.data(qtc.Qt.DisplayRole)
        
        # Set background colors based on text
        if text == "X-Axis":
            option.backgroundBrush = QBrush(QColor(192, 192, 255))  # Light blue
        elif text == "Y-Axis":
            option.backgroundBrush = QBrush(QColor(255, 192, 192))  # Light red

if __name__ == '__main__':
    # Enable High-DPI scaling BEFORE creating QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # <-- Must come first!
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # Optional: For high-res icons

    # Now create the application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Create and show your main window
    WAVEFORM_GEM = Pangolin_waveform_generator()
    WAVEFORM_GEM.show()

    sys.exit(app.exec_())
