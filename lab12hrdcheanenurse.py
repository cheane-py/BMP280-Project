from guizero import App, Text, PushButton, info, Box
from datetime import datetime
import socket
import smbus2
import time
from RPLCD.i2c import CharLCD
import board
import adafruit_bmp280
import pytz
import subprocess
import threading
import os
import csv
from flask import Flask, render_template_string, request, jsonify
import webbrowser

# Flask setup
flask_app = Flask(__name__)

# Global variables
bus = smbus2.SMBus(1)
lcd = CharLCD('PCF8574', address=0x27, port=1, cols=16, rows=2)
i2c = board.I2C()
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
bmp280.sea_level_pressure = 1013.25

# Data logging variables
logging_active = False
log_file = "sensor_log.csv"
log_data = []

# Min/Max tracking
max_temperature = -float('inf')
max_pressure = -float('inf')
max_timestamp = ""
min_temperature = float('inf')
min_pressure = float('inf')
min_timestamp = ""

latest_sensor_data = {
    'temperature': 0,
    'pressure': 0,
    'altitude': 0,
    'last_update': ''
}

def get_wifi_ip():
    """Get WiFi IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "No WiFi IP"

def get_cpu_temperature():
    """Get CPU temperature as fallback if BMP280 fails"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000.0
        return temp
    except:
        return 0

def update_sensor_readings():
    """Update global sensor readings and track min/max"""
    global latest_sensor_data, max_temperature, max_pressure, max_timestamp
    global min_temperature, min_pressure, min_timestamp, logging_active, log_data
    
    try:
        temp = bmp280.temperature
        pressure = bmp280.pressure
        altitude = bmp280.altitude
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        latest_sensor_data['temperature'] = temp
        latest_sensor_data['pressure'] = pressure
        latest_sensor_data['altitude'] = altitude
        latest_sensor_data['last_update'] = timestamp
        
        # Update max values
        if temp > max_temperature:
            max_temperature = temp
            max_timestamp = timestamp
            
        if pressure > max_pressure:
            max_pressure = pressure
            
        # Update min values
        if temp < min_temperature:
            min_temperature = temp
            
        if pressure < min_pressure:
            min_pressure = pressure
            min_timestamp = timestamp
            
        # Log data if logging is active
        if logging_active:
            log_entry = {
                'timestamp': timestamp,
                'temperature': temp,
                'pressure': pressure,
                'altitude': altitude
            }
            log_data.append(log_entry)
            
    except Exception as e:
        print(f"Sensor error: {e}")
        latest_sensor_data['temperature'] = get_cpu_temperature()
        latest_sensor_data['pressure'] = 0
        latest_sensor_data['altitude'] = 0
        latest_sensor_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def display_on_lcd(text_line1, text_line2=""):
    """Display text on LCD with proper formatting"""
    lcd.clear()
    line1 = text_line1[:16]
    line2 = text_line2[:16]
    lcd.write_string(line1)
    if text_line2:
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2)

def display_name_lab():
    """Display name and lab number on LCD"""
    display_on_lcd("Cheane Nurse", "ECET3710 Lab 12")

def display_datetime():
    """Display current date and time on LCD"""
    now = datetime.now()
    date_str = now.strftime("%m/%d/%Y")
    time_str = now.strftime("%H:%M:%S")
    display_on_lcd(date_str, time_str)

def display_ip_address():
    """Display WiFi IP address on LCD"""
    ip = get_wifi_ip()
    display_on_lcd("WiFi IP:", ip)

def display_pressure_temp():
    """Display pressure and temperature on LCD"""
    update_sensor_readings()
    temp = latest_sensor_data['temperature']
    pressure = latest_sensor_data['pressure']
    display_on_lcd(f"T:{temp:.1f}C", f"P:{pressure:.1f}hPa")

def start_logging():
    """Start data logging"""
    global logging_active, log_data
    logging_active = True
    log_data = []  # Clear previous log data
    display_on_lcd("Logging Started", datetime.now().strftime("%H:%M:%S"))
    info("Logging Started", "Sensor data will now be logged to file when stop is pressed")

