import os
import glob
import time
import boto3
import threading

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

#Open file containing the recorded temperatures
base_dir = '/sys/bus/w1/devices/'
therm_folder = glob.glob(base_dir + '28*')[0] 
therm_file = therm_folder + '/w1_slave' 

class MyDb(object):

	def __init__(self, Table_Name='DS18'):

		self.Table_Name=Table_Name
		self.db = boto3.resource('dynamodb')
		self.table = self.db.Table(Table_Name)
		self.client = boto3.client('dynamodb')

	@property
	def get(self):

		response = self.table.get_item(
			Key = {
				'Sensor_Id':"1"
			}
		)	
		return response
	
	#put meta
	def put(self, Sensor_Id='' , dCelsius='', dFahrenheit=''):
		{self.table.put_item(
			Item={
				'Sensor_Id':Sensor_Id,
				'dCelsius':dCelsius,
				'dFahrenheit':dFahrenheit
			}
		)}
	"""
	def delete(self, Sensor_Id=''):
		self.table.delete_item(
			Key={
				'Sensor_Id': Sensor_Id
			}
		)
	"""
	def describe_table(self):
		response = self.client.describe_table(
			TableName='Sensor'
		)
		return response
    

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

def main():
    global counter
    threading.Timer(interval=10, function=main).start()			
    obj = MyDb()
    obj.put(Sensor_Id=str(counter), dCelsius = str(celsius()), dFahrenheit = str(fahrenheit()))
    counter = counter + 1
    print ("Uploaded to dynamodb C:{},F:{} ".format(celsius(), fahrenheit()))

if __name__ == "__main__":
    global counter
    counter = 0
    main()