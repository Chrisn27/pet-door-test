"""
Pet Door Monitor - Local Development Version
Use this version for testing on your PC without a Raspberry Pi camera
"""
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import shutil
import platform

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import cv2
import psutil

# Mock imports for local development
RUNNING_ON_PI = platform.machine().startswith('arm') or platform.machine().startswith('aarch')

if RUNNING_ON_PI:
    from picamera2 import Picamera2
    from ultralytics import YOLO
    print("Running on Raspberry Pi - using real camera and YOLO")
else:
    from mock_camera import Picamera2, MockYOLO as YOLO
    print("Running on PC - using mock camera and YOLO")

# Configuration
CONFIG = {
    'fps': 2,
    'resolution': (1280, 720),
    'storage_path': Path.home() / 'pet-door-data',
    'high_water_mark_gb': 10,
    'detection_confidence': 0.5,
    'motion_threshold': 30,
    'cooldown_seconds': 5,
}

app = Flask(__name__)
CORS(app)

# Global state
camera = None
model = None
last_detection_time = 0
detection_active = True
background_frame = None

def init_camera():
    """Initialize the camera with proper configuration"""
    global camera
    try:
        camera = Picamera2()
        config = camera.create_still_configuration(
            main={"size": CONFIG['resolution']},
            buffer_count=2
        )
        camera.configure(config)
        camera.start()
        time.sleep(2)
        print("✓ Camera initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Camera initialization failed: {e}")
        return False

