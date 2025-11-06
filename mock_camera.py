"""
Mock Camera Module for Local Development
Replace picamera2 with this when testing on non-Pi systems
"""
import numpy as np
import time
from pathlib import Path

class Picamera2:
    """Mock Picamera2 for local development"""
    
    def __init__(self):
        self.running = False
        print("Mock Camera initialized (for local development)")
    
    def create_still_configuration(self, main=None, buffer_count=2):
        """Mock configuration"""
        return {
            'main': main,
            'buffer_count': buffer_count
        }
    
    def configure(self, config):
        """Mock configure"""
        print(f"Mock camera configured: {config['main']['size']}")
    
    def start(self):
        """Mock start"""
        self.running = True
        print("Mock camera started")
    
    def stop(self):
        """Mock stop"""
        self.running = False
        print("Mock camera stopped")
    
    def capture_array(self):
        """Return a mock image array"""
        if not self.running:
            raise RuntimeError("Camera not started")
        
        # Generate a random image (simulating camera capture)
        # 1280x720 RGB image
        height, width = 720, 1280
        
        # Create a gradient background
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some noise to simulate motion
        noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
        image = image + noise
        
        # Simulate a "pet" moving through frame occasionally
        if np.random.random() > 0.7:  # 30% chance of "motion"
            # Draw a simple rectangle to simulate a pet
            x, y = np.random.randint(0, width-200), np.random.randint(0, height-200)
            image[y:y+100, x:x+150] = [200, 150, 100]  # Brown-ish rectangle
        
        # Small delay to simulate camera capture time
        time.sleep(0.01)
        
        return image


# For testing YOLO locally without real model
class MockYOLO:
    """Mock YOLO model for local testing"""
    
    def __init__(self, model_path):
        print(f"Mock YOLO loaded: {model_path}")
        self.names = {15: 'cat', 16: 'dog'}
    
    def __call__(self, frame, conf=0.5):
        """Simulate detection results"""
        return [MockResult()]


class MockResult:
    """Mock YOLO result"""
    
    def __init__(self):
        self.boxes = MockBoxes()
        self.names = {15: 'cat', 16: 'dog'}


class MockBoxes:
    """Mock detection boxes"""
    
    def __iter__(self):
        # Randomly return 0-2 detections
        num_detections = np.random.choice([0, 0, 0, 1, 2])  # Mostly no detections
        
        for _ in range(num_detections):
            yield MockBox()


class MockBox:
    """Mock single detection box"""
    
    def __init__(self):
        # Random cat or dog
        self.cls = [np.random.choice([15, 16])]
        self.conf = [np.random.uniform(0.5, 0.95)]
        
        # Random bounding box
        x1 = np.random.randint(0, 1000)
        y1 = np.random.randint(0, 600)
        x2 = x1 + np.random.randint(100, 300)
        y2 = y1 + np.random.randint(100, 300)
        
        self.xyxy = [np.array([x1, y1, x2, y2])]
