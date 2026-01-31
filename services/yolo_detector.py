"""
Fast Face Detector Service
Uses OpenCV Haar Cascade (fastest) for face detection
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
from config import Config


class FastFaceDetector:
    """
    Fast face detection using OpenCV Haar Cascade
    This is the fastest method for face detection on CPU
    """
    
    def __init__(self):
        self.confidence_threshold = Config.YOLO_CONFIDENCE
        self._initialized = False
        
        # Primary detector: Haar Cascade (very fast)
        self.haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Alternative: Haar cascade with alt tree (faster)
        self.haar_alt = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
        )
    
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
            # Faster settings
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,  # Larger = faster, less accurate
                minNeighbors=3,
                minSize=(60, 60),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
        else:
            # More accurate settings
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
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