def init_model():
    """Load YOLO model for pet detection"""
    global model
    try:
        model = YOLO('yolov8n.pt')
        print("✓ YOLO model loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        if not RUNNING_ON_PI:
            print("  (This is expected on PC - using mock model)")
        return False

def ensure_storage():
    """Create storage directory structure"""
    paths = [
        CONFIG['storage_path'],
        CONFIG['storage_path'] / 'cats',
        CONFIG['storage_path'] / 'dogs',
        CONFIG['storage_path'] / 'unknown',
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    print("✓ Storage directories ready")

def get_storage_usage_gb():
    """Calculate total storage used"""
    total_size = 0
    for root, _, files in os.walk(CONFIG['storage_path']):
        total_size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    return total_size / (1024 ** 3)

def cleanup_old_files():
    """Remove oldest files when storage exceeds high water mark"""
    current_usage = get_storage_usage_gb()
    if current_usage <= CONFIG['high_water_mark_gb']:
        return
    
    print(f"Storage at {current_usage:.2f}GB, cleaning up...")
    
    all_files = []
    for root, _, files in os.walk(CONFIG['storage_path']):
        for file in files:
            if file.endswith('.jpg'):
                filepath = os.path.join(root, file)
                all_files.append((filepath, os.path.getmtime(filepath)))
    
    all_files.sort(key=lambda x: x[1])
    
    files_to_delete = int(len(all_files) * 0.2)
    for filepath, _ in all_files[:files_to_delete]:
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")
    
    new_usage = get_storage_usage_gb()
    print(f"Cleanup complete. Storage now: {new_usage:.2f}GB")

def detect_motion(frame):
    """Simple motion detection by comparing with background frame"""
    global background_frame
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if background_frame is None:
        background_frame = gray
        return False
    
    frame_delta = cv2.absdiff(background_frame, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    
    background_frame = cv2.addWeighted(background_frame, 0.9, gray, 0.1, 0)
    
    motion_pixels = cv2.countNonZero(thresh)
    frame_pixels = frame.shape[0] * frame.shape[1]
    motion_percent = (motion_pixels / frame_pixels) * 100
    
    return motion_percent > CONFIG['motion_threshold']

def detect_pets(frame):
    """Detect cats and dogs in the frame"""
    results = model(frame, conf=CONFIG['detection_confidence'])
    
    detected_pets = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])
            
            if class_name in ['cat', 'dog']:
                detected_pets.append({
                    'type': class_name,
                    'confidence': confidence,
                    'bbox': box.xyxy[0].tolist()
                })
    
    return detected_pets

def save_detection(frame, pets):
    """Save detected image with metadata"""
    timestamp = datetime.now()
    
    if not pets:
        category = 'unknown'
    elif any(p['type'] == 'cat' for p in pets):
        category = 'cats'
    elif any(p['type'] == 'dog' for p in pets):
        category = 'dogs'
    else:
        category = 'unknown'
    
    filename = timestamp.strftime('%Y%m%d_%H%M%S.jpg')
    filepath = CONFIG['storage_path'] / category / filename
    cv2.imwrite(str(filepath), frame)
    
    meta_filepath = filepath.with_suffix('.json')
    metadata = {
        'timestamp': timestamp.isoformat(),
        'category': category,
        'detections': pets,
        'filename': filename
    }
    with open(meta_filepath, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Saved: {category}/{filename} - {len(pets)} pet(s) detected")
    return filepath

def monitoring_loop():
    """Main monitoring loop"""
    global last_detection_time
    
    print("Starting monitoring loop...")
    
    while True:
        if not detection_active:
            time.sleep(1)
            continue
        
        try:
            frame = camera.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            if detect_motion(frame_bgr):
                current_time = time.time()
                
                if current_time - last_detection_time < CONFIG['cooldown_seconds']:
                    time.sleep(1 / CONFIG['fps'])
                    continue
                
                pets = detect_pets(frame_bgr)
                
                if pets or True:
                    save_detection(frame_bgr, pets)
                    last_detection_time = current_time
                    cleanup_old_files()
            
            time.sleep(1 / CONFIG['fps'])
            
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(1)

# REST API Endpoints

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    return jsonify({
        'active': detection_active,
        'storage_used_gb': round(get_storage_usage_gb(), 2),
        'storage_limit_gb': CONFIG['high_water_mark_gb'],
        'fps': CONFIG['fps'],
        'last_detection': last_detection_time,
        'running_on_pi': RUNNING_ON_PI
    })

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Get list of all detections with optional filtering"""
    category = request.args.get('category', 'all')
    limit = int(request.args.get('limit', 100))
    
    detections = []
    
    if category == 'all':
        dirs = ['cats', 'dogs', 'unknown']
    else:
        dirs = [category]
    
    for dir_name in dirs:
        dir_path = CONFIG['storage_path'] / dir_name
        if not dir_path.exists():
            continue
        
        for meta_file in dir_path.glob('*.json'):
            try:
                with open(meta_file, 'r') as f:
                    data = json.load(f)
                    data['id'] = meta_file.stem
                    data['image_url'] = f"/api/image/{dir_name}/{meta_file.stem}.jpg"
                    detections.append(data)
            except Exception as e:
                print(f"Error reading {meta_file}: {e}")
    
    detections.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({
        'detections': detections[:limit],
        'total': len(detections)
    })

@app.route('/api/image/<category>/<filename>', methods=['GET'])
def get_image(category, filename):
    """Serve an image file"""
    filepath = CONFIG['storage_path'] / category / filename
    if filepath.exists():
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/toggle', methods=['POST'])
def toggle_detection():
    """Start/stop detection"""
    global detection_active
    detection_active = not detection_active
    return jsonify({
        'active': detection_active,
        'message': 'Detection ' + ('started' if detection_active else 'stopped')
    })

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify(CONFIG)
    
    data = request.json
    if 'fps' in data:
        CONFIG['fps'] = int(data['fps'])
    if 'high_water_mark_gb' in data:
        CONFIG['high_water_mark_gb'] = int(data['high_water_mark_gb'])
    if 'detection_confidence' in data:
        CONFIG['detection_confidence'] = float(data['detection_confidence'])
    
    return jsonify({'success': True, 'config': CONFIG})

@app.route('/api/delete/<category>/<image_id>', methods=['DELETE'])
def delete_detection(category, image_id):
    """Delete a specific detection"""
    img_path = CONFIG['storage_path'] / category / f"{image_id}.jpg"
    meta_path = CONFIG['storage_path'] / category / f"{image_id}.json"
    
    try:
        if img_path.exists():
            os.remove(img_path)
        if meta_path.exists():
            os.remove(meta_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Pet Door Monitor - Starting Up")
    if not RUNNING_ON_PI:
        print("*** LOCAL DEVELOPMENT MODE ***")
        print("Using mock camera and YOLO for testing")
    print("="*50 + "\n")
    
    ensure_storage()
    
    if not init_camera():
        print("Failed to initialize camera. Exiting.")
        exit(1)
    
    if not init_model():
        print("Failed to load YOLO model. Exiting.")
        exit(1)
    
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()
    
    print("\n" + "="*50)
    print("System Ready!")
    print("API running on http://0.0.0.0:5000")
    if not RUNNING_ON_PI:
        print("\n*** TESTING LOCALLY - No real camera ***")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
