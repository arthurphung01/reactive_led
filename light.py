"""
Audio-Reactive LED Strip Control for Raspberry Pi 5

This script captures audio from the Raspberry Pi's microphone, processes it to
extract the amplitude (volume), and sends commands to an LED strip connected
to the Pi to react to the audio.

Prerequisites:
1.  Raspberry Pi 5 with Raspberry Pi OS (Bullseye or later)
2.  Python 3.7 or later
3.  WS2812B LED strip connected to the Pi
4.  USB Microphone
5.  Libraries: sounddevice, numpy, rpi_ws281x

Installation:

1.  Ensure your Raspberry Pi is updated:
    sudo apt update
    sudo apt upgrade

2.  Install the necessary Python libraries:
    sudo apt install libportaudio2 libportaudiocpp0
    pip3 install sounddevice numpy

3.  Install rpi_ws281x:
    sudo apt install python3-rpi.gpio
    pip3 install rpi_ws281x

4.  Connect your LED strip to the Raspberry Pi.
    * For WS281x, connect to GPIO 18 (PWM).
    * Ensure proper power supply for your LED strip!  The Raspberry Pi
        cannot directly power large numbers of LEDs.  A separate 5V power
        supply is essential.

Configuration:

* LED Strip Type:  Choose  'WS281x' (for WS2811/WS2812B/NeoPixel).
* Number of LEDs:  Set the `LED_COUNT` variable.
* Audio Device:  Adjust `audio_device_index` if necessary.  Use
    `python3 -m sounddevice` to list available audio devices.
* Sensitivity: Adjust `SENSITIVITY` to control how much the LEDs react
    to the audio.
* Color Mapping:  The `calculate_color` function maps audio amplitude to
    LED colors.  You can customize this for different color effects.

Running the Script:

1.  Save the code to a file, e.g., `audio_reactive_leds.py`.
2.  Run the script from the terminal:
    python3 audio_reactive_leds.py

Troubleshooting:

* No sound:  Check your microphone connection and ensure it's not muted.
    Use `python3 -m sounddevice` to verify the microphone is detected
    and to find its index.
* LEDs not lighting up:  Double-check your wiring, power supply, and
    LED strip type.  Make sure you've installed the correct libraries.
* "ALSA lib pcm.c:..." errors:  These are often harmless but can be
    suppressed by adding "options snd-usb-audio index=-2" to
    `/etc/modprobe.d/alsa-base.conf` (create the file if it doesn't exist)
    and then rebooting.
* Script needs to be run as root: If you get errors about permissions
    accessing hardware, try running the script with `sudo python3 ...`.
"""

import sounddevice as sd
import numpy as np
import time

# Configuration
LED_COUNT = 30  # Number of LEDs in your strip
LED_TYPE = 'WS281x'  #  'WS281x'
AUDIO_DEVICE_INDEX = None  # Use None for default microphone, or specify the device index
SENSITIVITY = 100  # Adjust to make the LEDs more or less sensitive to sound

if LED_TYPE == 'WS281x':
    import rpi_ws281x
    # WS281x LED strip configuration:
    LED_PIN = 18  # GPIO pin connected to the LED data line (PWM!)
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (800kHz is typical)
    LED_DMA = 10  # DMA channel for transfers (try 5 or 10)
    LED_BRIGHTNESS = 255  # Set maximum brightness (0 to 255)
    LED_INVERT = False  # True to invert the signal (if needed)
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
elif LED_TYPE == 'Blinkt':
    import blinkt
    blinkt.set_clear_on_exit()  # Clear LEDs when the script exits
else:
    print("Error: Invalid LED_TYPE.  Choose 'WS281x' or 'Blinkt'.")
    exit()

def calculate_color(amplitude):
    """
    Maps audio amplitude to an RGB color.  This function can be customized
    to create different color patterns.

    Args:
        amplitude: The audio amplitude (a value between 0 and some maximum).

    Returns:
        A tuple (r, g, b) representing the color.
    """
    # Example: Map amplitude to a color gradient (blue -> green -> red)
    if amplitude < SENSITIVITY / 3:
        r = 0
        g = int(255 * amplitude / (SENSITIVITY / 3))
        b = 255 - g
    elif amplitude < 2 * SENSITIVITY / 3:
        r = int(255 * (amplitude - SENSITIVITY / 3) / (SENSITIVITY / 3))
        g = 255
        b = 0
    else:
        r = 255
        g = 255 - int(255 * (amplitude - 2 * SENSITIVITY / 3) / (SENSITIVITY / 3))
        b = 0
    return r, g, b

def set_leds(led_data):
    """
    Sets the colors of the LEDs.

    Args:
        led_data: A list of RGB tuples, one for each LED.
    """
    if LED_TYPE == 'WS281x':
        for i, color in enumerate(led_data):
            r, g, b = color
            # Convert RGB to WS281x color format (GRB)
            led_strip.setPixelColor(i, rpi_ws281x.Color(g, r, b))
        led_strip.show()
    elif LED_TYPE == 'Blinkt':
        for i, color in enumerate(led_data):
            r, g, b = color
            blinkt.set_pixel(i, r, g, b)
        blinkt.show()

def audio_callback(indata, frames, time, status):
    """
    Callback function for the sounddevice audio stream.  This function
    is called whenever a new chunk of audio data is available.

    Args:
        indata:  The audio data as a numpy array.
        frames:  The number of frames in the audio data.
        time:    A sounddevice.CallbackTime object (not used here).
        status:  A sounddevice.CallbackFlags object (checks for errors).
    """
    if status:
        print(f"Error in audio stream: {status}")
        return

    # Calculate the amplitude of the audio data.  We use the RMS (root mean
    # square) of the audio signal as a measure of its loudness.
    amplitude = np.sqrt(np.mean(indata**2))
    # print(f"Amplitude: {amplitude}") #for debugging

    # Calculate LED colors based on the amplitude.
    led_colors = []
    for _ in range(LED_COUNT):
        led_colors.append(calculate_color(amplitude))

    # Set the LED colors.
    set_leds(led_colors)

if __name__ == '__main__':
    try:
        # Initialize the LED strip.
        if LED_TYPE == 'WS281x':
            # Create the LED strip object.
            led_strip = rpi_ws281x.Adafruit_NeoPixel(
                LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT,
                LED_BRIGHTNESS, LED_CHANNEL
            )
            # Intialize the library (must be called once before using).
            led_strip.begin()
            print("WS281x LED strip initialized.")
        elif LED_TYPE == 'Blinkt':
            blinkt.set_brightness(0.5)  # Adjust brightness as needed (0.0 to 1.0)
            print("Blinkt! LED strip initialized.")

        # Open an audio input stream.
        with sd.InputStream(
            device=AUDIO_DEVICE_INDEX,
            channels=1,  # Mono audio
            dtype='float32',  # Important: Use float32 for audio processing
            callback=audio_callback,
        ):
            print("Listening for audio... Press Ctrl+C to stop.")
            # Keep the script running until Ctrl+C is pressed.
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up: Turn off LEDs.
        if LED_TYPE == 'WS281x':
            for i in range(LED_COUNT):
                led_strip.setPixelColor(i, rpi_ws281x.Color(0, 0, 0))
            led_strip.show()
        elif LED_TYPE == 'Blinkt':
            blinkt.clear()
            blinkt.show()
        print("LEDs cleared and program exited.")
