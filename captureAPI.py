from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from autolivescript import WebAudioStreamCapture

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

capture_instance = None
capture_thread = None

@app.route('/start', methods=['POST'])
def start_capture():
    global capture_instance, capture_thread
    
    # Stop any existing capture
    if capture_thread and capture_thread.is_alive():
        return jsonify({"status": "error", "message": "Capture already running"})
    
    # Get settings from request
    data = request.json
    email_settings = {
        'sender': data['email']['sender'],
        'receiver': data['email']['receiver'],
        'password': data['email']['password']
    }
    
    # Create capture instance
    capture_instance = WebAudioStreamCapture(
        email_settings, 
        data['url'], 
        data['selector']
    )
    
    # Set duration
    capture_instance.duration = data['duration']
    
    # Start in scheduled or single mode
    if data['scheduled']:
        capture_thread = threading.Thread(
            target=capture_instance.run_scheduled,
            args=(data['interval'],)
        )
    else:
        capture_thread = threading.Thread(
            target=capture_instance.run
        )
    
    capture_thread.daemon = True
    capture_thread.start()
    
    return jsonify({"status": "success", "message": "Capture started"})

@app.route('/stop', methods=['POST'])
def stop_capture():
    global capture_instance
    
    if capture_instance:
        capture_instance.cleanup_browser()
        return jsonify({"status": "success", "message": "Capture stopped"})
    else:
        return jsonify({"status": "error", "message": "No capture running"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)