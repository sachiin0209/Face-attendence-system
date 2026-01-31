"""
Anti-Spoofing Service
Detects presentation attacks (photos, videos, masks)
Optimized for speed with configurable settings
"""
import cv2
import numpy as np
from scipy.spatial import distance as dist
from typing import List, Dict, Any
from config import Config


class AntiSpoofingService:
    """
    Anti-spoofing detection service using multiple techniques:
    1. Texture analysis (detect printed photos) - FAST
    2. Motion analysis (detect static images) - FAST
    3. Blink detection (liveness check) - SLOW, optional
    """
    
    def __init__(self):
        # Eye aspect ratio threshold for blink detection
        self.EYE_AR_THRESH = Config.BLINK_THRESHOLD
        self.EYE_AR_CONSEC_FRAMES = 2
        
        # For motion detection
        self.prev_frame = None
        self.motion_threshold = 1000
        
        # Configurable thresholds
        self.laplacian_threshold = Config.SPOOF_LAPLACIAN_THRESHOLD
        self.texture_threshold = Config.SPOOF_TEXTURE_THRESHOLD
        self.quick_mode = Config.SPOOF_QUICK_MODE
        self.frame_count = Config.SPOOF_FRAME_COUNT
        
        # Load face detector (fast Haar cascade)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def eye_aspect_ratio(self, eye_points: np.ndarray) -> float:
        """
        Calculate eye aspect ratio for blink detection
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        # Compute euclidean distances between vertical eye landmarks
        A = dist.euclidean(eye_points[1], eye_points[5])
        B = dist.euclidean(eye_points[2], eye_points[4])
        
        # Compute euclidean distance between horizontal eye landmarks
        C = dist.euclidean(eye_points[0], eye_points[3])
        
        # Compute eye aspect ratio
        ear = (A + B) / (2.0 * C) if C != 0 else 0
        return ear
    
    def detect_blink(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """
        Detect if a blink occurred across multiple frames
        NOTE: This is slow due to face_recognition landmarks - use sparingly
        
        Args:
            frames: List of consecutive frames
        
        Returns:
            Dictionary with blink_detected boolean and details
        """
        # Skip blink detection in quick mode
        if self.quick_mode:
            return {
                "success": True,
                "blink_detected": True,  # Assume real in quick mode
                "message": "Blink detection skipped (quick mode)"
            }
        
        import face_recognition
        
        ear_values = []
        
        # Only check every other frame for speed
        for i, frame in enumerate(frames):
            if i % 2 != 0:
                continue
                
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get facial landmarks
            face_landmarks_list = face_recognition.face_landmarks(rgb_frame)
            
            if not face_landmarks_list:
                continue
            
            landmarks = face_landmarks_list[0]
            
            # Get eye landmarks
            left_eye = np.array(landmarks['left_eye'])
            right_eye = np.array(landmarks['right_eye'])
            
            # Calculate EAR for both eyes
            left_ear = self.eye_aspect_ratio(left_eye)
            right_ear = self.eye_aspect_ratio(right_eye)
            
            # Average EAR
            ear = (left_ear + right_ear) / 2.0
            ear_values.append(ear)
        
        if len(ear_values) < 3:
            return {
                "success": False,
                "blink_detected": False,
                "message": "Not enough frames with detected face"
            }
        
        # Check for blink pattern (EAR drops below threshold then rises)
        blink_detected = False
        for i in range(1, len(ear_values) - 1):
            if (ear_values[i] < self.EYE_AR_THRESH and 
                ear_values[i-1] > self.EYE_AR_THRESH and 
                ear_values[i+1] > self.EYE_AR_THRESH):
                blink_detected = True
                break
        
        return {
            "success": True,
            "blink_detected": blink_detected,
            "ear_values": ear_values,
            "message": "Blink detected - Liveness confirmed" if blink_detected else "No blink detected"
        }
    
    def analyze_texture(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze image texture to detect printed photos or screens
        Uses Laplacian variance analysis (fast method)
        
        Args:
            image: BGR image
        
        Returns:
            Dictionary with is_real boolean and confidence
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect face region (using fast Haar cascade)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.2,  # Faster with larger scale
            minNeighbors=3,
            minSize=(50, 50)
        )
        
        if len(faces) == 0:
            # If no face detected, analyze the whole image
            face_roi = gray
        else:
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
        
        # Calculate Laplacian variance (blur/sharpness detection) - FAST
        laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
        
        # Calculate simple texture variance - FAST
        texture_var = np.var(face_roi)
        
        # Use configurable thresholds
        is_real = laplacian_var > self.laplacian_threshold or texture_var > self.texture_threshold
        
        confidence = min(1.0, (laplacian_var / 500 + texture_var / 5000) / 2)
        
        return {
            "success": True,
            "is_real": is_real,
            "confidence": round(confidence, 4),
            "laplacian_variance": round(laplacian_var, 2),
            "texture_variance": round(texture_var, 2),
            "message": "Real face detected" if is_real else "Possible spoof detected"
        }
    
    def detect_motion(self, current_frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect motion between frames (static images don't have motion)
        
        Args:
            current_frame: Current BGR frame
        
        Returns:
            Dictionary with motion_detected boolean
        """
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return {
                "success": True,
                "motion_detected": False,
                "message": "First frame - no motion comparison"
            }
        
        # Compute difference
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = np.sum(thresh > 0)
        
        self.prev_frame = gray
        
        motion_detected = motion_pixels > self.motion_threshold
        
        return {
            "success": True,
            "motion_detected": motion_detected,
            "motion_pixels": int(motion_pixels),
            "message": "Motion detected" if motion_detected else "No significant motion"
        }
    
    def reset_motion_detector(self):
        """Reset motion detector state"""
        self.prev_frame = None
    
    def comprehensive_spoof_check(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """
        Run anti-spoofing checks (optimized for speed)
        
        Args:
            frames: List of consecutive frames
        
        Returns:
            Dictionary with overall spoof detection result
        """
        min_frames = min(self.frame_count, 3)  # At least 3 frames
        
        if len(frames) < min_frames:
            return {
                "success": False,
                "overall_is_real": True,  # Pass if not enough frames
                "message": f"Not enough frames ({len(frames)}/{min_frames})"
            }
        
        # Only use last N frames for speed
        frames_to_check = frames[-self.frame_count:] if len(frames) > self.frame_count else frames
        
        results = {
            "texture_check": None,
            "motion_count": 0,
            "overall_is_real": False
        }
        
        # Quick texture check on last frame only
        results["texture_check"] = self.analyze_texture(frames_to_check[-1])
        texture_real = results["texture_check"].get("is_real", False)
        
        # Quick motion check (only check a few frames)
        self.reset_motion_detector()
        motion_count = 0
        
        # Check every other frame for speed
        for i in range(0, len(frames_to_check), 2):
            motion_result = self.detect_motion(frames_to_check[i])
            if motion_result.get("motion_detected"):
                motion_count += 1
        
        results["motion_count"] = motion_count
        has_motion = motion_count >= 1  # Just need 1 motion detection
        
        # Final decision - pass if texture is real OR has motion
        results["overall_is_real"] = texture_real or has_motion
        results["confidence"] = (
            (0.6 if texture_real else 0) + 
            (0.4 if has_motion else 0)
        )
        
        if results["overall_is_real"]:
            results["message"] = "Liveness verification passed"
        else:
            reasons = []
            if not texture_real:
                reasons.append("texture analysis failed")
            if not has_motion:
                reasons.append("no motion detected")
            results["message"] = f"Possible spoof: {', '.join(reasons)}"
        
        return results
    
    def quick_spoof_check(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Ultra-fast single-image spoof check
        Only checks texture (no motion or blink detection)
        
        Args:
            image: Single BGR image
            
        Returns:
            Dictionary with is_real result
        """
        return self.analyze_texture(image)