def stop_logging_and_save():
    """Stop logging and save data to file with header"""
    global logging_active, log_data
    logging_active = False
    
    if log_data:
        try:
            with open(log_file, 'w', newline='') as file:
                writer = csv.writer(file)
                
                writer.writerow(['ECET3710 Lab 12 - Sensor Data Log'])
                writer.writerow(['Student: Cheane Nurse'])
                writer.writerow(['Date/Time Created:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([]) 
                writer.writerow(['Timestamp', 'Temperature (C)', 'Pressure (hPa)', 'Altitude (m)'])
                
                for entry in log_data:
                    writer.writerow([
                        entry['timestamp'],
                        f"{entry['temperature']:.2f}",
                        f"{entry['pressure']:.2f}",
                        f"{entry['altitude']:.2f}"
                    ])
            
            display_on_lcd(f"Saved {len(log_data)}", "records to file")
            info("Logging Stopped", f"Data saved to {log_file}\n{len(log_data)} records")
        except Exception as e:
            info("Error", f"Failed to save log: {str(e)}")
    else:
        display_on_lcd("No data logged", "")
        info("Logging Stopped", "No data was logged")

def display_maximum():
    """Display maximum pressure and temperature with time/date on LCD"""
    update_sensor_readings()
    max_info = f"Max T:{max_temperature:.1f}C"
    max_info2 = f"Max P:{max_pressure:.1f}hPa"
    display_on_lcd(max_info, max_info2)
    
    
    def show_details():
        time.sleep(5)
        display_on_lcd(f"Time: {max_timestamp[:10]}", f"Date: {max_timestamp[11:19]}")
        time.sleep(3)
        display_on_lcd("Max Values", "Press button again")
    
    threading.Thread(target=show_details, daemon=True).start()

def display_minimum():
    """Display minimum pressure and temperature with time/date on LCD"""
    update_sensor_readings()
    min_info = f"Min T:{min_temperature:.1f}C"
    min_info2 = f"Min P:{min_pressure:.1f}hPa"
    display_on_lcd(min_info, min_info2)
    
    def show_details():
        time.sleep(5)
        display_on_lcd(f"Time: {min_timestamp[:10]}", f"Date: {min_timestamp[11:19]}")
        time.sleep(3)
        display_on_lcd("Min Values", "Press button again")
    
    threading.Thread(target=show_details, daemon=True).start()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ECET3710 Lab 12 - Sensor Monitor & Data Logging</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        h2 {
            color: #764ba2;
            margin-top: 20px;
        }
        .info-card {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
        }
        .sensor-data {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .sensor-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s;
        }
        .sensor-card:hover {
            transform: translateY(-5px);
        }
        .sensor-value {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }
        .sensor-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .button-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .btn:active {
            transform: translateY(0);
        }
        .btn-danger {
            background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
        }
        .btn-success {
            background: linear-gradient(135deg, #48bb78 0%, #276749 100%);
        }
        .btn-info {
            background: linear-gradient(135deg, #4299e1 0%, #2b6cb0 100%);
        }
        .minmax-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .minmax-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .minmax-card {
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .minmax-card.max {
            background: #fff3e0;
            border-left: 4px solid #ed8936;
        }
        .minmax-card.min {
            background: #e0f2fe;
            border-left: 4px solid #4299e1;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌡️ ECET3710 Lab 12 - Raspberry Pi Sensor Monitor & Data Logging</h1>
        <h3>Cheane Nurse - Hardware Programming</h3>
        
        <div class="info-card">
            <strong>📋 Lab Information:</strong><br>
            <strong>Name:</strong> Cheane Nurse<br>
            <strong>Lab:</strong> ECET3710 Lab 12<br>
            <strong>Current Time:</strong> <span id="currentTime"></span><br>
            <strong>🌐 WiFi IP Address:</strong> {{ ip }}<br>
            <strong>📊 Logging Status:</strong> 
            <span class="status" id="logStatus">
                {{ "Active" if logging_active else "Inactive" }}
            </span>
        </div>
        
        <h2>Live Sensor Readings</h2>
        <div class="sensor-data">
            <div class="sensor-card">
                <div class="sensor-label">🌡️ Temperature</div>
                <div class="sensor-value" id="temperature">{{ "%.1f"|format(temp) }}°C</div>
            </div>
            <div class="sensor-card">
                <div class="sensor-label">📊 Pressure</div>
                <div class="sensor-value" id="pressure">{{ "%.1f"|format(pressure) }} hPa</div>
            </div>
            <div class="sensor-card">
                <div class="sensor-label">⛰️ Altitude</div>
                <div class="sensor-value" id="altitude">{{ "%.1f"|format(altitude) }} m</div>
            </div>
        </div>
        
        <h2>Control Buttons</h2>
        <div class="button-grid">
            <button class="btn" onclick="sendCommand('name_lab')">📝 Display Name & Lab</button>
            <button class="btn" onclick="sendCommand('datetime')">📅 Display Date/Time</button>
            <button class="btn" onclick="sendCommand('ip')">🌐 Display IP Address</button>
            <button class="btn" onclick="sendCommand('pressure_temp')">📊 Display P & T</button>
            <button class="btn btn-success" onclick="sendCommand('start_logging')">▶️ Start Logging</button>
            <button class="btn btn-danger" onclick="sendCommand('stop_logging')">⏹️ Stop Logging</button>
            <button class="btn btn-info" onclick="sendCommand('max')">📈 Show Maximum</button>
            <button class="btn btn-info" onclick="sendCommand('min')">📉 Show Minimum</button>
        </div>
        
        <div class="minmax-section">
            <h3>📊 Min/Max Values (Since Program Start)</h3>
            <div class="minmax-grid">
                <div class="minmax-card max">
                    <strong>📈 MAXIMUM</strong><br>
                    Temperature: <span id="maxTemp">{{ "%.1f"|format(max_temp) }}°C</span><br>
                    Pressure: <span id="maxPress">{{ "%.1f"|format(max_press) }} hPa</span><br>
                    <small>Recorded: <span id="maxTime">{{ max_timestamp }}</span></small>
                </div>
                <div class="minmax-card min">
                    <strong>📉 MINIMUM</strong><br>
                    Temperature: <span id="minTemp">{{ "%.1f"|format(min_temp) }}°C</span><br>
                    Pressure: <span id="minPress">{{ "%.1f"|format(min_press) }} hPa</span><br>
                    <small>Recorded: <span id="minTime">{{ min_timestamp }}</span></small>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Raspberry Pi 5 | I2C BMP280 Sensor | I2C LCD Display | Data Logging to CSV</p>
            <p>Last Update: <span id="lastUpdate">{{ last_update }}</span></p>
        </div>
    </div>
    
    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('currentTime').innerHTML = now.toLocaleString();
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        function sendCommand(command) {
            fetch('/command/' + command)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        console.log('Command executed:', command);
                    }
                    if (data.logging_status) {
                        const statusSpan = document.getElementById('logStatus');
                        statusSpan.innerHTML = data.logging_status === 'active' ? 'Active' : 'Inactive';
                        statusSpan.className = 'status ' + (data.logging_status === 'active' ? 'status-active' : 'status-inactive');
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        function fetchSensorData() {
            fetch('/sensor_data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('temperature').innerHTML = data.temperature.toFixed(1) + '°C';
                    document.getElementById('pressure').innerHTML = data.pressure.toFixed(1) + ' hPa';
                    document.getElementById('altitude').innerHTML = data.altitude.toFixed(1) + ' m';
                    document.getElementById('maxTemp').innerHTML = data.max_temp.toFixed(1) + '°C';
                    document.getElementById('maxPress').innerHTML = data.max_press.toFixed(1) + ' hPa';
                    document.getElementById('minTemp').innerHTML = data.min_temp.toFixed(1) + '°C';
                    document.getElementById('minPress').innerHTML = data.min_press.toFixed(1) + ' hPa';
                    document.getElementById('maxTime').innerHTML = data.max_timestamp;
                    document.getElementById('minTime').innerHTML = data.min_timestamp;
                    document.getElementById('lastUpdate').innerHTML = data.last_update;
                })
                .catch(error => console.error('Error:', error));
        }
        
        setInterval(fetchSensorData, 3000);
        fetchSensorData();
    </script>
</body>
</html>
"""

@flask_app.route('/')
def index():
    """Serve the main webpage"""
    update_sensor_readings()
    return render_template_string(HTML_TEMPLATE,
                                ip=get_wifi_ip(),
                                temp=latest_sensor_data['temperature'],
                                pressure=latest_sensor_data['pressure'],
                                altitude=latest_sensor_data['altitude'],
                                logging_active=logging_active,
                                max_temp=max_temperature,
                                max_press=max_pressure,
                                min_temp=min_temperature,
                                min_press=min_pressure,
                                max_timestamp=max_timestamp,
                                min_timestamp=min_timestamp,
                                last_update=latest_sensor_data['last_update'])

@flask_app.route('/command/<cmd>')
def handle_command(cmd):
    """Handle button commands from webpage"""
    global logging_active
    response = {'status': 'success', 'command': cmd}
    
    if cmd == 'name_lab':
        display_name_lab()
    elif cmd == 'datetime':
        display_datetime()
    elif cmd == 'ip':
        display_ip_address()
    elif cmd == 'pressure_temp':
        display_pressure_temp()
    elif cmd == 'start_logging':
        start_logging()
        response['logging_status'] = 'active'
    elif cmd == 'stop_logging':
        stop_logging_and_save()
        response['logging_status'] = 'inactive'
    elif cmd == 'max':
        display_maximum()
    elif cmd == 'min':
        display_minimum()
    
    return jsonify(response)

@flask_app.route('/sensor_data')
def sensor_data():
    """Return current sensor data as JSON"""
    update_sensor_readings()
    return jsonify({
        'temperature': latest_sensor_data['temperature'],
        'pressure': latest_sensor_data['pressure'],
        'altitude': latest_sensor_data['altitude'],
        'max_temp': max_temperature,
        'max_press': max_pressure,
        'min_temp': min_temperature,
        'min_press': min_pressure,
        'max_timestamp': max_timestamp,
        'min_timestamp': min_timestamp,
        'last_update': latest_sensor_data['last_update']
    })

def run_flask():
    """Run Flask web server"""
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def create_gui():
    """Create the GUI application"""
    app = App("ECET3710 Lab 12 - Sensor Display & Data Logging", width=550, height=750, layout="grid")
    
    title_box = Box(app, grid=[0, 0, 2, 1], width="fill")
    Text(title_box, text="ECET3710 Lab 12 - Sensor Control Panel", size=16, font="Arial")
    
    info_box = Box(app, grid=[0, 1, 2, 1], width="fill")
    Text(info_box, text="Cheane Nurse - Lab 12", size=12)
    
   
    buttons = [
        (" Display Name & Lab", display_name_lab, 0, 2),
        (" Display Date & Time", display_datetime, 1, 2),
        (" Display IP Address", display_ip_address, 0, 3),
        (" Display Pressure & Temp", display_pressure_temp, 1, 3),
        (" Start Data Logging", start_logging, 0, 4),
        (" Stop & Save Log", stop_logging_and_save, 1, 4),
        (" Show Maximum Values", display_maximum, 0, 5),
        (" Show Minimum Values", display_minimum, 1, 5),
    ]
    
    for btn_text, btn_command, col, row in buttons:
        PushButton(app, text=btn_text, command=btn_command, grid=[col, row], width=27, height=2)
    
    status_box = Box(app, grid=[0, 6, 2, 1], width="fill")
    status_text = Text(status_box, text="Ready - Click buttons to display information on LCD", size=10)
    
    note_box = Box(app, grid=[0, 7, 2, 1], width="fill")
    Text(note_box, text="💡 Web server running at http://" + get_wifi_ip() + ":5000", size=9, color="#666")
    Text(note_box, text="📁 Data logs saved to sensor_log.csv", size=9, color="#666")
    
    app.display()

if __name__ == "__main__":
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    ip = get_wifi_ip()
    print(f"\n{'='*50}")
    print(f"Web server running at: http://{ip}:5000")
    print(f"Data log file: {os.path.abspath(log_file)}")
    print(f"{'='*50}\n")
    
 
    webbrowser.open(f"http://{ip}:5000")
    
  
    create_gui()