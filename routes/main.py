"""
Main Routes
Handles main pages and health check
"""
from flask import Blueprint, render_template, jsonify
from datetime import datetime
from services import FaceRecognitionService
from services.admin_auth import get_admin_auth_service
from models import Database, AdminDatabase
from config import Config

main_bp = Blueprint('main', __name__)

# Initialize services
face_service = FaceRecognitionService()


@main_bp.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')


@main_bp.route('/register')
def register_page():
    """User registration page (requires admin auth)"""
    return render_template('register.html')


@main_bp.route('/attendance')
def attendance_page():
    """Attendance marking page"""
    return render_template('attendance.html')


@main_bp.route('/dashboard')
def dashboard_page():
    """Dashboard page"""
    return render_template('dashboard.html')


@main_bp.route('/admin')
def admin_page():
    """Admin management page"""
    return render_template('admin.html')


@main_bp.route('/admin/setup')
def admin_setup_page():
    """First admin setup page"""
    admin_service = get_admin_auth_service()
    if not admin_service.is_first_admin():
        return render_template('admin.html')
    return render_template('admin_setup.html')


@main_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    admin_service = get_admin_auth_service()
    
    return jsonify({
        "status": "healthy",
        "database": "connected" if Database.is_connected() else "not configured",
        "admin_database": "connected" if AdminDatabase.is_connected() else "not configured",
        "registered_users": face_service.get_registered_count(),
        "registered_admins": admin_service.face_service.get_registered_count(),
        "has_admin": not admin_service.is_first_admin(),
        "timestamp": datetime.now().isoformat()
    })


@main_bp.route('/api/system/status', methods=['GET'])
def system_status():
    """Detailed system status"""
    admin_service = get_admin_auth_service()
    
    return jsonify({
        "success": True,
        "system": {
            "version": "1.0.0",
            "face_detection_model": Config.FACE_DETECTION_MODEL,
            "spoof_detection_enabled": Config.SPOOF_DETECTION_ENABLED,
            "admin_auth_required": not admin_service.is_first_admin()
        },
        "database": {
            "main": "connected" if Database.is_connected() else "not configured",
            "admin": "connected" if AdminDatabase.is_connected() else "not configured"
        },
        "statistics": {
            "registered_users": face_service.get_registered_count(),
            "registered_admins": admin_service.face_service.get_registered_count()
        }
    })
