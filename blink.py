from gpiozero import LED
from signal import pause

# CHANGE THIS to the GPIO pin number connected to the positive side prong
led_pin = 3 

# Setup the LED
arcade_light = LED(led_pin)

print(f"Blinking LED on GPIO {led_pin}...")
print("Press Ctrl+C to stop.")

# The blink function takes two arguments:
# on_time: How long the light stays ON (in seconds)
# off_time: How long the light stays OFF (in seconds)
arcade_light.blink(on_time=0.5, off_time=0.5)

# Keep the program running so the blinking continues
pause()
