"""
Attendance Model
Handles all attendance-related database operations
"""
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from .database import Database


class AttendanceModel:
    """Attendance database operations"""
    
    TABLE_NAME = "attendance"
    
    @classmethod
    def _get_client(cls):
        return Database.get_client()
    
    @classmethod
    def record_punch_in(cls, employee_id: str, confidence: float = None) -> Dict[str, Any]:
        """
        Record punch-in time for an employee
        
        Args:
            employee_id: Employee identifier
            confidence: Face recognition confidence score
        
        Returns:
            Attendance record or error
        """
        client = cls._get_client()
        if not client:
            return {"error": "Database not connected"}
        
        today = date.today().isoformat()
        now = datetime.utcnow()
        
        # Check if already punched in today
        existing = cls.get_today_record(employee_id)
        if existing and existing.get('punch_in'):
            return {"error": "Already punched in today", "record": existing}
        
        attendance_data = {
            "employee_id": employee_id,
            "date": today,
            "punch_in": now.isoformat(),
            "created_at": now.isoformat()
        }
        
        try:
            result = client.table(cls.TABLE_NAME).insert(attendance_data).execute()
            return result.data[0] if result.data else {"error": "Failed to record"}
        except Exception as e:
            print(f"Error recording punch-in: {e}")
            return {"error": str(e)}
    
    @classmethod
    def record_punch_out(cls, employee_id: str, confidence: float = None) -> Dict[str, Any]:
        """
        Record punch-out time for an employee
        
        Args:
            employee_id: Employee identifier
            confidence: Face recognition confidence score
        
        Returns:
            Updated attendance record or error
        """
        client = cls._get_client()
        if not client:
            return {"error": "Database not connected"}
        
        now = datetime.utcnow()
        
        # Check if punched in today
        existing = cls.get_today_record(employee_id)
        if not existing:
            return {"error": "No punch-in record found for today"}
        if existing.get('punch_out'):
            return {"error": "Already punched out today", "record": existing}
        
        # Calculate hours worked
        punch_in_str = existing['punch_in']
        if punch_in_str.endswith('Z'):
            punch_in_str = punch_in_str[:-1] + '+00:00'
        punch_in_time = datetime.fromisoformat(punch_in_str)
        hours_worked = (now - punch_in_time.replace(tzinfo=None)).total_seconds() / 3600
        
        try:
            result = client.table(cls.TABLE_NAME).update({
                "punch_out": now.isoformat(),
                "hours_worked": round(hours_worked, 2)
            }).eq("id", existing['id']).execute()
            
            return result.data[0] if result.data else {"error": "Failed to update"}
        except Exception as e:
            print(f"Error recording punch-out: {e}")
            return {"error": str(e)}
    
    @classmethod
    def record_punch_out_with_validation(cls, employee_id: str, confidence: float = None,
                                          min_duration_seconds: int = 20) -> Dict[str, Any]:
        """
        Record punch-out with validation for minimum duration.
        If punch-out is within min_duration_seconds of punch-in, discard the attendance.
        
        Args:
            employee_id: Employee identifier
            confidence: Face recognition confidence score
            min_duration_seconds: Minimum seconds between punch-in and punch-out (default 20)
        
        Returns:
            Updated attendance record, discarded status, or error
        """
        client = cls._get_client()
        if not client:
            return {"error": "Database not connected"}
        
        now = datetime.utcnow()
        
        # Check if punched in today
        existing = cls.get_today_record(employee_id)
        if not existing:
            return {"error": "No punch-in record found for today"}
        if existing.get('punch_out'):
            return {"error": "Already punched out today", "record": existing}
        
        # Calculate time difference
        punch_in_str = existing['punch_in']
        if punch_in_str.endswith('Z'):
            punch_in_str = punch_in_str[:-1] + '+00:00'
        punch_in_time = datetime.fromisoformat(punch_in_str)
        duration_seconds = (now - punch_in_time.replace(tzinfo=None)).total_seconds()
        
        # Check if within minimum duration (10-20 seconds as per requirement)
        if duration_seconds < min_duration_seconds:
            # Delete this attendance record as it's too short
            try:
                client.table(cls.TABLE_NAME).delete().eq("id", existing['id']).execute()
                return {
                    "discarded": True,
                    "duration_seconds": duration_seconds,
                    "message": f"Attendance discarded - duration was only {duration_seconds:.0f} seconds"
                }
            except Exception as e:
                print(f"Error discarding attendance: {e}")
                return {"error": f"Failed to discard: {str(e)}"}
        
        # Calculate hours worked
        hours_worked = duration_seconds / 3600
        
        try:
            result = client.table(cls.TABLE_NAME).update({
                "punch_out": now.isoformat(),
                "hours_worked": round(hours_worked, 2)
            }).eq("id", existing['id']).execute()
            
            if result.data:
                result_data = result.data[0]
                result_data['hours_worked'] = round(hours_worked, 2)
                return result_data
            return {"error": "Failed to update"}
        except Exception as e:
            print(f"Error recording punch-out: {e}")
            return {"error": str(e)}
    
    @classmethod
    def get_today_record(cls, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get today's attendance record for an employee"""
        client = cls._get_client()
        if not client:
            return None
        
        today = date.today().isoformat()
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq(
                "employee_id", employee_id
            ).eq("date", today).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching today's record: {e}")
            return None
    
    @classmethod
    def get_history(cls, employee_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get attendance history for an employee"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq(
                "employee_id", employee_id
            ).order("date", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []
    
    @classmethod
    def get_all_today(cls) -> List[Dict[str, Any]]:
        """Get all attendance records for today"""
        client = cls._get_client()
        if not client:
            return []
        
        today = date.today().isoformat()
        
        try:
            # First get all attendance records without join (to include admins)
            result = client.table(cls.TABLE_NAME).select("*").eq(
                "date", today
            ).order("punch_in", desc=True).execute()
            
            records = result.data if result.data else []
            
            # Enrich with user/admin info
            from models import UserModel, AdminModel
            for record in records:
                employee_id = record.get('employee_id')
                user = UserModel.get_by_employee_id(employee_id)
                if user:
                    record['name'] = user.get('name', employee_id)
                    record['department'] = user.get('department', '-')
                else:
                    # Check if admin
                    admin = AdminModel.get_by_admin_id(employee_id)
                    if admin:
                        record['name'] = admin.get('name', employee_id)
                        record['department'] = 'Admin'
                    else:
                        record['name'] = employee_id
                        record['department'] = '-'
            
            return records
        except Exception as e:
            print(f"Error fetching today's records: {e}")
            return []
    
    @classmethod
    def get_report(cls, start_date: str, end_date: str, 
                   employee_id: str = None) -> List[Dict[str, Any]]:
        """Get attendance report for a date range"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            query = client.table(cls.TABLE_NAME).select("*").gte(
                "date", start_date
            ).lte("date", end_date)
            
            if employee_id:
                query = query.eq("employee_id", employee_id)
            
            result = query.order("date", desc=True).execute()
            records = result.data if result.data else []
            
            # Enrich with user/admin info
            from models import UserModel, AdminModel
            for record in records:
                emp_id = record.get('employee_id')
                user = UserModel.get_by_employee_id(emp_id)
                if user:
                    record['name'] = user.get('name', emp_id)
                    record['department'] = user.get('department', '-')
                else:
                    admin = AdminModel.get_by_admin_id(emp_id)
                    if admin:
                        record['name'] = admin.get('name', emp_id)
                        record['department'] = 'Admin'
                    else:
                        record['name'] = emp_id
                        record['department'] = '-'
            
            return records
        except Exception as e:
            print(f"Error fetching report: {e}")
            return []
    
    @classmethod
    def get_statistics(cls, employee_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get attendance statistics"""
        client = cls._get_client()
        if not client:
            return {}
        
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        today = date.today().isoformat()
        
        try:
            # Get records for the period
            query = client.table(cls.TABLE_NAME).select("*").gte(
                "date", start_date.isoformat()
            ).lte("date", end_date.isoformat())
            
            if employee_id:
                query = query.eq("employee_id", employee_id)
            
            result = query.execute()
            records = result.data if result.data else []
            
            # Get today's records separately
            today_result = client.table(cls.TABLE_NAME).select("*").eq("date", today).execute()
            today_records = today_result.data if today_result.data else []
            
            # Calculate statistics
            total_days = len(records)
            total_hours = sum(r.get('hours_worked', 0) or 0 for r in records)
            complete_days = sum(1 for r in records if r.get('punch_out'))
            
            # Today's stats
            present_today = len(today_records)  # Anyone who punched in today
            completed_today = sum(1 for r in today_records if r.get('punch_out'))
            
            return {
                "total_days": total_days,
                "complete_days": complete_days,
                "total_hours": round(total_hours, 2),
                "average_hours": round(total_hours / complete_days, 2) if complete_days > 0 else 0,
                "present_today": present_today,
                "completed_today": completed_today
            }
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}
