try:
	#module imports
	import os
	import glob
	import argparse
	import time
	
	#other imports
	import adafruit_ssd1306
	import board
	import busio
	import boto3
	import digitalio
	import pyfiglet
	import RPi.GPIO as GPIO
	from PIL import Image, ImageDraw, ImageFont
	from termcolor import colored, cprint
	from pyfiglet import Figlet
	print ("Modules loaded")
except Exception as e:
	print ("Error {}".format(e))

"""
sensor.py
"""
__version__ = "0.2"

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

#LCD DISPLAY
WIDTH = 128
HEIGHT = 64
BORDER = 5

i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3c)

#Gimmick Title Art
def titleArt():

	f = Figlet(font="slant")
	cprint(colored(f.renderText('RPi Thermometer'), 'cyan'))
	print(r"""					By

	An Temperature Sensor with Cloud functionality

	Use -c for Celsius, -f for Fahrenheit, -d to upload data to DynamoDB
	""" )
	print ("    	Version ",__version__)
#dynamodb class
class MyDb(object):

	def __init__(self, Table_Name='DS18'):

		self.Table_Name=Table_Name
		self.db = boto3.resource('dynamodb', 
			region_name = 'us-east-1', 
			endpoint_url="https://dynamodb.us-east-1.amazonaws.com"
		)
		self.table = self.db.Table(Table_Name)

	@property
	def get(self):

		response = self.table.get_item(
			Key = {
				'Sensor_Id':"1"
			}
		)	
		return response
	
	#put meta
	def put(self, Sensor_Id='', dbCelsiusVal='', dbFahrenheitVal='',):
		self.table.put_item(
			Item={
				'id':Sensor_Id,
				'CelsiusVal':dbCelsiusVal,
				'FahrenheitVal':dbFahrenheitVal
			}
		)

	def describe_table(self):
		response = self.client.describe_table(
			TableName='DS18'
		)
		return response
#displays text on Adafruit LCD display   
def display_text(text):
	#Clear Display
	oled.fill(0)
	oled.show()

	image = Image.new("1", (oled.width, oled.height))

	#Get drawing object to draw on image
	draw = ImageDraw.Draw(image)

	#Draw white background
	draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

	#Draw smaller rectangle inside larger rectangle
	draw.rectangle(
		(BORDER, BORDER, oled.width - BORDER - 1, oled.height - BORDER - 1),
		outline=0,
		fill=0,
	)
	
	#Load font
	font = ImageFont.load_default()

	#Test Text
	(font_width, font_height) = font.getsize(text)
	draw.text(
		(oled.width // 2 - font_width // 2, oled.height // 2 - font_height // 2),
		text,
		font=font,
		fill=255,
	)

	#Display Text
	oled.image(image)
	oled.show()	

#Open file containing the recorded temperatures
base_dir = '/sys/bus/w1/devices/'
therm_folder = glob.glob(base_dir + '28*')[0] 
therm_file = therm_folder + '/w1_slave' 

def read_temperature():
	f = open(therm_file, 'r')
	temps = f.readlines()
	f.close()
	
	return temps
#Arguments for Argparse
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--celsius", help="output temperature in Celsius", action="store_true")
    parser.add_argument("-f", "--fahrenheit", help="output temperature in Fahrenheit", action="store_true") 
    parser.add_argument("-d", "--dynamo", help="upload temperatures to DynamoDb", action="store_true")
    return parser.parse_args()

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
#Main function
def main():
	
	args = parse_args()
	global counter

	GPIO.setmode(GPIO.BCM)
	#Assign GPIO pins
	ledR = 23
	ledY = 20
	ledB = 21
	GPIO.setup(ledR, GPIO.OUT)
	GPIO.setup(ledY, GPIO.OUT)
	GPIO.setup(ledB, GPIO.OUT)

	try:
		while True:
			#prints celsius
			if args.celsius:

				print(celsius()+u"\N{DEGREE SIGN}"+ "C")
				display_text(str(celsius())+u"\N{DEGREE SIGN}"+ "C")
				
				cTemp = float(celsius())
				if float(cTemp) >= 19 and float(cTemp) <= 23:
					GPIO.output(ledY, GPIO.HIGH)
					GPIO.output(ledB, GPIO.LOW)
					GPIO.output(ledR, GPIO.LOW)
				elif float(cTemp) < 19:
					GPIO.output(ledB, GPIO.HIGH)
					GPIO.output(ledY, GPIO.LOW)
					GPIO.output(ledR, GPIO.LOW)
				elif float(cTemp) > 24:
					GPIO.output(ledR, GPIO.HIGH)
					GPIO.output(ledB, GPIO.LOW)
					GPIO.output(ledY, GPIO.LOW)
			#prints fahrenheit
			elif args.fahrenheit:

				print(fahrenheit()+u"\N{DEGREE SIGN}"+ "F")
				display_text(str(fahrenheit())+u"\N{DEGREE SIGN}"+ "F")	

				fTemp = float(fahrenheit())
				if float(fTemp) >= 65 and float(fTemp) <= 75:
					GPIO.output(ledY, GPIO.HIGH)
					GPIO.output(ledB, GPIO.LOW)
					GPIO.output(ledR, GPIO.LOW)
				elif float(fTemp) < 64:
					GPIO.output(ledB, GPIO.HIGH)
					GPIO.output(ledY, GPIO.LOW)
					GPIO.output(ledR, GPIO.LOW)
				elif float(fTemp) > 76:
					GPIO.output(ledR, GPIO.HIGH)
					GPIO.output(ledB, GPIO.LOW)
					GPIO.output(ledY, GPIO.LOW)
			#uploads data to dynamodb
			elif args.dynamo:
				obj = MyDb()
				obj.put(Sensor_Id=str(counter), dbCelsiusVal = str(celsius()), dbFahrenheitVal = str(fahrenheit()))
				counter = counter + 1
				print ("Data uploaded to DynamoDB C: {} ".format(celsius()+u"\N{DEGREE SIGN}"+ "C"))
				print ("Data uploaded to DynamoDB F: {} ".format(fahrenheit()+u"\N{DEGREE SIGN}"+ "F"))
				time.sleep(1.0)
	
	except KeyboardInterrupt:
		GPIO.output(ledB, GPIO.LOW)
		GPIO.output(ledY, GPIO.LOW)
		GPIO.output(ledR, GPIO.LOW)
		GPIO.cleanup()		
	
if __name__ == "__main__":
	global counter
	counter = 0
	titleArt()
	main()	
