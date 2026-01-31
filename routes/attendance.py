"""
Attendance Routes
Handles punch-in/punch-out and attendance reporting
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from services import FaceRecognitionService, AntiSpoofingService, ImagePreprocessor
from models import UserModel, AttendanceModel, AdminModel
from utils.helpers import decode_base64_image
from config import Config

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

# Initialize services
face_service = FaceRecognitionService()
antispoof_service = AntiSpoofingService()
preprocessor = ImagePreprocessor()


@attendance_bp.route('/mark', methods=['POST'])
def mark_attendance():
    """
    Unified attendance marking - automatically detects punch-in or punch-out
    
    Expected JSON:
    {
        "image": "base64_image",
        "spoof_frames": ["base64_frame1", "base64_frame2", ...] (optional)
    }
    
    Logic:
    - If no punch-in today → Record punch-in
    - If already punched-in → Record punch-out
    - If punch-out within 10-20 seconds of punch-in → Discard attendance
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        if 'image' not in data or not data['image']:
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
                        "message": "Liveness check failed. Please ensure you're using a live camera.",
                        "spoof_details": spoof_result
                    }), 400
        
        # Identify face (includes admins)
        identify_result = face_service.identify_face(image, include_admins=True)
        
        if not identify_result['success']:
            return jsonify(identify_result), 400
        
        employee_id = identify_result['person_id']
        confidence = identify_result.get('confidence', 0)
        
        # Get user or admin name
        user = UserModel.get_by_employee_id(employee_id)
        if user:
            user_name = user.get('name', employee_id)
            department = user.get('department')
        else:
            # Check if it's an admin
            admin = AdminModel.get_by_admin_id(employee_id)
            if admin:
                user_name = admin.get('name', employee_id)
                department = 'Admin'
            else:
                user_name = employee_id
                department = None
        
        # Check current attendance status and auto-determine action
        existing_record = AttendanceModel.get_today_record(employee_id)
        
        if not existing_record or not existing_record.get('punch_in'):
            # No punch-in today → Record punch-in
            attendance_result = AttendanceModel.record_punch_in(employee_id, confidence)
            
            if attendance_result and 'error' in attendance_result:
                return jsonify({
                    "success": False,
                    "message": attendance_result['error'],
                    "employee_id": employee_id
                }), 400
            
            return jsonify({
                "success": True,
                "message": f"Punch-in recorded for {user_name}",
                "action": "Punch In",
                "employee_id": employee_id,
                "name": user_name,
                "department": department,
                "confidence": confidence,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        elif existing_record.get('punch_out'):
            # Already punched out today
            return jsonify({
                "success": False,
                "message": f"Attendance already complete for {user_name} today",
                "employee_id": employee_id,
                "name": user_name
            }), 400
        
        else:
            # Has punch-in but no punch-out → Record punch-out
            # First check if punch-out is within 10-20 seconds of punch-in (discard if so)
            attendance_result = AttendanceModel.record_punch_out_with_validation(
                employee_id, 
                confidence,
                min_duration_seconds=20  # Minimum 20 seconds between punch-in and punch-out
            )
            
            if attendance_result and 'error' in attendance_result:
                return jsonify({
                    "success": False,
                    "message": attendance_result['error'],
                    "employee_id": employee_id
                }), 400
            
            if attendance_result and attendance_result.get('discarded'):
                return jsonify({
                    "success": False,
                    "message": f"Attendance discarded - punch-out too soon after punch-in (within {attendance_result.get('duration_seconds', 0):.0f} seconds)",
                    "employee_id": employee_id,
                    "name": user_name
                }), 400
            
            hours_worked = attendance_result.get('hours_worked', 0) if attendance_result else 0
            
            return jsonify({
                "success": True,
                "message": f"Punch-out recorded for {user_name}",
                "action": "Punch Out",
                "employee_id": employee_id,
                "name": user_name,
                "department": department,
                "confidence": confidence,
                "hours_worked": hours_worked,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Attendance failed: {str(e)}"
        }), 500


@attendance_bp.route('/punch-in', methods=['POST'])
def punch_in():
    """
    Record punch-in for identified user
    
    Expected JSON:
    {
        "image": "base64_image",
        "spoof_frames": ["base64_frame1", "base64_frame2", ...] (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        if 'image' not in data or not data['image']:
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
                        "message": "Liveness check failed. Please ensure you're using a live camera.",
                        "spoof_details": spoof_result
                    }), 400
        
        # Identify face (includes admins)
        identify_result = face_service.identify_face(image, include_admins=True)
        
        if not identify_result['success']:
            return jsonify(identify_result), 400
        
        employee_id = identify_result['person_id']
        confidence = identify_result.get('confidence', 0)
        
        # Record punch-in
        attendance_result = AttendanceModel.record_punch_in(employee_id, confidence)
        
        if attendance_result and 'error' in attendance_result:
            return jsonify({
                "success": False,
                "message": attendance_result['error'],
                "employee_id": employee_id
            }), 400
        
        # Get user or admin name
        user = UserModel.get_by_employee_id(employee_id)
        if user:
            user_name = user.get('name', employee_id)
            department = user.get('department')
        else:
            # Check if it's an admin
            admin = AdminModel.get_by_admin_id(employee_id)
            if admin:
                user_name = admin.get('name', employee_id)
                department = 'Admin'
            else:
                user_name = employee_id
                department = None
        
        return jsonify({
            "success": True,
            "message": f"Punch-in recorded for {user_name}",
            "employee_id": employee_id,
            "name": user_name,
            "department": department,
            "confidence": confidence,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Punch-in failed: {str(e)}"
        }), 500


@attendance_bp.route('/punch-out', methods=['POST'])
def punch_out():
    """
    Record punch-out for identified user
    
    Expected JSON:
    {
        "image": "base64_image",
        "spoof_frames": ["base64_frame1", "base64_frame2", ...] (optional)
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        if 'image' not in data or not data['image']:
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
                        "message": "Liveness check failed. Please ensure you're using a live camera."
                    }), 400
        
        # Identify face (includes admins)
        identify_result = face_service.identify_face(image, include_admins=True)
        
        if not identify_result['success']:
            return jsonify(identify_result), 400
        
        employee_id = identify_result['person_id']
        confidence = identify_result.get('confidence', 0)
        
        # Record punch-out
        attendance_result = AttendanceModel.record_punch_out(employee_id, confidence)
        
        if attendance_result and 'error' in attendance_result:
            return jsonify({
                "success": False,
                "message": attendance_result['error'],
                "employee_id": employee_id
            }), 400
        
        # Get user or admin name
        user = UserModel.get_by_employee_id(employee_id)
        if user:
            user_name = user.get('name', employee_id)
            department = user.get('department')
        else:
            # Check if it's an admin
            admin = AdminModel.get_by_admin_id(employee_id)
            if admin:
                user_name = admin.get('name', employee_id)
                department = 'Admin'
            else:
                user_name = employee_id
                department = None
        
        hours_worked = attendance_result.get('hours_worked', 0) if attendance_result else 0
        
        return jsonify({
            "success": True,
            "message": f"Punch-out recorded for {user_name}",
            "employee_id": employee_id,
            "name": user_name,
            "department": department,
            "confidence": confidence,
            "hours_worked": hours_worked,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Punch-out failed: {str(e)}"
        }), 500


@attendance_bp.route('/today', methods=['GET'])
def get_today_attendance():
    """Get all attendance records for today"""
    try:
        records = AttendanceModel.get_all_today()
        
        return jsonify({
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "records": records
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@attendance_bp.route('/history/<employee_id>', methods=['GET'])
def get_attendance_history(employee_id):
    """Get attendance history for an employee"""
    try:
        limit = int(request.args.get('limit', 30))
        records = AttendanceModel.get_history(employee_id, limit)
        
        return jsonify({
            "success": True,
            "employee_id": employee_id,
            "records": records
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@attendance_bp.route('/report', methods=['GET'])
def get_attendance_report():
    """
    Get attendance report for a date range
    
    Query params:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - employee_id: Optional employee filter
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        
        if not start_date or not end_date:
            return jsonify({
                "success": False,
                "message": "start_date and end_date are required"
            }), 400
        
        records = AttendanceModel.get_report(start_date, end_date, employee_id)
        
        return jsonify({
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "records": records
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@attendance_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get attendance statistics
    
    Query params:
    - employee_id: Optional employee filter
    - days: Number of days (default 30)
    """
    try:
        employee_id = request.args.get('employee_id')
        days = int(request.args.get('days', 30))
        
        stats = AttendanceModel.get_statistics(employee_id, days)
        
        return jsonify({
            "success": True,
            "employee_id": employee_id,
            "period_days": days,
            "statistics": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@attendance_bp.route('/status/<employee_id>', methods=['GET'])
def get_today_status(employee_id):
    """Get today's attendance status for an employee"""
    try:
        record = AttendanceModel.get_today_record(employee_id)
        
        if not record:
            return jsonify({
                "success": True,
                "status": "not_punched_in",
                "message": "Not punched in today"
            })
        
        if record.get('punch_out'):
            return jsonify({
                "success": True,
                "status": "completed",
                "punch_in": record.get('punch_in'),
                "punch_out": record.get('punch_out'),
                "hours_worked": record.get('hours_worked'),
                "message": "Attendance complete for today"
            })
        else:
            return jsonify({
                "success": True,
                "status": "punched_in",
                "punch_in": record.get('punch_in'),
                "message": "Punched in, waiting for punch out"
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
