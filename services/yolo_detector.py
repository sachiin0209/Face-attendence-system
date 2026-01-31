"""
Fast Face Detector Service
Uses OpenCV Haar Cascade (fastest) for face detection
"""
import cv2
import numpy as np
import os
from typing import List, Tuple, Optional
from config import Config


def get_haar_cascade_path(cascade_name: str) -> str:
    """Get the path to a Haar cascade file"""
    # Try cv2.data first
    try:
        if hasattr(cv2, 'data') and cv2.data.haarcascades:
            path = cv2.data.haarcascades + cascade_name
            if os.path.exists(path):
                return path
    except:
        pass
    
    # Try common OpenCV installation paths
    possible_paths = [
        # Windows paths
        os.path.join(os.path.dirname(cv2.__file__), 'data', cascade_name),
        os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascades', cascade_name),
        # Site-packages path
        os.path.join(os.path.dirname(os.path.dirname(cv2.__file__)), 'cv2', 'data', cascade_name),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Last resort - just return the name and hope OpenCV finds it
    return cascade_name


class FastFaceDetector:
    """
    Fast face detection using OpenCV Haar Cascade
    This is the fastest method for face detection on CPU
    """
    
    def __init__(self):
        self.confidence_threshold = Config.YOLO_CONFIDENCE
        self._initialized = False
        
        # Primary detector: Haar Cascade (very fast)
        cascade_path = get_haar_cascade_path('haarcascade_frontalface_default.xml')
        self.haar_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Alternative: Haar cascade with alt tree (faster)
        alt_path = get_haar_cascade_path('haarcascade_frontalface_alt2.xml')
        self.haar_alt = cv2.CascadeClassifier(alt_path)
        
        # Verify cascades loaded
        if self.haar_cascade.empty():
            print(f"Warning: Could not load primary Haar cascade from {cascade_path}")
        if self.haar_alt.empty():
            print(f"Warning: Could not load alt Haar cascade from {alt_path}")
    
    def detect_faces_haar(self, image: np.ndarray, fast_mode: bool = True) -> List[Tuple[int, int, int, int]]:
        """
        Fast face detection using OpenCV Haar Cascade
        
        Args:
            image: BGR image
            fast_mode: If True, uses faster but less accurate settings
            
        Returns:
            List of face locations as (top, right, bottom, left) - face_recognition format
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Equalize histogram for better detection
        gray = cv2.equalizeHist(gray)
        
        if fast_mode:
            # Balanced settings - not too strict
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,  # More accurate detection
                minNeighbors=4,
                minSize=(30, 30),  # Smaller min size for better detection
                flags=cv2.CASCADE_SCALE_IMAGE
            )
        else:
            # More accurate settings
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=5,
                minSize=(20, 20),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
        
        # Convert from (x, y, w, h) to (top, right, bottom, left)
        face_locations = []
        for (x, y, w, h) in faces:
            top = y
            right = x + w
            bottom = y + h
            left = x
            face_locations.append((top, right, bottom, left))
        
        return face_locations
    
    def detect_faces_alt(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Alternative fast face detection using alt Haar cascade
        
        Args:
            image: BGR image
            
        Returns:
            List of face locations
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        faces = self.haar_alt.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=3,
            minSize=(60, 60)
        )
        
        face_locations = []
        for (x, y, w, h) in faces:
            face_locations.append((y, x + w, y + h, x))
        
        return face_locations
    
    def detect_faces(self, image: np.ndarray, use_yolo: bool = False) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using the best available method
        
        Args:
            image: BGR image
            use_yolo: Ignored, always uses Haar
            
        Returns:
            List of face locations
        """
        # Always use Haar cascade - it's fast and reliable
        locations = self.detect_faces_haar(image, fast_mode=True)
        
        # Fallback to alt cascade if Haar finds nothing
        if not locations:
            locations = self.detect_faces_alt(image)
        
        return locations


# Alias for backward compatibility
YOLOFaceDetector = FastFaceDetector

# Singleton instance
_detector = None


def get_face_detector() -> FastFaceDetector:
    """Get or create face detector singleton"""
    global _detector
    if _detector is None:
        _detector = FastFaceDetector()
    return _detector
