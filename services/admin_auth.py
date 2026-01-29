"""
Admin Authentication Service
Handles admin face verification for authorization
"""
import time
from typing import Dict, Any, Optional
from config import Config, AdminConfig
from models import AdminModel
from .face_recognition import FaceRecognitionService


class AdminAuthService:
    """
    Admin authentication service using face recognition
    Provides authorization layer before sensitive operations
    """
    
    # Store active admin sessions {session_token: (admin_id, timestamp)}
    _active_sessions: Dict[str, tuple] = {}
    
    def __init__(self):
        """Initialize admin face recognition service with stricter tolerance"""
        self.face_service = FaceRecognitionService(
            encodings_dir=Config.ADMIN_ENCODINGS_DIR,
            tolerance=AdminConfig.ADMIN_RECOGNITION_TOLERANCE
        )
    
    def register_admin(self, admin_id: str, name: str, email: str, 
                       images: list, role: str = "admin") -> Dict[str, Any]:
        """
        Register a new admin with face
        
        Args:
            admin_id: Unique admin identifier
            name: Admin's full name
            email: Admin's email
            images: List of face images (numpy arrays)
            role: 'admin' or 'super_admin'
        
        Returns:
            Registration result
        """
        # Check if this is the first admin (no authorization needed)
        has_admin = AdminModel.has_any_registered_admin()
        
        if has_admin:
            # Only super_admin can register new admins
            # This check should be done at route level with session verification
            pass
        
        # Register face
        face_result = self.face_service.register_face(admin_id, images)
        
        if not face_result['success']:
            return face_result
        
        # Create admin in database
        existing = AdminModel.get_by_admin_id(admin_id)
        if not existing:
            AdminModel.create(admin_id, name, email, role)
        
        # Update registration status
        AdminModel.update_registration_status(admin_id, True)
        
        # Log activity
        AdminModel.log_activity(
            admin_id=admin_id,
            action="admin_registration",
            details={"name": name, "role": role}
        )
        
        return {
            "success": True,
            "message": f"Admin {name} registered successfully",
            "admin_id": admin_id,
            "images_used": face_result.get('images_used', 0)
        }
    
    def authenticate_admin(self, image) -> Dict[str, Any]:
        """
        Authenticate an admin using face recognition
        
        Args:
            image: Face image (numpy array)
        
        Returns:
            Authentication result with session token if successful
        """
        # Identify face
        result = self.face_service.identify_face(image)
        
        if not result['success']:
            return {
                "success": False,
                "authenticated": False,
                "message": result.get('message', 'Face not recognized')
            }
        
        admin_id = result['person_id']
        
        # Verify admin exists and is active
        admin = AdminModel.get_by_admin_id(admin_id)
        if not admin:
            return {
                "success": False,
                "authenticated": False,
                "message": "Admin not found in database"
            }
        
        if not admin.get('is_active', False):
            return {
                "success": False,
                "authenticated": False,
                "message": "Admin account is deactivated"
            }
        
        # Generate session token
        import secrets
        session_token = secrets.token_urlsafe(32)
        
        # Store session
        self._active_sessions[session_token] = (admin_id, time.time())
        
        # Log activity
        AdminModel.log_activity(
            admin_id=admin_id,
            action="admin_authentication",
            details={"confidence": result.get('confidence')}
        )
        
        return {
            "success": True,
            "authenticated": True,
            "admin_id": admin_id,
            "name": admin.get('name'),
            "role": admin.get('role'),
            "confidence": result.get('confidence'),
            "session_token": session_token,
            "expires_in": AdminConfig.ADMIN_SESSION_TIMEOUT,
            "message": f"Welcome, {admin.get('name')}"
        }
    
    def verify_session(self, session_token: str) -> Dict[str, Any]:
        """
        Verify if an admin session is valid
        
        Args:
            session_token: Session token to verify
        
        Returns:
            Verification result
        """
        if not session_token:
            return {
                "valid": False,
                "message": "No session token provided"
            }
        
        if session_token not in self._active_sessions:
            return {
                "valid": False,
                "message": "Invalid session token"
            }
        
        admin_id, timestamp = self._active_sessions[session_token]
        
        # Check if session has expired
        if time.time() - timestamp > AdminConfig.ADMIN_SESSION_TIMEOUT:
            del self._active_sessions[session_token]
            return {
                "valid": False,
                "message": "Session expired. Please re-authenticate."
            }
        
        # Get admin details
        admin = AdminModel.get_by_admin_id(admin_id)
        
        return {
            "valid": True,
            "admin_id": admin_id,
            "name": admin.get('name') if admin else None,
            "role": admin.get('role') if admin else None,
            "remaining_time": int(AdminConfig.ADMIN_SESSION_TIMEOUT - (time.time() - timestamp))
        }
    
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate an admin session (logout)"""
        if session_token in self._active_sessions:
            del self._active_sessions[session_token]
            return True
        return False
    
    def extend_session(self, session_token: str) -> Dict[str, Any]:
        """Extend an active session"""
        if session_token not in self._active_sessions:
            return {
                "success": False,
                "message": "Invalid session token"
            }
        
        admin_id, _ = self._active_sessions[session_token]
        self._active_sessions[session_token] = (admin_id, time.time())
        
        return {
            "success": True,
            "message": "Session extended",
            "expires_in": AdminConfig.ADMIN_SESSION_TIMEOUT
        }
    
    def is_first_admin(self) -> bool:
        """Check if this would be the first admin (no auth required)"""
        return not AdminModel.has_any_registered_admin()
    
    def get_all_admins(self) -> list:
        """Get list of all admins"""
        return AdminModel.get_all()
    
    def deactivate_admin(self, admin_id: str, deactivated_by: str) -> Dict[str, Any]:
        """Deactivate an admin account"""
        # Delete face encoding
        self.face_service.delete_face(admin_id)
        
        # Deactivate in database
        success = AdminModel.deactivate(admin_id)
        
        if success:
            # Log activity
            AdminModel.log_activity(
                admin_id=deactivated_by,
                action="admin_deactivation",
                target_employee_id=admin_id
            )
        
        return {
            "success": success,
            "message": f"Admin {admin_id} deactivated" if success else "Failed to deactivate"
        }
    
    def log_user_registration(self, admin_id: str, employee_id: str, 
                              employee_name: str) -> None:
        """Log when an admin registers a new user"""
        AdminModel.log_activity(
            admin_id=admin_id,
            action="user_registration",
            target_employee_id=employee_id,
            details={"employee_name": employee_name}
        )
    
    def get_activity_log(self, admin_id: str = None, limit: int = 50) -> list:
        """Get admin activity log"""
        return AdminModel.get_activity_log(admin_id, limit)


# Singleton instance
_admin_auth_service: Optional[AdminAuthService] = None


def get_admin_auth_service() -> AdminAuthService:
    """Get or create AdminAuthService singleton"""
    global _admin_auth_service
    if _admin_auth_service is None:
        _admin_auth_service = AdminAuthService()
    return _admin_auth_service
