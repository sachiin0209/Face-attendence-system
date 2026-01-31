"""
Face Recognition Service
Handles face detection, encoding, and recognition
Optimized for speed with YOLO detection
"""
import cv2
import numpy as np
import face_recognition
import pickle
import os
from typing import Tuple, List, Optional, Dict, Any
from config import Config


class FaceRecognitionService:
    """
    Service class for face recognition operations including:
    - Face detection and encoding (with YOLO for speed)
    - Face matching and identification
    """
    
    def __init__(self, encodings_dir: str = None, tolerance: float = None):
        """
        Initialize face recognition service
        
        Args:
            encodings_dir: Directory to store face encodings
            tolerance: Recognition tolerance (lower = stricter)
        """
        self.encodings_dir = encodings_dir or Config.FACE_ENCODINGS_DIR
        self.tolerance = tolerance or Config.FACE_RECOGNITION_TOLERANCE
        self.detection_model = Config.FACE_DETECTION_MODEL
        self.num_jitters = Config.FACE_NUM_JITTERS
        self.scale_factor = Config.IMAGE_SCALE_FACTOR
        self.known_face_encodings: Dict[str, np.ndarray] = {}
        
        # Initialize fast detector
        self._fast_detector = None
        
        # Ensure directory exists
        os.makedirs(self.encodings_dir, exist_ok=True)
        
        # Load existing face encodings
        self._load_all_encodings()
    
    @property
    def fast_detector(self):
        """Lazy load fast detector"""
        if self._fast_detector is None:
            from services.yolo_detector import get_face_detector
            self._fast_detector = get_face_detector()
        return self._fast_detector
    
    def _load_all_encodings(self):
        """Load all saved face encodings from disk"""
        for filename in os.listdir(self.encodings_dir):
            if filename.endswith('.pkl'):
                person_id = filename[:-4]
                filepath = os.path.join(self.encodings_dir, filename)
                try:
                    with open(filepath, 'rb') as f:
                        self.known_face_encodings[person_id] = pickle.load(f)
                except Exception as e:
                    print(f"Error loading encoding for {person_id}: {e}")
    
    def _save_encoding(self, person_id: str, encoding: np.ndarray):
        """Save face encoding to disk"""
        filepath = os.path.join(self.encodings_dir, f"{person_id}.pkl")
        with open(filepath, 'wb') as f:
            pickle.dump(encoding, f)
    
    def _delete_encoding(self, person_id: str):
        """Delete face encoding from disk"""
        filepath = os.path.join(self.encodings_dir, f"{person_id}.pkl")
        if os.path.exists(filepath):
            os.remove(filepath)
        if person_id in self.known_face_encodings:
            del self.known_face_encodings[person_id]
    
    def _resize_image(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Resize image for faster processing"""
        if self.scale_factor >= 1.0:
            return image, 1.0
        
        height, width = image.shape[:2]
        new_width = int(width * self.scale_factor)
        new_height = int(height * self.scale_factor)
        
        resized = cv2.resize(image, (new_width, new_height))
        return resized, self.scale_factor
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image using fast detection
        
        Args:
            image: BGR image (from OpenCV)
        
        Returns:
            List of face locations as (top, right, bottom, left)
        """
        # Use fast Haar cascade detector (fastest method)
        if self.detection_model in ['yolo', 'haar', 'fast']:
            return self.fast_detector.detect_faces(image)
        else:
            # Fall back to face_recognition library (slower but more accurate)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return face_recognition.face_locations(rgb_image, model=self.detection_model)
    
    def detect_faces_fast(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Fast face detection with image scaling
        
        Args:
            image: BGR image
            
        Returns:
            Face locations scaled back to original image size
        """
        # Resize for faster processing
        resized, scale = self._resize_image(image)
        
        # Detect on resized image
        locations = self.detect_faces(resized)
        
        # Scale locations back to original size
        if scale < 1.0:
            scale_inv = 1.0 / scale
            locations = [
                (int(top * scale_inv), int(right * scale_inv), 
                 int(bottom * scale_inv), int(left * scale_inv))
                for (top, right, bottom, left) in locations
            ]
        
        return locations
    
    def get_face_encoding(self, image: np.ndarray, 
                          face_location: Tuple = None) -> Optional[np.ndarray]:
        """
        Get face encoding from an image
        
        Args:
            image: BGR image
            face_location: Optional specific face location
        
        Returns:
            128-dimensional face encoding or None if no face found
        """
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if face_location:
            encodings = face_recognition.face_encodings(
                rgb_image, 
                [face_location],
                num_jitters=self.num_jitters
            )
        else:
            encodings = face_recognition.face_encodings(
                rgb_image,
                num_jitters=self.num_jitters
            )
        
        return encodings[0] if encodings else None
    
    def register_face(self, person_id: str, images: List[np.ndarray]) -> Dict[str, Any]:
        """
        Register a new face with multiple images for better accuracy
        
        Args:
            person_id: Unique identifier (employee_id or admin_id)
            images: List of face images (at least 3 recommended)
        
        Returns:
            Registration result with success status and message
        """
        encodings = []
        
        for image in images:
            face_locations = self.detect_faces(image)
            
            if len(face_locations) == 0:
                continue
            elif len(face_locations) > 1:
                continue  # Skip images with multiple faces
            
            encoding = self.get_face_encoding(image, face_locations[0])
            if encoding is not None:
                encodings.append(encoding)
        
        if len(encodings) < 1:
            return {
                "success": False,
                "message": "Could not detect a clear face in any of the provided images"
            }
        
        # Average the encodings for more robust recognition
        average_encoding = np.mean(encodings, axis=0)
        
        # Save encoding
        self.known_face_encodings[person_id] = average_encoding
        self._save_encoding(person_id, average_encoding)
        
        return {
            "success": True,
            "message": f"Successfully registered face with {len(encodings)} images",
            "images_used": len(encodings)
        }
    
    def identify_face(self, image: np.ndarray, include_admins: bool = True) -> Dict[str, Any]:
        """
        Identify a face from the known faces database (optimized for speed)
        
        Args:
            image: BGR image containing a face
            include_admins: Whether to also check admin face encodings
        
        Returns:
            Dictionary with person_id, confidence, and status
        """
        # Use fast detection
        face_locations = self.detect_faces_fast(image)
        
        if len(face_locations) == 0:
            # Try again with original size if scaled detection failed
            face_locations = self.detect_faces(image)
        
        if len(face_locations) == 0:
            # Final fallback: use face_recognition library's HOG detector
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image, model='hog')
            
        if len(face_locations) == 0:
            return {
                "success": False,
                "message": "No face detected in the image",
                "person_id": None
            }
        
        if len(face_locations) > 1:
            return {
                "success": False,
                "message": "Multiple faces detected. Please ensure only one face is visible",
                "person_id": None
            }
        
        encoding = self.get_face_encoding(image, face_locations[0])
        if encoding is None:
            return {
                "success": False,
                "message": "Could not encode the detected face",
                "person_id": None
            }
        
        # Combine user encodings with admin encodings if requested
        all_encodings = dict(self.known_face_encodings)
        
        if include_admins:
            # Load admin encodings from admin directory
            admin_dir = Config.ADMIN_ENCODINGS_DIR
            if os.path.exists(admin_dir):
                for filename in os.listdir(admin_dir):
                    if filename.endswith('.pkl'):
                        admin_id = filename[:-4]
                        filepath = os.path.join(admin_dir, filename)
                        try:
                            with open(filepath, 'rb') as f:
                                all_encodings[admin_id] = pickle.load(f)
                        except Exception as e:
                            print(f"Error loading admin encoding for {admin_id}: {e}")
        
        if not all_encodings:
            return {
                "success": False,
                "message": "No registered faces in the system",
                "person_id": None
            }
        
        # Compare with all known faces (users and admins)
        best_match_id = None
        best_match_distance = float('inf')
        
        for pid, known_encoding in all_encodings.items():
            distance = face_recognition.face_distance([known_encoding], encoding)[0]
            if distance < best_match_distance:
                best_match_distance = distance
                best_match_id = pid
        
        # Convert distance to confidence (0-1, higher is better)
        confidence = 1 - best_match_distance
        
        if best_match_distance <= self.tolerance:
            return {
                "success": True,
                "person_id": best_match_id,
                "confidence": round(confidence, 4),
                "message": "Face identified successfully"
            }
        else:
            return {
                "success": False,
                "message": "Face not recognized",
                "person_id": None,
                "confidence": round(confidence, 4)
            }
    
    def verify_face(self, person_id: str, image: np.ndarray) -> Dict[str, Any]:
        """
        Verify if the face in image matches a specific person
        
        Args:
            person_id: ID of person to verify against
            image: BGR image containing a face
        
        Returns:
            Dictionary with verification result
        """
        if person_id not in self.known_face_encodings:
            return {
                "success": False,
                "verified": False,
                "message": f"No registered face for ID: {person_id}"
            }
        
        face_locations = self.detect_faces(image)
        
        if len(face_locations) == 0:
            return {
                "success": False,
                "verified": False,
                "message": "No face detected"
            }
        
        encoding = self.get_face_encoding(image, face_locations[0])
        if encoding is None:
            return {
                "success": False,
                "verified": False,
                "message": "Could not encode face"
            }
        
        known_encoding = self.known_face_encodings[person_id]
        distance = face_recognition.face_distance([known_encoding], encoding)[0]
        confidence = 1 - distance
        
        verified = distance <= self.tolerance
        
        return {
            "success": True,
            "verified": verified,
            "confidence": round(confidence, 4),
            "message": "Face verified" if verified else "Face does not match"
        }
    
    def delete_face(self, person_id: str) -> bool:
        """Delete a registered face"""
        self._delete_encoding(person_id)
        return True
    
    def get_registered_count(self) -> int:
        """Get count of registered faces"""
        return len(self.known_face_encodings)
    
    def is_registered(self, person_id: str) -> bool:
        """Check if a person is registered"""
        return person_id in self.known_face_encodings
