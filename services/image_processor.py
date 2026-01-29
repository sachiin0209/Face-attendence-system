"""
Image Preprocessor Service
Handles image preprocessing for varying lighting conditions
"""
import cv2
import numpy as np


class ImagePreprocessor:
    """
    Image preprocessing for handling varying lighting conditions
    """
    
    @staticmethod
    def normalize_lighting(image: np.ndarray) -> np.ndarray:
        """
        Normalize image lighting using CLAHE
        (Contrast Limited Adaptive Histogram Equalization)
        
        Args:
            image: BGR image
        
        Returns:
            Lighting-normalized image
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # Split channels
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l)
        
        # Merge channels
        lab_clahe = cv2.merge([l_clahe, a, b])
        
        # Convert back to BGR
        result = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        
        return result
    
    @staticmethod
    def adjust_gamma(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
        """
        Adjust image gamma for brightness correction
        
        Args:
            image: BGR image
            gamma: Gamma value (< 1 brightens, > 1 darkens)
        
        Returns:
            Gamma-adjusted image
        """
        inv_gamma = 1.0 / gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in np.arange(0, 256)
        ]).astype("uint8")
        
        return cv2.LUT(image, table)
    
    @staticmethod
    def auto_brightness(image: np.ndarray) -> np.ndarray:
        """
        Automatically adjust brightness based on image histogram
        
        Args:
            image: BGR image
        
        Returns:
            Brightness-adjusted image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        # Target brightness
        target = 127
        
        if mean_brightness < 50:  # Too dark
            gamma = 0.5
        elif mean_brightness > 200:  # Too bright
            gamma = 1.5
        else:
            gamma = target / mean_brightness if mean_brightness > 0 else 1.0
        
        # Clamp gamma
        gamma = max(0.3, min(2.0, gamma))
        
        return ImagePreprocessor.adjust_gamma(image, gamma)
    
    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """
        Remove noise from image
        
        Args:
            image: BGR image
        
        Returns:
            Denoised image
        """
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    
    @staticmethod
    def preprocess_for_recognition(image: np.ndarray) -> np.ndarray:
        """
        Full preprocessing pipeline for face recognition
        
        Args:
            image: BGR image
        
        Returns:
            Preprocessed image ready for face recognition
        """
        # Auto brightness adjustment
        image = ImagePreprocessor.auto_brightness(image)
        
        # Normalize lighting
        image = ImagePreprocessor.normalize_lighting(image)
        
        # Denoise
        image = ImagePreprocessor.denoise(image)
        
        return image
    
    @staticmethod
    def resize_for_processing(image: np.ndarray, max_size: int = 800) -> np.ndarray:
        """
        Resize image for faster processing while maintaining aspect ratio
        
        Args:
            image: BGR image
            max_size: Maximum dimension
        
        Returns:
            Resized image
        """
        height, width = image.shape[:2]
        
        if max(height, width) <= max_size:
            return image
        
        if height > width:
            new_height = max_size
            new_width = int(width * (max_size / height))
        else:
            new_width = max_size
            new_height = int(height * (max_size / width))
        
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
