import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# CHANGE '17' TO WHICHEVER GPIO PIN YOU USED
BUTTON_PIN = 17 

# Setup the pin with an internal Pull-Up Resistor
# This creates a "default" state of HIGH (3.3V)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Press the arcade button...")

try:
    while True:
        # We look for 0 (False) because pressing the button connects it to Ground
        if GPIO.input(BUTTON_PIN) == 0:
            print("Button Pressed!")
            time.sleep(0.2) # Small delay to prevent double-counting

except KeyboardInterrupt:
    GPIO.cleanup()
