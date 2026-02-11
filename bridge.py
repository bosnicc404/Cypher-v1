import subprocess
import os
import sys
import threading
import queue
import time
import numpy as np
import re
import requests
from collections import deque
import sounddevice as sd
import wavio
from faster_whisper import WhisperModel
import pyttsx3
from transformers import pipeline
import PyPDF2
from flask import Flask, request, jsonify
from flask_cors import CORS
import pyaudio
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

#api keys
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
OPENWEATHER_API_KEY= os .getenv('OPENWEATHER_API_KEY')

def list_audio_devices():
    """List all available audio devices"""
    p = pyaudio.PyAudio()
    print("\n=== AUDIO DEVICES ===")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']}")
        print(f"  - Input channels: {info['maxInputChannels']}")
        print(f"  - Sample rate: {info['defaultSampleRate']}")
        print(f"  - Host API: {info['hostApi']}")
    p.terminate()

list_audio_devices()

app = Flask(__name__)
CORS(app, origins=["http://localhost:8000", "http://127.0.0.1:8000"])

# ==================== SPOTIFY CONFIG ====================
# SPOTIFY_CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
# SPOTIFY_CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
# SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"

# # Initialize Spotify client
# sp_oauth = SpotifyOAuth(
#     client_id=SPOTIFY_CLIENT_ID,
#     client_secret=SPOTIFY_CLIENT_SECRET,
#     redirect_uri=SPOTIFY_REDIRECT_URI,
#     scope="user-read-private user-read-email user-read-currently-playing user-modify-playback-state playlist-modify-public playlist-modify-private"
# )

# sp = None

# def init_spotify():
#     """Initialize Spotify connection"""
#     global sp
#     try:
#         cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=".spotifycache")
#         auth_manager = SpotifyOAuth(
#             client_id=SPOTIFY_CLIENT_ID,
#             client_secret=SPOTIFY_CLIENT_SECRET,
#             redirect_uri=SPOTIFY_REDIRECT_URI,
#             scope="user-read-private user-read-email user-read-currently-playing user-modify-playback-state playlist-modify-public playlist-modify-private",
#             cache_handler=cache_handler
#         )
#         sp = spotipy.Spotify(auth_manager=auth_manager)
#         print("✅ Spotify initialized")
#         return True
#     except Exception as e:
#         print(f"❌ Spotify init failed: {e}")
#         return False


WAKE_WORDS = ["cipher", "cypher"]
STOP_WORDS = ["bye cipher", "bye cypher", "go to sleep", "stop listening", "goodbye cipher", "goodbye cypher"]

SILENCE_THRESHOLD = 2.0       
SAMPLE_RATE = 44100
WAKE_CHECK_INTERVAL_CHUNKS = 5  

sys.stdout.reconfigure(encoding="utf-8")
print("DEBUG: Starting imports...")

try:
    import wavio
    print("✅ wavio imported")
except ImportError as e:
    print(f"❌ wavio failed: {e}")
    sys.exit(1)

try:
    import sounddevice as sd
    print("✅ sounddevice imported")
except ImportError as e:
    print(f"❌ sounddevice failed: {e}")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
    print("✅ faster_whisper imported")
except ImportError as e:
    print(f"❌ faster_whisper failed: {e}")
    sys.exit(1)

try:
    import pyttsx3
    print("✅ pyttsx3 imported")
except ImportError as e:
    print(f"❌ pyttsx3 failed: {e}")
    sys.exit(1)

try:
    from transformers import pipeline
    print("✅ transformers imported")
except ImportError as e:
    print(f"❌ transformers failed: {e}")
    sys.exit(1)

try:
    import PyPDF2
    print("✅ PyPDF2 imported")
except ImportError as e:
    print(f"❌ PyPDF2 failed: {e}")
    sys.exit(1)

try:
    import spotipy
    print("✅ spotipy imported")
except ImportError as e:
    print(f"❌ spotipy failed: {e}")
    sys.exit(1)

print("\n🔄 Loading Whisper model...")
model = WhisperModel("base.en", device="cpu", compute_type="int8")
print("✅ Whisper model loaded")

print("🔄 Loading mBart Summarization model...")
summarizer = pipeline("summarization", model="ARTeLab/mbart-summarization-fanpage", load_in_8bit=True)
print("✅ mBart model loaded")

#print("🔄 Initializing Spotify...")
#init_spotify()

print("Available audio devices:")
for i, device in enumerate(sd.query_devices()):
    print(f"Device {i}: {device['name']} (input channels: {device['max_input_channels']})")

