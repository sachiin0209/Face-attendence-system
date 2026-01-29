"""
Application Settings and Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Main application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Supabase settings - Main database for users and attendance
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Supabase settings - Admin database (can be same or different)
    ADMIN_SUPABASE_URL = os.getenv('ADMIN_SUPABASE_URL', '') or os.getenv('SUPABASE_URL', '')
    ADMIN_SUPABASE_KEY = os.getenv('ADMIN_SUPABASE_KEY', '') or os.getenv('SUPABASE_KEY', '')
    
    # Face recognition settings
    FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', '0.6'))
    FACE_DETECTION_MODEL = os.getenv('FACE_DETECTION_MODEL', 'hog')  # 'hog' for CPU, 'cnn' for GPU
    
    # Anti-spoofing settings
    BLINK_THRESHOLD = float(os.getenv('BLINK_THRESHOLD', '0.25'))
    SPOOF_DETECTION_ENABLED = os.getenv('SPOOF_DETECTION_ENABLED', 'True').lower() == 'true'
    
    # Directory settings
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FACE_ENCODINGS_DIR = os.path.join(BASE_DIR, 'data', 'face_encodings')
    ADMIN_ENCODINGS_DIR = os.path.join(BASE_DIR, 'data', 'admin_encodings')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
    
    # Ensure directories exist
    @classmethod
    def init_directories(cls):
        os.makedirs(cls.FACE_ENCODINGS_DIR, exist_ok=True)
        os.makedirs(cls.ADMIN_ENCODINGS_DIR, exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)


class AdminConfig:
    """Admin-specific configuration"""
    
    # Admin session timeout (in seconds)
    ADMIN_SESSION_TIMEOUT = int(os.getenv('ADMIN_SESSION_TIMEOUT', '300'))  # 5 minutes
    
    # Admin authorization required for registration
    REQUIRE_ADMIN_AUTH = os.getenv('REQUIRE_ADMIN_AUTH', 'True').lower() == 'true'
    
    # Maximum admin authorization attempts
    MAX_AUTH_ATTEMPTS = int(os.getenv('MAX_AUTH_ATTEMPTS', '3'))
    
    # Admin face recognition tolerance (stricter than regular)
    ADMIN_RECOGNITION_TOLERANCE = float(os.getenv('ADMIN_RECOGNITION_TOLERANCE', '0.5'))


# Initialize directories on import
Config.init_directories()
