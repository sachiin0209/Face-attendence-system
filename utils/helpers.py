"""
Helper Utility Functions
"""
import cv2
import numpy as np
import base64
from typing import Optional


def decode_base64_image(base64_string: str) -> Optional[np.ndarray]:
    """
    Decode base64 image string to numpy array (OpenCV BGR format)
    
    Args:
        base64_string: Base64 encoded image string
    
    Returns:
        OpenCV BGR image or None if decoding fails
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        img_data = base64.b64decode(base64_string)
        
        # Convert to numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        
        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return image
    except Exception as e:
        print(f"Error decoding base64 image: {e}")
        return None


def encode_image_to_base64(image: np.ndarray, format: str = '.jpg') -> Optional[str]:
    """
    Encode OpenCV image to base64 string
    
    Args:
        image: OpenCV BGR image
        format: Image format (e.g., '.jpg', '.png')
    
    Returns:
        Base64 encoded string or None if encoding fails
    """
    try:
        # Encode image
        _, buffer = cv2.imencode(format, image)
        
        # Convert to base64
        base64_string = base64.b64encode(buffer).decode('utf-8')
        
        # Add data URL prefix
        mime_type = 'image/jpeg' if format == '.jpg' else 'image/png'
        return f"data:{mime_type};base64,{base64_string}"
    except Exception as e:
        print(f"Error encoding image to base64: {e}")
        return None


def format_datetime(dt_string: str) -> str:
    """Format datetime string for display"""
    from datetime import datetime
    try:
        if dt_string.endswith('Z'):
            dt_string = dt_string[:-1] + '+00:00'
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_string


def calculate_hours_worked(punch_in: str, punch_out: str) -> float:
    """Calculate hours worked between punch in and punch out"""
    from datetime import datetime
    try:
        if punch_in.endswith('Z'):
            punch_in = punch_in[:-1] + '+00:00'
        if punch_out.endswith('Z'):
            punch_out = punch_out[:-1] + '+00:00'
        
        dt_in = datetime.fromisoformat(punch_in)
        dt_out = datetime.fromisoformat(punch_out)
        
        delta = dt_out - dt_in
        return round(delta.total_seconds() / 3600, 2)
    except:
        return 0.0
