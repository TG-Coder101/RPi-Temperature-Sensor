import os
import glob
import time

#Open file containing the recorded temperatures
base_dir = '/sys/bus/w1/devices/'
therm_folder = glob.glob(base_dir + '28*')[0] 
therm_file = therm_folder + '/w1_slave' 

def read_temperature():
	f = open(therm_file, 'r')
	temps = f.readlines()
	f.close()
	
	return temps

#Convert temperature into Celsius
def celsius():
	temps = read_temperature()
	while temps[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		temps = read_temperature()
	equals_pos = temps[1].find('t=')	
	if equals_pos != -1:
		temp_string = temps[1][equals_pos+2:]
		temp_c = int(temp_string) / 1000.0 #Temp string is the sensor output, make sure its an integer to do the math
		temp_c = str(round(temp_c, 1)) #Round the result to 1 place after the decimal, then convert it to a string
		return temp_c

#Convert temperature into Fahrenheit
def fahrenheit():
	temps = read_temperature()
	while temps[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		temps = read_temperature()
	equals_pos = temps[1].find('t=')	
	if equals_pos != -1:
		temp_string = temps[1][equals_pos+2:]
		temp_f = int(temp_string) / 1000.0 * 9.0 / 5.0 + 32.0 #Temp string is the sensor output
		temp_f = str(round(temp_f, 1))
		return temp_f

while True:
	buttonPressed = open('/dev/tempchar').read(1)[0]
	print (buttonPressed)
	if buttonPressed == 1:
		while True:
			try:
				print (celsius())
				print (fahrenheit())
			except KeyboardInterrupt:
				break  