import pygame
from picamera import PiCamera
from time import sleep
from fractions import Fraction
import time
from pynput import keyboard
import os
import sys
import shutil

from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from gpiozero.tools import sin_values

tb = TonalBuzzer(21)
def play(tune):
    for note, duration in tune:
        #print(note)
        tb.play(note)
        sleep(float(duration))
    tb.stop()

beep = [('Bb4', 0.05)]
bloop = [('C4', 0.05)]

# Thermal Printer Stuff:
from lib.Adafruit_Thermal import *
printer = Adafruit_Thermal("/dev/serial0", 19200, timeout=5)

# E-ink Display Stuff
from lib.waveshare_epd import epd4in2
display = epd4in2.EPD()
screenSize = (400,300)
screenOffset = 0

from PIL import Image,ImageDraw,ImageFont

# Camera Stuff
camera = PiCamera(
    resolution=(800, 600))

# Variable Defaults
slideshowArray = []
slideshowLength = 0
currentImage = 0
currentImageName = "NA"
destinationDir = '/home/pi/Desktop/digital-polaroid-camera/gallery/bw'
sourceDir = '/home/pi/Desktop/digital-polaroid-camera/gallery'

def updateSlideshowList():
    global currentImage
    global currentImageName
    global slideshowLength
    
    slideshowArray.clear()
    list = ['.th.']

    for filename in os.listdir(sourceDir):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            if any([x in filename for x in list]):
                print("skipping thumbnail")
            else: 
                slideshowArray.append(sourceDir+'/'+filename)
        else:
            continue

    slideshowArray.sort()
    slideshowLength = len(slideshowArray)
    currentImageName = slideshowArray[slideshowLength-1]
    updateDisplay(currentImageName)

def updateDisplay(imagePath):
    global display
    print(imagePath)
    image = Image.new(mode='1', size=(w, h), color=255)
    draw = ImageDraw.Draw(image)
    time.sleep(3) # Pause for 3 seconds.
    newImage = Image.open(imagePath)
    newImage = newImage.resize(screenSize, Image.ANTIALIAS)
    newImage = newImage.transpose(Image.ROTATE_180)
    image.paste(newImage, (screenOffset, 0))
    display.display(display.getbuffer(image)) # Update display

display.init()
display.Clear()
w = display.width
h = display.height
updateSlideshowList()

def nextImage():
    global currentImage
    global currentImageName
    global slideshowLength
    currentImage=currentImage+1
    if currentImage >= slideshowLength:
        currentImage = 0
    currentImageName = slideshowArray[currentImage]
    updateDisplay(slideshowArray[currentImage])

def previousImage():
    global currentImage
    global slideshowLength
    global currentImageName
    currentImage=currentImage-1
    if currentImage <= -1:
        currentImage = slideshowLength-1
    currentImageName = slideshowArray[currentImage]
    updateDisplay(slideshowArray[currentImage])

def takePicture():
    global camera
    print("taking a picture...")
    timestr = time.strftime("%Y%m%d-%H%M%S")
    camera.resolution = (2480, 1860) # I get an error at sizes above this!
    camera.capture(sourceDir + '/' + timestr +'.jpg')
    updateSlideshowList()
    convertImage(sourceDir + '/' + timestr +'.jpg')
    play(beep)
    print("Photo complete.")

def convertImage(imagePath):
    outputName = "bw"+os.path.basename(imagePath)
    print("converting image...")
    os.system("convert "+ imagePath + " -rotate 90 -resize 384 -dither FloydSteinberg -remap pattern:gray50 /home/pi/Desktop/digital-polaroid-camera/gallery/bw/"+outputName)
    # os.system("convert "+ imagePath + " -rotate 90 -brightness-contrast 30x50 -resize 384 -dither FloydSteinberg -remap pattern:gray50 /home/pi/Desktop/digital-polaroid-camera/gallery/bw/"+outputName)

    printerFileName = outputName.replace(".jpg", "") # remove .jpg from file name
    printerFileName = printerFileName.replace("-", "") # remove dashes
    os.system("/home/pi/cttp/cttp.rb /home/pi/Desktop/digital-polaroid-camera/gallery/bw/"+outputName+" -o --output /home/pi/Desktop/digital-polaroid-camera/gallery/"+printerFileName+".py -i -a")