# ==================== FIXED TTS CLASS ====================
class TTSThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = queue.Queue()
        self.engine = None
        self.initialized = False

    def run(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            
            voices = self.engine.getProperty('voices')
            print("Available voices:")
            for i, v in enumerate(voices):
                print(f"Voice {i}: {v.name} ({v.id})")
                
            voice_set = False
            for v in voices:
                if "zira" in v.name.lower() or "english" in v.name.lower():
                    self.engine.setProperty('voice', v.id)
                    voice_set = True
                    print(f"✅ Using voice: {v.name}")
                    break
            
            if not voice_set and voices:
                self.engine.setProperty('voice', voices[0].id)
                print("⚠️ Using fallback voice: " + voices[0].name)
            
            self.initialized = True
            print("✅ TTS Engine initialized successfully")
            
        except Exception as e:
            print(f"❌ TTS Engine initialization failed: {e}")
            return

        while True:
            try:
                text = self.queue.get()
                if text is None:
                    break
                print(f"🔊 Speaking: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
                self.queue.task_done()
                print("✅ Finished speaking")
            except Exception as e:
                print(f"❌ TTS Error in thread: {e}")
                self.queue.task_done()

    def speak(self, text):
        if not self.initialized:
            print("❌ TTS not initialized!")
            return
        print(f"📥 Queuing text: {text}")
        self.queue.put(text)

speaker = TTSThread()
speaker.start()

time.sleep(2)

try:
    speaker.speak("Test audio output - Cipher is ready")
    print("✅ TTS engine test queued successfully")
except Exception as e:
    print(f"❌ TTS startup test failed: {e}")

# ==================== VOICE STATE WITH AUTO-CALIBRATION ====================
class VoiceManager:
    def __init__(self):
        self.is_active = False
        self.is_listening = False
        self.audio_queue = queue.Queue(maxsize=200)
        self.stop_event = threading.Event()
        self.silence_frames = 0
        self.frames = []
        self.last_response = None
        self.noise_floor = 0.001
        self.calibration_samples = 50
        self.calibration_count = 0
        self.calibrated = False

    def calibrate_noise_floor(self, audio_chunk):
        chunk_level = np.abs(audio_chunk).mean()
        if self.calibration_count < self.calibration_samples:
            self.noise_floor = (self.noise_floor * self.calibration_count + chunk_level) / (self.calibration_count + 1)
            self.calibration_count += 1
            if self.calibration_count == self.calibration_samples:
                print(f"🎯 Auto-calibrated noise floor: {self.noise_floor:.6f}")
                self.calibrated = True
        return chunk_level

    def is_silent(self, audio_chunk):
        chunk_level = self.calibrate_noise_floor(audio_chunk)
        threshold = max(self.noise_floor * 3, 0.001)
        is_silent = chunk_level < threshold
        if not self.calibrated and self.calibration_count % 10 == 0:
            print(f"⚙️ Calibrating... Current level: {chunk_level:.6f}, Threshold: {threshold:.6f}")
        elif self.calibrated:
            print(f"🔊 Audio level: {chunk_level:.6f}, Threshold: {threshold:.6f}, Silent: {is_silent}")
        return is_silent

    def reset(self):
        self.frames = []
        self.silence_frames = 0

voice_manager = VoiceManager()

def speak_blocking(text):
    try:
        print(f"🔊 Attempting to speak: '{text}'")
        speaker.speak(text)
    except Exception as e:
        print(f"❌ TTS blocking error: {e}")

def continuous_audio_capture():
    print("🎤 Starting ALWAYS-ON audio capture stream...")
    
    input_device = None
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_device = i
                print(f"🎤 Using input device {i}: {device['name']}")
                break
    except Exception as e:
        print(f"⚠️ Could not query devices: {e}")
        input_device = sd.default.device['input']
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"⚠️ Audio status: {status}")
        try:
            audio_level = np.abs(indata).mean()
            if audio_level > 0.001:
                print(f"🔊 Audio level: {audio_level:.6f}")
            voice_manager.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            try:
                voice_manager.audio_queue.get_nowait()
                voice_manager.audio_queue.put_nowait(indata.copy())
            except:
                pass

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=int(SAMPLE_RATE * 0.1),
            callback=audio_callback,
            dtype='float32',
            device=input_device
        ):
            print("🔊 Audio stream active and listening forever...")
            while not voice_manager.stop_event.is_set():
                time.sleep(0.1)
    except Exception as e:
        print(f"❌ Audio capture error: {e}")
        print("🔧 Trying default device...")
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=int(SAMPLE_RATE * 0.1),
                callback=audio_callback,
                dtype='float32'
            ):
                print("🔊 Audio stream active with default settings...")
                while not voice_manager.stop_event.is_set():
                    time.sleep(0.1)
        except Exception as e2:
            print(f"❌ Audio capture failed completely: {e2}")

