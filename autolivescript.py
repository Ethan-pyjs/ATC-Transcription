import pyaudio
import wave
import email, smtplib, ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import time
import speech_recognition as sr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class WebAudioStreamCapture:
    def __init__(self, email_settings, url, play_button_selector):
        self.email_settings = email_settings
        self.url = url
        self.play_button_selector = play_button_selector
        self.sample_rate = 44100
        self.channels = 2
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.duration = 30  # Recording duration in seconds
        self.recognizer = sr.Recognizer()
        self.driver = None

    def setup_browser(self):
        """Set up and launch browser with target URL"""
        print("Setting up browser...")
        options = webdriver.ChromeOptions()
        # Optional: Add arguments for headless mode if needed
        # options.add_argument('--headless')
        options.add_argument('--use-fake-ui-for-media-stream')  # Allow media access
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.get(self.url)
        
        try:
            # Wait for play button to be available
            play_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.play_button_selector))
            )
            # Click the play button
            play_button.click()
            print("Media playback started")
            # Give time for media to start playing
            time.sleep(2)
            return True
        except TimeoutException:
            print("Timeout waiting for play button")
            self.driver.quit()
            return False
        except Exception as e:
            print(f"Error starting media: {e}")
            self.driver.quit()
            return False

    def cleanup_browser(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def record_audio(self):
        """Record audio from system output"""
        try:
            print("Recording system audio...")
            p = pyaudio.PyAudio()

            # Find the loopback device (system audio)
            loopback_device_index = None
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if "Stereo Mix" in device_info["name"] or "What U Hear" in device_info["name"]:
                    loopback_device_index = i
                    break

            if loopback_device_index is None:
                print("Could not find loopback device. Please enable Stereo Mix or similar.")
                return None

            # Open stream
            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=loopback_device_index,
                frames_per_buffer=self.chunk
            )

            print("* recording")
            frames = []

            # Calculate how many chunks we need to read
            chunks_to_record = int((self.sample_rate * self.duration) / self.chunk)

            # Record audio
            for i in range(chunks_to_record):
                data = stream.read(self.chunk)
                frames.append(data)

            print("* done recording")

            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            p.terminate()

            # Save the recorded data as a WAV file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
            
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()

            print(f"Recording saved as {filename}")
            return filename

        except Exception as e:
            print(f"Error recording audio: {e}")
            return None

    def transcribe_audio(self, audio_file):
        """Convert speech to text"""
        try:
            print("Transcribing audio...")
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                return text
        except sr.UnknownValueError:
            return "Speech Recognition could not understand the audio"
        except sr.RequestError as e:
            return f"Could not request results from Speech Recognition service; {e}"
        except Exception as e:
            return f"Error during transcription: {e}"

    def send_email(self, audio_file, transcription):
        """Send email with audio attachment and transcription"""
        subject = "New Audio Recording with Transcription"
        body = f"""
Please find attached the latest audio recording.

Transcription:
--------------
{transcription}

Recording Time: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Recording Source: {self.url}
        """
        
        sender_email = self.email_settings['sender']
        receiver_email = self.email_settings['receiver']
        password = self.email_settings['password']

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with open(audio_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {audio_file}",
        )
        message.attach(part)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, message.as_string())
            print("Email sent successfully")
        except Exception as e:
            print(f"Error sending email: {e}")

    def run(self):
        """Main execution function"""
        try:
            # Setup browser and start media playback
            if not self.setup_browser():
                print("Failed to set up browser and start media playback.")
                return
            
            # Wait a moment for media to start playing
            time.sleep(3)
            
            # Record audio
            audio_file = self.record_audio()
            if audio_file:
                # Transcribe audio
                transcription = self.transcribe_audio(audio_file)
                print("Transcription:", transcription)
                
                # Send email with recording and transcription
                self.send_email(audio_file, transcription)
        except KeyboardInterrupt:
            print("\nStopping audio capture...")
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            # Clean up browser
            self.cleanup_browser()

    def run_scheduled(self, interval_minutes=60):
        """Run the capture on a schedule"""
        try:
            while True:
                print(f"Starting scheduled capture at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.run()
                print(f"Next capture scheduled in {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nStopping scheduled captures...")
            self.cleanup_browser()

# Example usage
if __name__ == "__main__":
    email_settings = {
        'sender': 'wubbalubba37@gmail.com',
        'receiver': 'holliemtran@gmail.com',
        'password': 'tenq vatb hkza venb'  # Use Gmail App Password
    }
    
    # Replace with your target URL and the CSS selector for the play button
    target_url = "https://www.liveatc.net/hlisten.php?mount=kdfw1_atis_arr&icao=kdfw"
    play_button_selector = "button"  # Example: CSS selector for the play button
    
    capture = WebAudioStreamCapture(email_settings, target_url, play_button_selector)

    # For a single capture:
    capture.run()
    
    # For scheduled captures every hour:
    
   # capture.run_scheduled(interval_minutes=60)