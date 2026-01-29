"""
Routes Package
"""
from .main import main_bp
from .admin import admin_bp
from .users import users_bp
from .attendance import attendance_bp

__all__ = ['main_bp', 'admin_bp', 'users_bp', 'attendance_bp']