def process_audio_stream():
    print("🔊 Starting audio processor - ALWAYS LISTENING...")
    temp_audio = "temp_voice.wav"
    wake_check = "wake_check.wav"

    while not voice_manager.stop_event.is_set():
        try:
            if not voice_manager.is_active:
                voice_manager.frames = []
                frame_count = 0

                while not voice_manager.is_active and not voice_manager.stop_event.is_set():
                    try:
                        chunk = voice_manager.audio_queue.get(timeout=0.2)
                        voice_manager.frames.append(chunk)
                        frame_count += 1

                        if frame_count % WAKE_CHECK_INTERVAL_CHUNKS == 0 and len(voice_manager.frames) >= 5:
                            audio_data = np.concatenate(voice_manager.frames[-10:])
                            wavio.write(wake_check, (audio_data * 32767).astype(np.int16), SAMPLE_RATE, sampwidth=2)

                            try:
                                segments, _ = model.transcribe(
                                    wake_check, 
                                    language="en",
                                    beam_size=7,
                                    vad_filter=True
                                )
                                text = " ".join([s.text.lower().strip() for s in segments if s.avg_logprob > -0.5 and s.text.strip()])
                                print(f"Whisper heard (wake check): '{text}'")

                                if text and len(text) > 3 and any(re.search(r'\b' + re.escape(word) + r'\b', text) for word in WAKE_WORDS):
                                    print(f"\n🚀🚀🚀 WAKE WORD DETECTED: '{text}' 🚀🚀🚀\n")
                                    voice_manager.is_active = True
                                    voice_manager.reset()
                                    
                                    speak_blocking("I'm awake")
                                    time.sleep(0.5)
                                    
                                    while not voice_manager.audio_queue.empty():
                                        try:
                                            voice_manager.audio_queue.get_nowait()
                                        except queue.Empty:
                                            break
                                    time.sleep(0.4)
                                    break
                            except Exception as e:
                                print(f"Whisper wake-check error: {e}")
                    except queue.Empty:
                        continue

            else:
                try:
                    chunk = voice_manager.audio_queue.get(timeout=0.1)
                    voice_manager.frames.append(chunk)

                    is_silent = voice_manager.is_silent(chunk)
                    
                    if is_silent:
                        voice_manager.silence_frames += 1
                        print(f"🔇 Silence frame count: {voice_manager.silence_frames}")
                    else:
                        voice_manager.silence_frames = 0
                        print("🔊 Detected speech")

                    max_frames = 300
                    if voice_manager.silence_frames > int(SILENCE_THRESHOLD * 10) or len(voice_manager.frames) > max_frames:
                        if len(voice_manager.frames) > 15:
                            print("⏹️ Silence detected or max reached, processing...")
                            
                            trim_frames = int(SILENCE_THRESHOLD * 10) if voice_manager.silence_frames > 0 else 0
                            end_idx = -trim_frames if trim_frames > 0 else None
                            audio_data = np.concatenate(voice_manager.frames[:end_idx])
                            wavio.write(temp_audio, (audio_data * 32767).astype(np.int16), SAMPLE_RATE, sampwidth=2)

                            try:
                                segments, _ = model.transcribe(
                                    temp_audio, 
                                    language="en",
                                    beam_size=7,
                                    vad_filter=True
                                )
                                user_text = " ".join([s.text.strip() for s in segments]).strip()

                                if user_text:
                                    print(f"👤 User said: '{user_text}'")

                                    if any(stop.lower() in user_text.lower() for stop in STOP_WORDS):
                                        print("👋 STOP WORD DETECTED - GOING TO SLEEP\n")
                                        voice_manager.is_active = False
                                        speak_blocking("Going to sleep. Catch you later.")  
                                        voice_manager.reset()
                                    else:
                                        try:
                                            response = requests.post(
                                                'http://127.0.0.1:8080/api/chat',
                                                json={
                                                    "model": "cypher",
                                                    "messages": [{"role": "user", "content": user_text}],
                                                    "stream": False
                                                },
                                                timeout=30
                                            )
                                            response.raise_for_status()
                                            ai_response = response.json().get("message", {}).get("content", "No response")
                                            print(f"🤖 Cypher: {ai_response}\n")

                                            voice_manager.last_response = {
                                                "user": user_text,
                                                "response": ai_response
                                            }

                                            print(f"🔊 About to speak AI response: {ai_response}")
                                            speak_blocking(ai_response)

                                        except Exception as e:
                                            print(f"❌ Ollama error: {e}")
                                            error_msg = "Sorry, my brain is offline right now."
                                            speak_blocking(error_msg)  
                                            voice_manager.last_response = {
                                                "user": user_text,
                                                "response": error_msg
                                            }

                                voice_manager.reset()

                            except Exception as e:
                                print(f"❌ Transcription error: {e}")
                                voice_manager.reset()
                        else:
                            voice_manager.reset()

                except queue.Empty:
                    continue

        except Exception as e:
            print(f"❌ Audio processing loop error: {e}")
            time.sleep(1)

