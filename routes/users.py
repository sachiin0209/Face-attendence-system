"""
User Routes
Handles user registration with admin authorization
"""
from flask import Blueprint, request, jsonify
from services import FaceRecognitionService, AntiSpoofingService, ImagePreprocessor
from services.admin_auth import get_admin_auth_service
from models import UserModel
from utils.helpers import decode_base64_image
from config import Config, AdminConfig

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

# Initialize services
face_service = FaceRecognitionService()
antispoof_service = AntiSpoofingService()
preprocessor = ImagePreprocessor()


@users_bp.route('/register', methods=['POST'])
def register_user():
    """
    Register a new user's face
    REQUIRES ADMIN AUTHORIZATION FIRST
    
    Expected JSON:
    {
        "employee_id": "EMP001",
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering",
        "images": ["base64_image1", "base64_image2", ...],
        "admin_session_token": "token"  (required)
    }
    """
    try:
        data = request.json
        admin_service = get_admin_auth_service()
        
        # Validate required fields
        required_fields = ['employee_id', 'name', 'email', 'images', 'admin_session_token']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Verify admin session (ADMIN AUTHORIZATION REQUIRED)
        session_token = data.get('admin_session_token')
        session = admin_service.verify_session(session_token)
        
        if not session.get('valid'):
            return jsonify({
                "success": False,
                "message": "Admin authorization required. Admin must scan their face first.",
                "requires_admin_auth": True
            }), 401
        
        admin_id = session.get('admin_id')
        
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
        
        # Register face
        result = face_service.register_face(data['employee_id'], images)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Save user to database
        existing_user = UserModel.get_by_employee_id(data['employee_id'])
        if not existing_user:
            UserModel.create(
                employee_id=data['employee_id'],
                name=data['name'],
                email=data['email'],
                department=data.get('department', ''),
                registered_by=admin_id
            )
        
        UserModel.update_registration_status(data['employee_id'], True)
        
        # Log admin activity
        admin_service.log_user_registration(
            admin_id=admin_id,
            employee_id=data['employee_id'],
            employee_name=data['name']
        )
        
        return jsonify({
            "success": True,
            "message": f"Successfully registered {data['name']}",
            "employee_id": data['employee_id'],
            "registered_by": admin_id,
            "images_used": result.get('images_used', len(images))
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Registration failed: {str(e)}"
        }), 500


@users_bp.route('/identify', methods=['POST'])
def identify_user():
    """
    Identify a user from face image
    
    Expected JSON:
    {
        "image": "base64_image"
    }
    """
    try:
        data = request.json
        
        if 'image' not in data:
            return jsonify({
                "success": False,
                "message": "No image provided"
            }), 400
        
        # Decode and preprocess image
        image = decode_base64_image(data['image'])
        if image is None:
            return jsonify({
                "success": False,
                "message": "Could not decode image"
            }), 400
        
        image = preprocessor.preprocess_for_recognition(image)
        
        # Identify face
        result = face_service.identify_face(image)
        
        if result['success']:
            # Get user details
            user = UserModel.get_by_employee_id(result['person_id'])
            if user:
                result['user'] = {
                    'name': user.get('name'),
                    'email': user.get('email'),
                    'department': user.get('department')
                }
            result['employee_id'] = result.pop('person_id')
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Identification failed: {str(e)}"
        }), 500


@users_bp.route('/list', methods=['GET'])
def list_users():
    """Get all users"""
    try:
        users = UserModel.get_all()
        
        return jsonify({
            "success": True,
            "users": users
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@users_bp.route('/registered', methods=['GET'])
def list_registered_users():
    """Get all users with registered faces"""
    try:
        users = UserModel.get_registered()
        
        return jsonify({
            "success": True,
            "users": users
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@users_bp.route('/<employee_id>', methods=['GET'])
def get_user(employee_id):
    """Get user details"""
    try:
        user = UserModel.get_by_employee_id(employee_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        return jsonify({
            "success": True,
            "user": user
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@users_bp.route('/<employee_id>', methods=['DELETE'])
def delete_user(employee_id):
    """
    Delete a user (requires admin authorization)
    
    Expected JSON:
    {
        "admin_session_token": "token"
    }
    """
    try:
        data = request.json or {}
        admin_service = get_admin_auth_service()
        
        # Verify admin session
        session_token = data.get('admin_session_token')
        session = admin_service.verify_session(session_token)
        
        if not session.get('valid'):
            return jsonify({
                "success": False,
                "message": "Admin authorization required",
                "requires_admin_auth": True
            }), 401
        
        # Delete face encoding
        face_service.delete_face(employee_id)
        
        # Delete from database
        UserModel.delete(employee_id)
        
        return jsonify({
            "success": True,
            "message": f"User {employee_id} deleted successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@users_bp.route('/search', methods=['GET'])
def search_users():
    """Search users by name or employee ID"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                "success": False,
                "message": "Search query required"
            }), 400
        
        users = UserModel.search(query)
        
        return jsonify({
            "success": True,
            "users": users
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
