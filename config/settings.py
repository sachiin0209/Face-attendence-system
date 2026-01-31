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
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    
    # Supabase settings - Main database for users and attendance
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Supabase settings - Admin database (can be same or different)
    ADMIN_SUPABASE_URL = os.getenv('ADMIN_SUPABASE_URL', '') or os.getenv('SUPABASE_URL', '')
    ADMIN_SUPABASE_KEY = os.getenv('ADMIN_SUPABASE_KEY', '') or os.getenv('SUPABASE_KEY', '')
    
    # Face detection settings
    FACE_DETECTION_MODEL = os.getenv('FACE_DETECTION_MODEL', 'yolo')  # 'yolo', 'hog', or 'cnn'
    
    # YOLO settings
    YOLO_MODEL_SIZE = os.getenv('YOLO_MODEL_SIZE', 'n')  # n, s, m, l
    YOLO_CONFIDENCE = float(os.getenv('YOLO_CONFIDENCE', '0.5'))
    
    # Face recognition settings
    FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', '0.5'))
    FACE_NUM_JITTERS = int(os.getenv('FACE_NUM_JITTERS', '1'))
    
    # Anti-spoofing settings
    BLINK_THRESHOLD = float(os.getenv('BLINK_THRESHOLD', '0.25'))
    SPOOF_DETECTION_ENABLED = os.getenv('SPOOF_DETECTION_ENABLED', 'True').lower() == 'true'
    SPOOF_QUICK_MODE = os.getenv('SPOOF_QUICK_MODE', 'True').lower() == 'true'
    SPOOF_FRAME_COUNT = int(os.getenv('SPOOF_FRAME_COUNT', '5'))
    SPOOF_LAPLACIAN_THRESHOLD = float(os.getenv('SPOOF_LAPLACIAN_THRESHOLD', '50'))
    SPOOF_TEXTURE_THRESHOLD = float(os.getenv('SPOOF_TEXTURE_THRESHOLD', '200'))
    
    # Performance settings
    IMAGE_SCALE_FACTOR = float(os.getenv('IMAGE_SCALE_FACTOR', '0.5'))
    MAX_IMAGE_DIMENSION = int(os.getenv('MAX_IMAGE_DIMENSION', '640'))
    CACHE_ENCODINGS = os.getenv('CACHE_ENCODINGS', 'True').lower() == 'true'
    
    # Directory settings
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    FACE_ENCODINGS_DIR = os.path.join(BASE_DIR, 'data', 'face_encodings')
    ADMIN_ENCODINGS_DIR = os.path.join(BASE_DIR, 'data', 'admin_encodings')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
    MODELS_DIR = os.path.join(BASE_DIR, 'models_data')
    
    # Ensure directories exist
    @classmethod
    def init_directories(cls):
        os.makedirs(cls.FACE_ENCODINGS_DIR, exist_ok=True)
        os.makedirs(cls.ADMIN_ENCODINGS_DIR, exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.MODELS_DIR, exist_ok=True)


class AdminConfig:
    """Admin-specific configuration"""
    
    # Admin session timeout (in seconds)
    ADMIN_SESSION_TIMEOUT = int(os.getenv('ADMIN_SESSION_TIMEOUT', '300'))  # 5 minutes
    
    # Admin authorization required for registration
    REQUIRE_ADMIN_AUTH = os.getenv('REQUIRE_ADMIN_AUTH', 'True').lower() == 'true'
    
    # Maximum admin authorization attempts
    MAX_AUTH_ATTEMPTS = int(os.getenv('MAX_AUTH_ATTEMPTS', '3'))
    
    # Admin face recognition tolerance (stricter than regular)
    ADMIN_RECOGNITION_TOLERANCE = float(os.getenv('ADMIN_RECOGNITION_TOLERANCE', '0.45'))


# Initialize directories on import
Config.init_directories()