print("\n🚀 Starting background audio listener...")
voice_manager.is_listening = True

capture_thread = threading.Thread(target=continuous_audio_capture, daemon=True)
process_thread = threading.Thread(target=process_audio_stream, daemon=True)

capture_thread.start()
process_thread.start()

print("✅ Background listening is LIVE\n")

# ==================== API ROUTES ====================
@app.route('/voice_status', methods=['GET'])
def voice_status():
    return jsonify({
        "listening": voice_manager.is_listening,
        "in_conversation": voice_manager.is_active
    })

@app.route('/get_voice_response', methods=['GET'])
def get_voice_response():
    if voice_manager.last_response:
        response = voice_manager.last_response
        voice_manager.last_response = None
        return jsonify(response), 200
    return jsonify({}), 204

@app.route('/speak', methods=['POST'])
def speak_route():
    text = request.json.get("text", "")
    print(f"📡 API Speak request: {text}")
    speaker.speak(text)
    return jsonify({"status": "spoken"})

@app.route('/weather', methods=['POST'])
def get_weather():
    try:
        data = request.json
        city = data.get('city', '').strip()
        
        if not city:
            return jsonify({"error": "No city provided"}), 400
        
        print(f"🌤️ Getting weather for: {city}")
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        weather_data = response.json()
        
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']
        description = weather_data['weather'][0]['description']
        humidity = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']
        
        weather_response = f"🌤️ **Weather in {city.title()}:**\n\n"
        weather_response += f"Temperature: {temp}°C (feels like {feels_like}°C)\n"
        weather_response += f"Conditions: {description.title()}\n"
        weather_response += f"Humidity: {humidity}%\n"
        weather_response += f"Wind Speed: {wind_speed} m/s"
        
        return jsonify({"weather": weather_response}), 200
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": f"City '{city}' not found"}), 404
        return jsonify({"error": "Weather API error"}), 500
    except Exception as e:
        print(f"❌ Weather error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== SPOTIFY ROUTES ====================
# @app.route('/spotify/play', methods=['POST'])
# def spotify_play():
#     """Play a track by query"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         data = request.json
#         query = data.get('query', '')
        
#         if not query:
#             return jsonify({"error": "No query provided"}), 400
        
#         results = sp.search(q=query, type='track', limit=1)
        
#         if not results['tracks']['items']:
#             return jsonify({"error": f"No tracks found for '{query}'"}), 404
        
#         track = results['tracks']['items'][0]
#         track_uri = track['uri']
        
#         sp.start_playback(uris=[track_uri])
        
#         return jsonify({
#             "status": "playing",
#             "track": track['name'],
#             "artist": track['artists'][0]['name']
#         }), 200
    
#     except Exception as e:
#         print(f"❌ Spotify play error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/pause', methods=['POST'])
# def spotify_pause():
#     """Pause playback"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         sp.pause_playback()
#         return jsonify({"status": "paused"}), 200
#     except Exception as e:
#         print(f"❌ Spotify pause error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/resume', methods=['POST'])
# def spotify_resume():
#     """Resume playback"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         sp.start_playback()
#         return jsonify({"status": "resumed"}), 200
#     except Exception as e:
#         print(f"❌ Spotify resume error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/next', methods=['POST'])
# def spotify_next():
#     """Skip to next track"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         sp.next_track()
#         return jsonify({"status": "skipped to next"}), 200
#     except Exception as e:
#         print(f"❌ Spotify next error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/previous', methods=['POST'])
# def spotify_previous():
#     """Go to previous track"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         sp.previous_track()
#         return jsonify({"status": "went to previous"}), 200
#     except Exception as e:
#         print(f"❌ Spotify previous error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/current', methods=['GET'])
# def spotify_current():
#     """Get currently playing track"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         current = sp.current_playback()
        
#         if not current or not current.get('item'):
#             return jsonify({"status": "nothing playing"}), 200
        
#         track = current['item']
#         return jsonify({
#             "track": track['name'],
#             "artist": track['artists'][0]['name'],
#             "album": track['album']['name'],
#             "is_playing": current['is_playing']
#         }), 200
#     except Exception as e:
#         print(f"❌ Spotify current error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/volume', methods=['POST'])
# def spotify_volume():
#     """Set volume 0-100"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         data = request.json
#         volume = data.get('volume', 50)
        
#         if volume < 0 or volume > 100:
#             return jsonify({"error": "Volume must be 0-100"}), 400
        
#         sp.volume(volume)
#         return jsonify({"status": f"volume set to {volume}"}), 200
#     except Exception as e:
#         print(f"❌ Spotify volume error: {e}")
#         return jsonify({"error": str(e)}), 500

# @app.route('/spotify/playlist', methods=['POST'])
# def spotify_playlist():
#     """Play a playlist by name"""
#     if not sp:
#         return jsonify({"error": "Spotify not initialized"}), 500
    
#     try:
#         data = request.json
#         playlist_name = data.get('playlist', '')
        
#         if not playlist_name:
#             return jsonify({"error": "No playlist name provided"}), 400
        
#         playlists = sp.current_user_playlists()
        
#         playlist = None
#         for p in playlists['items']:
#             if playlist_name.lower() in p['name'].lower():
#                 playlist = p
#                 break
        
#         if not playlist:
#             return jsonify({"error": f"Playlist '{playlist_name}' not found"}), 404
        
#         sp.start_playback(context_uri=playlist['uri'])
        
#         return jsonify({
#             "status": "playing",
#             "playlist": playlist['name']
#         }), 200
#     except Exception as e:
#         print(f"❌ Spotify playlist error: {e}")
#         return jsonify({"error": str(e)}), 500

@app.route('/exec', methods=['POST'])
def execute_command():
    data = request.json
    command = data.get('command', '').lower()
    apps = {
        "steam": "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Steam",
        "discord": "C:\\Users\\Amar\\AppData\\Local\\Discord\\app-1.0.9220\\Discord.exe",
        "spotify": "spotify",
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "roblox": "roblox:",
        "code": "code",
        "calculator": "calc",
        "notepad": "notepad"
    }

    for key, val in apps.items():
        if key in command:
            try:
                if "http" in val or ":" in val:
                    subprocess.Popen(f'start {val}', shell=True)
                else:
                    subprocess.Popen(val, shell=True)
                print(f"✅ Launched {key}")
                return jsonify({"status": f"{key} launched"}), 200
            except Exception as e:
                print(f"❌ Failed to launch {key}: {e}")
                return jsonify({"error": str(e)}), 500

    return jsonify({"status": "unknown command"}), 400

@app.route('/web_search', methods=['POST'])
def web_search():
    try:
        data = request.json
        query = data.get('query', '').strip()

        if not query:
            return jsonify({"error": "Empty query"}), 400

        print(f"🔍 Searching for: {query}")

        url = "https://google.serper.dev/search"
        payload = {"q": query, "num": 5}
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=8)
        response.raise_for_status()

        serper_data = response.json()
        formatted_results = []

        for result in serper_data.get('organic', [])[:5]:
            formatted_results.append({
                'title': result.get('title', ''),
                'url': result.get('link', ''),
                'content': result.get('snippet', '')
            })

        if formatted_results:
            return jsonify({
                "results": formatted_results,
                "count": len(formatted_results)
            }), 200
        else:
            return jsonify({"error": "No results found"}), 404

    except Exception as e:
        print(f"❌ Web search error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/summarize_pdf', methods=['POST'])
def summarize_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""

        if not text.strip():
            return jsonify({"error": "Could not extract text from PDF"}), 400

        max_chunk_length = 1024
        chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]

        summaries = []
        for idx, chunk in enumerate(chunks):
            if len(chunk.split()) > 30:
                try:
                    summary = summarizer(chunk, max_length=150, min_length=40, do_sample=False)
                    if summary and 'summary_text' in summary[0]:
                        summaries.append(summary[0]['summary_text'])
                except Exception as e:
                    print(f"⚠️ Chunk {idx + 1} summarization failed: {e}")

        final_summary = " ".join(summaries) if summaries else text[:1000] + "..." if len(text) > 1000 else text

        return jsonify({"summary": final_summary}), 200

    except Exception as e:
        print(f"❌ PDF summarization error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🔥🔥🔥 Cypher Bridge LIVE - ALWAYS LISTENING 🔥🔥🔥\n")
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        voice_manager.stop_event.set()
        capture_thread.join(timeout=2)
        process_thread.join(timeout=2)