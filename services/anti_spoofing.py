"""
Anti-Spoofing Service
Detects presentation attacks (photos, videos, masks)
"""
import cv2
import numpy as np
import face_recognition
from scipy.spatial import distance as dist
from typing import List, Dict, Any
from config import Config


class AntiSpoofingService:
    """
    Anti-spoofing detection service using multiple techniques:
    1. Blink detection (liveness check)
    2. Texture analysis (detect printed photos)
    3. Motion analysis (detect static images)
    """
    
    def __init__(self):
        # Eye aspect ratio threshold for blink detection
        self.EYE_AR_THRESH = Config.BLINK_THRESHOLD
        self.EYE_AR_CONSEC_FRAMES = 2
        
        # For motion detection
        self.prev_frame = None
        self.motion_threshold = 1000
        
        # Load face detector
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
        
        Args:
            frames: List of consecutive frames
        
        Returns:
            Dictionary with blink_detected boolean and details
        """
        ear_values = []
        
        for frame in frames:
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
        Uses Laplacian and Sobel variance analysis
        
        Args:
            image: BGR image
        
        Returns:
            Dictionary with is_real boolean and confidence
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect face region
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(faces) == 0:
            return {
                "success": False,
                "is_real": False,
                "message": "No face detected for texture analysis"
            }
        
        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        # Calculate Laplacian variance (blur/sharpness detection)
        laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
        
        # Calculate texture variance using Sobel
        sobelx = cv2.Sobel(face_roi, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(face_roi, cv2.CV_64F, 0, 1, ksize=3)
        texture_var = np.var(sobelx) + np.var(sobely)
        
        # High-frequency analysis using FFT
        f_transform = np.fft.fft2(face_roi)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        high_freq_energy = np.mean(magnitude[magnitude.shape[0]//4:3*magnitude.shape[0]//4,
                                              magnitude.shape[1]//4:3*magnitude.shape[1]//4])
        
        # Thresholds (tuned empirically)
        # Real faces typically have higher texture variance
        is_real = laplacian_var > 100 and texture_var > 500
        
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
        Run comprehensive anti-spoofing checks
        
        Args:
            frames: List of consecutive frames (at least 5 recommended)
        
        Returns:
            Dictionary with overall spoof detection result
        """
        if len(frames) < 5:
            return {
                "success": False,
                "is_real": False,
                "message": "Need at least 5 frames for spoof detection"
            }
        
        results = {
            "texture_check": self.analyze_texture(frames[-1]),
            "motion_checks": [],
            "overall_is_real": False
        }
        
        # Check motion across frames
        self.reset_motion_detector()
        motion_count = 0
        for frame in frames:
            motion_result = self.detect_motion(frame)
            results["motion_checks"].append(motion_result)
            if motion_result.get("motion_detected"):
                motion_count += 1
        
        # Determine if real based on multiple factors
        texture_real = results["texture_check"].get("is_real", False)
        has_motion = motion_count >= 2
        
        # Final decision
        results["overall_is_real"] = texture_real and has_motion
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
                reasons.append("insufficient motion detected")
            results["message"] = f"Possible spoof: {', '.join(reasons)}"
        
        return results
