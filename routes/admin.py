"""
Admin Routes
Handles admin registration, authentication, and management
"""
from flask import Blueprint, request, jsonify
from services.admin_auth import get_admin_auth_service
from services import AntiSpoofingService, ImagePreprocessor
from utils.helpers import decode_base64_image
from config import Config, AdminConfig

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Initialize services
antispoof_service = AntiSpoofingService()
preprocessor = ImagePreprocessor()


@admin_bp.route('/check-first', methods=['GET'])
def check_first_admin():
    """Check if this is the first admin setup"""
    admin_service = get_admin_auth_service()
    
    return jsonify({
        "success": True,
        "is_first_admin": admin_service.is_first_admin(),
        "message": "First admin setup required" if admin_service.is_first_admin() else "Admin system initialized"
    })


@admin_bp.route('/register', methods=['POST'])
def register_admin():
    """
    Register a new admin
    First admin doesn't need authorization, subsequent admins need super_admin auth
    
    Expected JSON:
    {
        "admin_id": "ADMIN001",
        "name": "Admin Name",
        "email": "admin@example.com",
        "role": "admin",
        "images": ["base64_image1", "base64_image2", ...],
        "session_token": "token" (required if not first admin)
    }
    """
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        # Validate required fields
        required_fields = ['admin_id', 'name', 'email', 'images']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Check if this is first admin
        is_first = admin_service.is_first_admin()
        
        if not is_first:
            # Verify session token for existing admin
            session_token = data.get('session_token')
            session = admin_service.verify_session(session_token)
            
            if not session.get('valid'):
                return jsonify({
                    "success": False,
                    "message": "Admin authorization required. Please authenticate first.",
                    "requires_auth": True
                }), 401
            
            # Only super_admin can register new admins
            if session.get('role') != 'super_admin':
                return jsonify({
                    "success": False,
                    "message": "Only super admin can register new admins"
                }), 403
        
        if len(data['images']) < 3:
            return jsonify({
                "success": False,
                "message": "Please provide at least 3 images for registration"
            }), 400
        
        # Decode and preprocess images
        images = []
        for img_base64 in data['images']:
            try:
                image = decode_base64_image(img_base64)
                if image is not None:
                    image = preprocessor.preprocess_for_recognition(image)
                    images.append(image)
            except Exception as e:
                continue
        
        if len(images) < 3:
            return jsonify({
                "success": False,
                "message": "Could not process enough valid images"
            }), 400
        
        # Anti-spoofing check
        if Config.SPOOF_DETECTION_ENABLED:
            texture_check = antispoof_service.analyze_texture(images[0])
            if not texture_check.get("is_real", True):
                return jsonify({
                    "success": False,
                    "message": "Spoof detection failed. Please use a real camera."
                }), 400
        
        # Register admin
        role = 'super_admin' if is_first else data.get('role', 'admin')
        
        result = admin_service.register_admin(
            admin_id=data['admin_id'],
            name=data['name'],
            email=data['email'],
            images=images,
            role=role
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Admin registration failed: {str(e)}"
        }), 500


@admin_bp.route('/authenticate', methods=['POST'])
def authenticate_admin():
    """
    Authenticate admin using face recognition
    
    Expected JSON:
    {
        "image": "base64_image",
        "spoof_frames": ["base64_frame1", ...] (optional)
    }
    """
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        if 'image' not in data or not data['image']:
            return jsonify({
                "success": False,
                "message": "No image provided"
            }), 400
        
        # Check if there are any admins
        if admin_service.is_first_admin():
            return jsonify({
                "success": False,
                "message": "No admin registered. Please set up the first admin.",
                "requires_setup": True
            }), 400
        
        # Decode and preprocess image
        image = decode_base64_image(data['image'])
        if image is None:
            return jsonify({
                "success": False,
                "message": "Could not decode image"
            }), 400
        
        image = preprocessor.preprocess_for_recognition(image)
        
        # Anti-spoofing check if frames provided
        if Config.SPOOF_DETECTION_ENABLED and 'spoof_frames' in data:
            frames = []
            for frame_b64 in data['spoof_frames']:
                frame = decode_base64_image(frame_b64)
                if frame is not None:
                    frames.append(frame)
            
            if len(frames) >= 5:
                spoof_result = antispoof_service.comprehensive_spoof_check(frames)
                if not spoof_result.get('overall_is_real', True):
                    return jsonify({
                        "success": False,
                        "message": "Liveness check failed. Please use a live camera."
                    }), 400
        
        # Authenticate
        result = admin_service.authenticate_admin(image)
        
        if not result['success']:
            return jsonify(result), 401
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Authentication failed: {str(e)}"
        }), 500


@admin_bp.route('/verify-session', methods=['POST'])
def verify_session():
    """
    Verify admin session token
    
    Expected JSON:
    {
        "session_token": "token"
    }
    """
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        session_token = data.get('session_token')
        result = admin_service.verify_session(session_token)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "valid": False,
            "message": str(e)
        }), 500


@admin_bp.route('/extend-session', methods=['POST'])
def extend_session():
    """Extend admin session"""
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        session_token = data.get('session_token')
        result = admin_service.extend_session(session_token)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@admin_bp.route('/logout', methods=['POST'])
def logout():
    """Logout admin (invalidate session)"""
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        session_token = data.get('session_token')
        admin_service.invalidate_session(session_token)
        
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@admin_bp.route('/list', methods=['GET'])
def list_admins():
    """Get list of all admins"""
    try:
        admin_service = get_admin_auth_service()
        admins = admin_service.get_all_admins()
        
        return jsonify({
            "success": True,
            "admins": admins
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@admin_bp.route('/activity-log', methods=['GET'])
def get_activity_log():
    """Get admin activity log"""
    try:
        admin_service = get_admin_auth_service()
        admin_id = request.args.get('admin_id')
        limit = int(request.args.get('limit', 50))
        
        logs = admin_service.get_activity_log(admin_id, limit)
        
        return jsonify({
            "success": True,
            "logs": logs
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@admin_bp.route('/deactivate/<admin_id>', methods=['POST'])
def deactivate_admin(admin_id):
    """Deactivate an admin account"""
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        # Verify session
        session_token = data.get('session_token')
        session = admin_service.verify_session(session_token)
        
        if not session.get('valid'):
            return jsonify({
                "success": False,
                "message": "Admin authorization required"
            }), 401
        
        if session.get('role') != 'super_admin':
            return jsonify({
                "success": False,
                "message": "Only super admin can deactivate admins"
            }), 403
        
        result = admin_service.deactivate_admin(admin_id, session.get('admin_id'))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
