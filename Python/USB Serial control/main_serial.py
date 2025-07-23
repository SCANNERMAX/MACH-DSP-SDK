import sys
from serial_front_end import Ui_MainWindow
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5.QtCore import  QObject, pyqtSignal, QThread, Qt
import threading
from PyQt5.QtWidgets import QApplication
import os
import serial
import serial.tools.list_ports

os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1' # pangolin screen

class PANGOLIN_SERIAL(qtw.QMainWindow):
    def __init__(self, * args, **kwargs):
        super().__init__(*args,**kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        #create signal object
        self.update_signal = UpdateSignal()
        self.serial_coms = COMS_MDSP(self.ui,self.update_signal)
        self.serial_coms.setup_com_list()
        self.serial_coms.update_com_list()
        self.port_name = None
        #self.ui.connect_button.clicked.connect(self.update_coms) 
        self.ui.refres_coms.clicked.connect(self.update_coms_button)
        self.ui.connect_button.clicked.connect(self.stablish_connection)
        self.ui.x_axis_checkBox.setChecked(True)
        self.ui.x_axis_checkBox.clicked.connect(self.sync_axis_checkboxes)
        self.ui.y_axis_checkBox.clicked.connect(self.sync_axis_checkboxes)

        # get flags
        self.ui.servo_flags_button.clicked.connect(self.get_flags)
        self.update_signal.servo_ready_label.connect(lambda data: self.update_flags_colors(data, 'servo_ready_label'))
        self.update_signal.power_supply_status_label.connect(lambda data: self.update_flags_colors(data, 'power_supply_status_label'))
        
        # serial commands
        self.update_signal.command_send_signal.connect(self.update_command_signal)
        self.update_signal.response.connect(self.update_response)

        # get power supply
        self.update_signal.positive_power_status_signal.connect(lambda data: self.update_positive_power_label(data,'positive'))
        self.update_signal.negative_power_status_signal.connect(lambda data: self.update_positive_power_label(data,'negative'))
        self.ui.power_supply_button.clicked.connect(self.get_power_supply)

        # get tuning number
        self.ui.read_tuning_button.clicked.connect(self.get_tuning_number)
        self.update_signal.tuning_number_signal.connect(self.update_tuning_label)
        
        #write tuning number
        self.ui.activate_tunning_number.clicked.connect(self.write_tuning_number)
        
        #write function generator frequency
        self.ui.write_function_generator_frequency_button.clicked.connect(self.write_generator_frequency)

        #write function generator amplitude
        self.ui.write_function_generator_amplitude_button.clicked.connect(self.write_generator_amplitude)

        #write function generator waveform
        self.ui.generator_waveform_button.clicked.connect(self.write_generator_waveform)

    def update_command_signal(self,data):
        self.ui.command_label.clear()
        self.ui.command_label.setText(data)

    def update_response(self,data):
        self.ui.response_label.clear()
        self.ui.response_label.setText(data)

    def get_tuning_number(self):
        self.update_signal.read_tuning_number_state = 'update'
        self.update_signal.read_tuning_number_signal .emit(self.update_signal.read_tuning_number_state)

    def write_tuning_number(self):
        self.ui.response_label.clear()
        self.serial_coms.write_tuning_number = self.ui.write_tuning_spinBox.value()
        self.update_signal.write_tuning_number_state = 'update'
        self.update_signal.write_tuning_number_signal .emit(self.update_signal.write_tuning_number_state)

    def write_generator_frequency(self):
        self.ui.response_label.clear()
        self.serial_coms.generator_frequency = self.ui.generator_frequency_spinBox.value()
        self.update_signal.write_generator_frequency_state = 'update'
        self.update_signal.write_generator_frequency_signal .emit(self.update_signal.write_generator_frequency_state)
    
    def write_generator_amplitude(self):
        self.ui.response_label.clear()
        self.serial_coms.generator_amplitude = self.ui.generator_amplitude_spinBox.value()
        self.update_signal.write_generator_amplitude_state = 'update'
        self.update_signal.write_generator_amplitude_signal .emit(self.update_signal.write_generator_amplitude_state)

    def write_generator_waveform(self):
        self.ui.response_label.clear()
        self.serial_coms.generator_waveform = self.ui.generator_waveform_spinBox.value()
        self.update_signal.write_generator_waveform_state = 'update'
        self.update_signal.write_generator_waveform_signal .emit(self.update_signal.write_generator_waveform_state)

    def update_tuning_label(self,data):
        self.ui.tuning_label.setText(data)

    def get_power_supply(self):
        self.update_signal.power_supply_state = 'update'
        self.update_signal.power_supply_state_signal .emit(self.update_signal.power_supply_state)
        
    def update_positive_power_label(self,data, source):
        if source == 'positive':
            self.ui.positive_power_label.setText('Positive supply voltage: ' + data + ' volts')
        if source == 'negative':
            self.ui.negative_power_label.setText('Negative supply voltage: ' + data + ' volts')


    def get_flags(self):
        self.update_signal.servo_flag_state = 'update'
        self.update_signal.servo_flag_state_signal .emit(self.update_signal.servo_flag_state)
        #QApplication.processEvents()

    def update_flags_colors(self,data,source):
        if source == 'servo_ready_label':
            self.ui.servo_ready_label.setStyleSheet("background-color: " + data)
        elif source == 'power_supply_status_label':
            self.ui.power_supply_status_label.setStyleSheet("background-color: " + data)

    def sync_axis_checkboxes(self):
        """Ensures only one axis checkbox is checked at a time."""
        sender = self.sender()  # Get which checkbox triggered the signal
        if sender == self.ui.x_axis_checkBox:
            self.ui.y_axis_checkBox.setChecked(False)
            self.update_signal.axis_selected = 'x-axis'
        elif sender == self.ui.y_axis_checkBox:
            self.ui.x_axis_checkBox.setChecked(False)
            self.update_signal.axis_selected = 'y-axis'
        self.update_signal.axis_selected_signal.emit(self.update_signal.axis_selected)

    def stablish_connection(self):
        current_label = self.ui.connect_button.text()
        if current_label == "Connect":
            # check for the selected comport that is being selected
            #self.coms_mdsp.update_com_list()
            self.port_name = self.serial_coms.port_list[self.ui.comboBox_6.currentIndex()]
            
            if self.port_name == '' and self.port_name is None: # meaning no comport has been selected
                qtw.QMessageBox.critical(self,'Error','Please select a COM!')
            else:  
                self.serial_coms.open_serial_port()
                self.serial_coms.start()
                
            self.ui.connect_button.setText("Disconnect")
        if current_label == "Disconnect":
            self.update_signal.power_supply_status_label.emit('#000000')
            self.update_signal.servo_ready_label.emit('#000000')
            threads_to_stop = [self.serial_coms]
        
            for thread in threads_to_stop:
                if thread.isRunning():
                    self.update_signal.connection_state = 'break_connection'
                    self.update_signal.connection_state_signal.emit(self.update_signal.connection_state)
                    thread.stop()
            self.ui.connect_button.setText("Connect")
            

    def update_coms_button(self):
        self.serial_coms.update_com_list()

class UpdateSignal(QObject):
    connection_state = ''
    connection_state_signal = pyqtSignal(str)

    axis_selected = 'x-axis'
    axis_selected_signal = pyqtSignal(str)

    servo_flag_state = 'no_update'
    servo_flag_state_signal = pyqtSignal(str)
    servo_ready_label = pyqtSignal(str)
    power_supply_status_label = pyqtSignal(str)

    command_send_signal = pyqtSignal(str)
    response = pyqtSignal(str)

    positive_power_status_signal = pyqtSignal(str)
    negative_power_status_signal = pyqtSignal(str)
    power_supply_state = 'no_update'
    power_supply_state_signal = pyqtSignal(str)

    tuning_number_signal = pyqtSignal(str)
    read_tuning_number_state = 'no_update'
    read_tuning_number_signal = pyqtSignal(str)

    write_tuning_number_state = 'no_update'
    write_tuning_number_signal = pyqtSignal(str)
    
    write_generator_frequency_state = 'no_update'
    write_generator_frequency_signal = pyqtSignal(str)

    write_generator_amplitude_state = 'no_update'
    write_generator_amplitude_signal = pyqtSignal(str)

    write_generator_waveform_state = 'no_update'
    write_generator_waveform_signal = pyqtSignal(str)
    
class COMS_MDSP(QThread):
    def __init__(self,UI,update_signal):
        super().__init__()
        self.serial_port = None  # Initialize serial port without any specific port
        self.ui = UI
        self.update_signal = update_signal
        self._stop_event = threading.Event()
        self.port_name = 'None'
        self.port_list = []
        self.new_port_list = []
        self.tuning_number_to_write = None
        self.generator_frequency = None
        self.generator_amplitude = None
        self.generator_waveform = None

    def pause(self):
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()

    def resume(self):
        self.mutex.lock()
        self.paused = False
        self.mutex.unlock()
        
    def setup_com_list(self):
        all_ports = serial.tools.list_ports.comports()
        self.port_list = [port.device for port in all_ports]
        self.ui.comboBox_6.clear()
        self.ui.comboBox_6.addItems(self.port_list)
        
    def update_com_list(self):
        # Get all port objects, not just device names
        all_ports = serial.tools.list_ports.comports()
        
        # Filter only external USB serial ports
        usb_ports = []
        for port in all_ports:  # Now port is a ListPortInfo object
            try:
                # Common indicators of USB serial adapters
                is_usb = (
                    'usb' in port.hwid.lower() or 
                    'ftdi' in port.hwid.lower() or 
                    'pl2303' in port.hwid.lower() or 
                    'cp210' in port.hwid.lower() or
                    'ch340' in port.hwid.lower()
                )
                
                # Exclude virtual ports and internal devices
                is_virtual = (
                    'bluetooth' in port.description.lower() or
                    'com0com' in port.description.lower() or
                    'ttyS' in port.device.lower() or  # Linux serial ports
                    'ttyAMA' in port.device.lower()   # Raspberry Pi serial
                )
                
                if is_usb and not is_virtual:
                    usb_ports.append(port.device)
            except AttributeError:
                # Skip ports that don't have the expected attributes
                continue
        
        # Update the port list if it has changed
        if usb_ports != self.port_list:
            self.ui.comboBox_6.clear()
            self.ui.comboBox_6.addItems(usb_ports)
            self.port_list = usb_ports
        
        
    def open_serial_port(self):
        current_index = self.ui.comboBox_6.currentIndex()
        self.port_name = self.port_list[current_index]
        
        if isinstance(self.port_name, str):
            if self.serial_port is not None and self.serial_port.isOpen():
                self.serial_port.close()  # Close the previous port if open
            self.serial_port = serial.Serial(self.port_name, 256000, timeout=0.05)
            self.serial_port.flushInput()
        else:
            self.ui.label_143.setText("Invalid port name:", self.port_name)
            
    def close_serial_port(self):
        if self.serial_port.is_open:
            self.serial_port.close()
            
    def stop(self):
        self._stop_event.set()
        
    def check_sign(self,W):
        V15 = W & 0x7FFF
        if V15 > 16383:
            return V15 - 32768
        else:
            return V15
    
    
    def servo_flags(self):
        # Read Servo Status Flags
        try:
            self.serial_port.flushInput()
            command = '80000000'
            self.serial_port.write(bytes.fromhex(command))  
            response = self.serial_port.read(8).hex()
            self.update_signal.response.emit(response)
            binary_flag_response = bin(int(response[4:], 16))[2:].zfill(16)
            print('binary response: {}'.format(binary_flag_response))
            if response[:4] == '5500':
                if self.update_signal.axis_selected == 'y-axis':
                    y_servo_ready = binary_flag_response[1]
                    if y_servo_ready == '1':
                        background_color = '#008000'
                    elif y_servo_ready == '0':
                        background_color = 'yellow'
                    self.update_signal.servo_ready_label.emit(background_color)

                    y_power_supply_fault = binary_flag_response[2]
                    if y_power_supply_fault == '1':
                        background_color = 'red'
                    elif y_power_supply_fault == '0':
                        background_color = '#008000'
                    self.update_signal.power_supply_status_label.emit(background_color)

                # X-flag
                elif self.update_signal.axis_selected == 'x-axis':
                    x_servo_ready = binary_flag_response[9]
                    if x_servo_ready == '1':
                        background_color = '#008000'
                    elif x_servo_ready == '0':
                        background_color = 'yellow'
                    self.update_signal.servo_ready_label.emit(background_color)

                    x_power_supply_fault = binary_flag_response[10]
                    if x_power_supply_fault == '1':
                        background_color = 'red'
                    elif x_power_supply_fault == '0':
                        background_color = '#008000'
                    self.update_signal.power_supply_status_label.emit(background_color)
                    
            else:
                self.serial_port.flushInput()
            self.update_signal.command_send_signal.emit(command)
        except Exception as e:
            # Handle other exceptions
            print("An error occurred:", e)
            
    def power_supply_status(self):
        
        # request positive_supply_voltage - 24 volts
        write_command = '80010000'
        self.serial_port.write(bytes.fromhex(write_command))  # Send command to the device
        response = self.serial_port.read(8).hex()
        if response[:4] == '5501':
            positive_supply_voltage = str(int(response[4:],16)/100)
            self.update_signal.positive_power_status_signal.emit(positive_supply_voltage)
        else:
            self.serial_port.flushInput()
        self.update_signal.command_send_signal.emit(write_command)
        self.update_signal.response.emit(response)
        
        # request negative_supply_voltage - 24 volts
        write_command = '80010100'
        self.serial_port.write(bytes.fromhex(write_command))  # Send command to the device
        response = self.serial_port.read(8).hex()
        if response[:4] == '5501':
            negative_supply_voltage = str(self.check_sign(int(response[4:],16))/100.0)
            self.update_signal.negative_power_status_signal.emit(negative_supply_voltage)
        else:
            self.serial_port.flushInput()
        self.update_signal.command_send_signal.emit(write_command)
        self.update_signal.response.emit(response)

    def get_tuning_number(self):
         # Read Servo Status Flags
        try:
            self.serial_port.flushInput()
            command = '80f18000'
            self.update_signal.command_send_signal.emit(command)
            send_comand = bytes.fromhex(command)
            print('send command: {}'.format(send_comand))
            print('send comand type: {}'.format(type(send_comand)))
            self.serial_port.write(send_comand)  
            response = self.serial_port.read(8).hex()
            self.update_signal.response.emit(response)
            if response[:4] == '55f1':
                tuning_number = str(int(response[4:],16))
                self.update_signal.tuning_number_signal.emit(tuning_number)
            else:
                self.serial_port.flushInput()
            
        except Exception as e:
            # Handle other exceptions
            print("An error occurred:", e)

    def write_to_board_tuning_number(self):
        while True:
            try:
                self.serial_port.flushInput()
                command = 'c0f1800' + str(self.write_tuning_number)
                self.update_signal.command_send_signal.emit(command)
                self.serial_port.write(bytes.fromhex(command))  
                response = self.serial_port.read(8).hex()
                if len(response) == 8:
                    #time.sleep(0.5)
                    self.update_signal.response.emit(response)   
                    break
                if response[:4] == 'aaf1':
                    pass
                else:
                    self.serial_port.flushInput()
            
            except Exception as e:
                # Handle other exceptions
                print("An error occurred:", e)

    def decimal_to_4digit_hex(self,decimal_num):
        """
        Convert a decimal number to 4-digit hexadecimal with leading zeros
        Args:
            decimal_num (int): The decimal number to convert
        Returns:
            str: 4-digit hexadecimal string (lowercase)
        Example:
            >>> decimal_to_4digit_hex(10)
            '000a'
            >>> decimal_to_4digit_hex(255)
            '00ff'
        """
        if not isinstance(decimal_num, int):
            raise ValueError("Input must be an integer")
        if decimal_num < 0:
            raise ValueError("Input must be a non-negative integer")
        # Convert to hex, remove '0x' prefix, and zero-pad to 4 digits
        hex_str = f"{decimal_num:04x}"
        return hex_str

    def write_function_generator_frequency(self):
        # request function generator frequency
        command = 'c01d' + str(self.decimal_to_4digit_hex(self.generator_frequency))
        self.update_signal.command_send_signal.emit(command)
        while(1):
            self.serial_port.flushInput()
            self.serial_port.write(bytes.fromhex(command))  # Send command to the device
            response = self.serial_port.read(8).hex()
            if response[:4] == 'aa1d':
                self.update_signal.response.emit(response) 
                break
            else:
                print('error writing frequency command')
                self.serial_port.flushInput()

    def write_function_generator_amplitude(self):
        # request function generator frequency
        command = 'c01e' + str(self.decimal_to_4digit_hex(self.generator_amplitude))
        self.update_signal.command_send_signal.emit(command)
        while(1):
            self.serial_port.flushInput()
            self.serial_port.write(bytes.fromhex(command))  # Send command to the device
            response = self.serial_port.read(8).hex()
            if response[:4] == 'aa1e':
                self.update_signal.response.emit(response) 
                break
            else:
                print('error writing frequency command')
                self.serial_port.flushInput()

    def write_function_generator_waveform(self):
        # request function generator frequency
        command = 'c01f' + str(self.decimal_to_4digit_hex(self.generator_waveform))
        self.update_signal.command_send_signal.emit(command)
        while(1):
            self.serial_port.flushInput()
            self.serial_port.write(bytes.fromhex(command))  # Send command to the device
            response = self.serial_port.read(8).hex()
            if response[:4] == 'aa1f':
                self.update_signal.response.emit(response) 
                break
            else:
                print('error writing frequency command')
                self.serial_port.flushInput()

        
    def run(self):
        self.servo_flags()
        while True:
            #update servo flags
            if self.update_signal.servo_flag_state == 'update':
                self.servo_flags()
                self.update_signal.servo_flag_state = 'no_update'
                self.update_signal.servo_flag_state_signal .emit(self.update_signal.servo_flag_state)

            #update power supply
            if self.update_signal.power_supply_state == 'update':
                self.power_supply_status()
                self.update_signal.power_supply_state = 'no_update'
                self.update_signal.power_supply_state_signal.emit(self.update_signal.power_supply_state)

            # get tuning number
            if self.update_signal.read_tuning_number_state == 'update':
                self.get_tuning_number()
                self.update_signal.read_tuning_number_state = 'no_update'
                self.update_signal.read_tuning_number_signal.emit(self.update_signal.read_tuning_number_state)

            # write tuning number
            if self.update_signal.write_tuning_number_state == 'update':
                self.write_to_board_tuning_number()
                self.update_signal.write_tuning_number_state = 'no_update'
                self.update_signal.write_tuning_number_signal.emit(self.update_signal.write_tuning_number_state)

            # write generator frequency
            if self.update_signal.write_generator_frequency_state == 'update':
                self.write_function_generator_frequency()
                self.update_signal.write_generator_frequency_state = 'no_update'
                self.update_signal.write_generator_frequency_signal.emit(self.update_signal.write_generator_frequency_state)

            # write generator amplitude
            if self.update_signal.write_generator_amplitude_state == 'update':
                self.write_function_generator_amplitude()
                self.update_signal.write_generator_amplitude_state = 'no_update'
                self.update_signal.write_generator_amplitude_signal.emit(self.update_signal.write_generator_amplitude_state)

            # write generator waveform
            if self.update_signal.write_generator_waveform_state == 'update':
                self.write_function_generator_waveform()
                self.update_signal.write_generator_waveform_state = 'no_update'
                self.update_signal.write_generator_waveform_signal.emit(self.update_signal.write_generator_waveform_state)



            if self.update_signal.connection_state == 'break_connection':
                break
            
        # Check for the condition to break the loop
        self.update_signal.connection_state = 'enable_connection'
        self.update_signal.connection_state_signal.emit(self.update_signal.connection_state)
        self.close_serial_port()
          

if __name__ == '__main__':

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # Optional: For high-res icons
    app = qtw.QApplication([])
    app.setStyle("Windows")
    Pangolin_serial = PANGOLIN_SERIAL()
    Pangolin_serial.show()
    sys.exit(app.exec_())