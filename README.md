
This project is used to be an introduction to the platform of programming sensors to track and display data. 
This can be applied to vast amounts of applications, and notably for ECET students, which will be implemented into our senior design project. 
This specific project involves incorporating the BMP280 Barometric Pressure and Temperature sensor along with python code, to create an interface that logs and records data. 





This project is comprised of a Raspberry Pi 5, an LCD display, and the BMP280 sensor. 
Each device individually has an SDA (Software Defined Access) and SCL (Serial Clock) 
port that are connected to each other with a series of female to male connector wires. 
The code is organized into three main functional layers: hardware interfacing, data management, 
and user interface. The hardware layer initializes and communicates with the BMP280 sensor 
and LCD display using the smbus2, adafruit_bmp280, and RPLCD.i2c libraries. 
The data management layer maintains variables for sensor readings, min/max tracking, 
and data logging, with the update_sensor_readings() function serving as the central routine 
that reads sensor data, updates min/max values, and adds to the log when active. 
The user interface layer provides three access methods: a GUI built with guizero for local control, 
a Flask web server with HTML/CSS/JavaScript for remote access, and direct LCD display functions. 
The Flask routes (/, /command/<cmd>, /sensor_data) handle, button commands, and AJAX data updates . 
Threading is used to run the Flask server along with the GUI, preventing blocking.
This organization separates discrepancies , making the code maintainable 
while enabling simultaneous local and remote control of all.
