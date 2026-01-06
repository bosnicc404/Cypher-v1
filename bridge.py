import subprocess
import os
import sys
import threading
import queue
import time
import numpy as np
import re

def structure_text(text):
    # split into sentences for spacing
    sentences = re.split(r'(?<=[.!?]) +', text)
    
    structured = ""
    for s in sentences:
        s = s.strip()
        if len(s) > 0:
            # maybe add a little stylistic flair
            if s[-1] not in ".!?":
                s += "."  # make sure every sentence ends properly
            # optional: add soft pause emoji for vibe
            if len(s.split()) > 6:
                s += " ⚡"
            structured += s + " "
    return structured.strip()


sys.stdout.reconfigure(encoding="utf-8")
# -*- coding: utf-8 -*-
print("🔍 DEBUG: Starting imports...")

try:
    import wavio
    print("✅ wavio imported")
except ImportError as e:
    print(f"❌ wavio FAILED: {e}")
    sys.exit(1)

try:
    import sounddevice as sd
    print("✅ sounddevice imported")
except ImportError as e:
    print(f"❌ sounddevice FAILED: {e}")
    sys.exit(1)

try:
    from faster_whisper import WhisperModel
    print("✅ faster_whisper imported")
except ImportError as e:
    print(f"❌ faster_whisper FAILED: {e}")
    sys.exit(1)

try:
    import pyttsx3
    print("✅ pyttsx3 imported")
except ImportError as e:
    print(f"❌ pyttsx3 FAILED: {e}")
    sys.exit(1)

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- LOAD WHISPER ---
print("🔍 DEBUG: Loading Whisper model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("✅ Whisper model loaded")

# --- PYTTSX3 SETUP ---
engine = pyttsx3.init()
engine.setProperty('rate', 150)   # speed
engine.setProperty('volume', 1.0) # max volume

voices = engine.getProperty('voices')
# Choose a male / robotic voice
for v in voices:
    if "male" in v.name.lower() or "english" in v.name.lower():
        engine.setProperty('voice', v.id)
        break

# --- RECORDING THREAD / FLAGS ---
recording_flag = threading.Event()
record_thread = None
audio_filename = "temp.wav"

def record_audio(filename=audio_filename, fs=44100):
    print("🎤 Recording started...")
    frames = []
    while recording_flag.is_set():
        chunk = sd.rec(int(0.5 * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        frames.append(chunk)
    if frames:
        audio_array = np.concatenate(frames, axis=0)
        wavio.write(filename, audio_array, fs, sampwidth=2)
        print(f"✅ Saved {filename}")
    return filename

def transcribe_audio(file_path):
    # Wait until file exists
    timeout = 5
    while not os.path.exists(file_path) and timeout > 0:
        time.sleep(0.1)
        timeout -= 0.1
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found after recording.")

    segments, _ = model.transcribe(file_path, beam_size=5)
    text = " ".join([s.text for s in segments])
    print(f"✅ Transcription: {text}")
    return text.strip()

# --- ROUTES ---
@app.route('/whisper_start', methods=['POST'])
def whisper_start():
    global record_thread
    recording_flag.set()
    record_thread = threading.Thread(target=record_audio)
    record_thread.start()
    return jsonify({"status": "recording"})

@app.route('/whisper_stop', methods=['POST'])
def whisper_stop():
    recording_flag.clear()
    if record_thread:
        record_thread.join()  # wait until recording finishes
    try:
        text = transcribe_audio(audio_filename)
        if os.path.exists(audio_filename):
            os.remove(audio_filename)
        return jsonify({"text": text})
    except Exception as e:
        print(f"❌ Whisper STOP error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/speak', methods=['POST'])
def speak_route():
    text = request.json.get("text", "")
    engine.say(text)
    engine.runAndWait()
    return jsonify({"status": "spoken"})

@app.route('/exec', methods=['POST'])
def execute_command():
    data = request.json
    command = data.get('command', '').lower()
    apps = {
        "discord": "discord",
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
                subprocess.Popen(['start', val] if "http" in val or ":" in val else [val], shell=True)
                print(f"✅ Launched {key}")
                return jsonify({"status": f"{key} launched"}), 200
            except Exception as e:
                print(f"❌ Failed to launch {key}: {e}")
                return jsonify({"error": str(e)}), 500
    return jsonify({"status": "unknown command"}), 400

if __name__ == "__main__":
    print("🚀 CYPHER BRIDGE LIVE ON PORT 5000")
    print("🔥 Ready to transcribe voice and execute commands")
    app.run(host='127.0.0.1', port=5000, debug=False)
