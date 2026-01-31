"""
Face Authentication Attendance System
Main Flask Application Entry Point
"""
from flask import Flask
from config import Config


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register blueprints
    from routes import main_bp, admin_bp, users_bp, attendance_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(attendance_bp)
    
    return app


# Create application instance
app = create_app()


if __name__ == '__main__':
    from services import FaceRecognitionService
    from services.admin_auth import get_admin_auth_service
    from models import Database, AdminDatabase
    
    face_service = FaceRecognitionService()
    admin_service = get_admin_auth_service()
    
    print("=" * 60)
    print("  Face Authentication Attendance System")
    print("=" * 60)
    print(f"  Detection Model:   {Config.FACE_DETECTION_MODEL.upper()}")
    print(f"  Registered Users:  {face_service.get_registered_count()}")
    print(f"  Registered Admins: {admin_service.face_service.get_registered_count()}")
    print(f"  Main Database:     {'Connected' if Database.is_connected() else 'Not configured'}")
    print(f"  Admin Database:    {'Connected' if AdminDatabase.is_connected() else 'Not configured'}")
    print(f"  First Admin Setup: {'Required' if admin_service.is_first_admin() else 'Complete'}")
    print(f"  Spoof Detection:   {'Enabled' if Config.SPOOF_DETECTION_ENABLED else 'Disabled'}")
    print(f"  Quick Mode:        {'Enabled' if Config.SPOOF_QUICK_MODE else 'Disabled'}")
    print("=" * 60)
    print(f"  Server starting on http://{Config.HOST}:{Config.PORT}")
    print("=" * 60)
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
