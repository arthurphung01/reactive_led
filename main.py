import sounddevice as sd
import numpy as np
import rpi_ws281x as ws
import time
import threading

class AudioVisualizer:
    """
    A class that encapsulates the functionality for audio-reactive LED control.
    """
    def __init__(self, led_count, led_pin, led_freq_hz, led_dma, led_invert,
                 led_brightness, led_channel, led_strip,
                 sample_rate, chunk_size, min_db, max_db, sensitivity):
        """
        Initializes the AudioVisualizer object.

        Args:
            led_count (int): Number of LEDs in the strip.
            led_pin (int): GPIO pin connected to the LED strip.
            led_freq_hz (int): LED signal frequency.
            led_dma (int): DMA channel for transfers.
            led_invert (bool): Set to True if using a level shifter.
            led_brightness (int): Initial brightness (0-255).
            led_channel (int): Channel 0 or 1.
            led_strip (int): Strip type (e.g., ws.WS2811_STRIP_GRB).
            sample_rate (int): Samples per second.
            chunk_size (int): Number of audio samples per chunk.
            min_db (int): Minimum decibel level to register sound.
            max_db (int): Maximum decibel level.
            sensitivity (int): Adjust to change LED reactivity.
        """
        # LED strip configuration
        self.led_count = led_count
        self.led_pin = led_pin
        self.led_freq_hz = led_freq_hz
        self.led_dma = led_dma
        self.led_invert = led_invert
        self.led_brightness = led_brightness
        self.led_channel = led_channel
        self.led_strip = led_strip

        # Sound capture parameters
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.min_db = min_db
        self.max_db = max_db
        self.sensitivity = sensitivity

        # Global variables
        self.strip = None
        self.audio_data = []
        self.audio_event = threading.Event()
        self.running = True
        self.stream = None  # To store the audio stream object

    def get_decibel_level(self, audio_chunk):
        """
        Calculates the decibel level of an audio chunk.

        Args:
            audio_chunk (numpy.ndarray): Audio data.

        Returns:
            float: Decibel level.
        """
        if np.any(audio_chunk):
            p_ref = 20e-6
            rms = np.sqrt(np.mean(audio_chunk**2))
            if rms > 0:
                db = 20 * np.log10(rms / p_ref)
                return max(self.min_db, db)
            else:
                return self.min_db
        else:
            return self.min_db

    def map_brightness(self, db):
        """
        Maps decibel levels to brightness values.

        Args:
            db (float): Decibel level.

        Returns:
            int: Brightness value (0-255).
        """
        clamped_db = max(self.min_db, min(self.max_db, db))
        brightness = int((clamped_db - self.min_db) / (self.max_db - self.min_db) * 255)
        return brightness

    def audio_callback(self, indata, frames, time, status):
        """
        Callback function for the audio stream.

        Args:
            indata (numpy.ndarray): Audio data from the input device.
            frames (int): Number of frames in the audio chunk.
            time (cffi.CData): Time information (not used here).
            status (sounddevice.CallbackFlags): Status flags.
        """
        if status:
            print(f"Error in audio stream: {status}")
            return

        self.audio_data = indata.copy()
        self.audio_event.set()

    def update_leds(self):
        """
        Updates the LED strip based on the processed audio data.
        """
        while self.running:
            self.audio_event.wait()
            self.audio_event.clear()
            if not self.running:
                break

            if len(self.audio_data) > 0:
                db = self.get_decibel_level(self.audio_data[:, 0])
                brightness = self.map_brightness(db)

                for i in range(self.strip.numPixels()):
                    self.strip.setPixelColor(i, ws.Color(0, brightness, 0))
                self.strip.show()

    def run(self):
        """
        Initializes and runs the audio processing and LED control.
        """
        # Initialize the LED strip
        self.strip = ws.Adafruit_NeoPixel(self.led_count, self.led_pin, self.led_freq_hz,
                                            self.led_dma, self.led_invert, self.led_brightness,
                                            self.led_channel, self.led_strip)
        self.strip.begin()

        # Initialize and start the audio stream
        try:
            self.stream = sd.InputStream(callback=self.audio_callback, samplerate=self.sample_rate,
                                         blocksize=self.chunk_size, channels=1)
            self.stream.start()

            # Start the LED update thread
            led_thread = threading.Thread(target=self.update_leds)
            led_thread.daemon = True
            led_thread.start()

            print("Listening for audio... Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nStopping...")
            self.running = False
            self.audio_event.set()  # Ensure led_thread wakes up
            if self.stream:
                self.stream.stop()
                self.stream.close()
            # Turn off LEDs before exiting
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, ws.Color(0, 0, 0))
            self.strip.show()
            print("Exiting...")

if __name__ == "__main__":
    # Configuration
    led_count = 300
    led_pin = 18
    led_freq_hz = 800000
    led_dma = 10
    led_invert = False
    led_brightness = 255
    led_channel = 0
    led_strip = ws.WS2811_STRIP_GRB

    sample_rate = 44100
    chunk_size = 512
    min_db = 40
    max_db = 90
    sensitivity = 200

    # Create and run the audio visualizer
    visualizer = AudioVisualizer(led_count, led_pin, led_freq_hz, led_dma, led_invert,
                                 led_brightness, led_channel, led_strip,
                                 sample_rate, chunk_size, min_db, max_db, sensitivity)
    visualizer.run()