def printPhoto(imageName):
    print ('sending to printer...')
    printableFileName = "bw"+os.path.basename(imageName)
    printerFileName = printableFileName.replace(".jpg", "") # remove .jpg from file name (the ".py" isn't needed)
    printerFileName = printerFileName.replace("-", "") # remove .jpg from file name (the ".py" isn't needed)
    printer.wake()       # Call wake() before printing again, even if reset
    print(printerFileName)
    photoSource = __import__("gallery."+printerFileName)
    width = eval("photoSource."+printerFileName+".width")
    height = eval("photoSource."+printerFileName+".height")
    imageData = eval("photoSource."+printerFileName+".data")
    printer.printBitmap(width, height, imageData)
    printer.sleep()      # Tell printer to sleep
    printer.setDefault() # Restore printer to defaults

def deletePhoto():
    # Note: This doesn't actually delete the photo, it just moves it to a folder called "trash" so it doesn't appear in the slideshow
    # Note: Need to move all 3 versions of the image
    # 1. Full size Image:
    fileName = currentImageName.replace("/home/pi/Desktop/digital-polaroid-camera/gallery/", "") # strip path out
    shutil.move(currentImageName, sourceDir + "/trash/"+ fileName)
    # 2. BW jpg:
    shutil.move(sourceDir + "/bw/bw" + fileName, sourceDir + "/trash/bw"+ fileName)
    # 3. Python printable file:
    pyFilename = fileName.replace(".jpg", ".py") # remove .jpg from file name
    pyFilename = pyFilename.replace("-", "") # remove dash
    shutil.move(sourceDir+ "/bw" + pyFilename, sourceDir + "/trash/"+ pyFilename)
    updateSlideshowList()

def feedPaper():
    printer.wake()       # Call wake() before printing again, even if reset
    printer.feed()
    printer.sleep()      # Tell printer to sleep

def on_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(
            key.char))
    except AttributeError:
        print('special key {0} pressed'.format(
            key))

pygame.init()
done = False

# Initialize the joysticks.
pygame.joystick.init()

# -------- Main Program Loop -----------
while not done:
    #
    # EVENT PROCESSING STEP
    #
    # Possible joystick actions: JOYAXISMOTION, JOYBALLMOTION, JOYBUTTONDOWN,
    # JOYBUTTONUP, JOxxYHATMOTION
    for event in pygame.event.get(): # User did something.
        if event.type == pygame.QUIT: # If user clicked close.
            done = True # Flag that we are done so we exit this loop.
#         elif event.type == pygame.JOYBUTTONDOWN:
#             print("Joystick button pressed.")
#         elif event.type == pygame.JOYBUTTONUP:
#             print("Joystick button released.")

        # print(event)
        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 2:
                print("B button pressed")
                play(beep)
                printPhoto(currentImageName)
            
            elif event.button == 1:
                print("A button pressed")
                takePicture()
                play(bloop)

            elif event.button == 8:
                print("Select button pressed")
                
            elif event.button == 9:
                print("Start button pressed")
                
            elif event.button == 3:
                print("y button pressed")
                play(beep)
                display.Clear()

            elif event.button == 0:
                print("x button pressed")
                play(beep)
                deletePhoto()
                
        elif event.type == pygame.JOYBUTTONUP:
            print(event.button, " button released.")

        elif event.type == pygame.JOYAXISMOTION:
            play(beep)
            if event.axis == 1 and event.value < 0:
                print("Up")

            elif event.axis == 1 and event.value == 1:
                print("down")
                feedPaper()

            elif event.axis == 0 and event.value < 0:
                print("left")
                previousImage()
                
            elif event.axis == 0 and event.value == 1:
                print("right")
                nextImage()

    # Get count of joysticks.
    joystick_count = pygame.joystick.get_count()

    # For each joystick:
    for i in range(joystick_count):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()

        try:
            jid = joystick.get_instance_id()
        except AttributeError:
            # get_instance_id() is an SDL2 method
            jid = joystick.get_id()

        # Get the name from the OS for the controller/joystick.
        name = joystick.get_name()

# Close the window and quit.
# If you forget this line, the program will 'hang'
# on exit if running from IDLE.
pygame.quit()