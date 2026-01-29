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
            result = client.table(cls.TABLE_NAME).select(
                "*, users!inner(name, department)"
            ).eq("date", today).order("punch_in", desc=True).execute()
            return result.data if result.data else []
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
            query = client.table(cls.TABLE_NAME).select(
                "*, users!inner(name, department, email)"
            ).gte("date", start_date).lte("date", end_date)
            
            if employee_id:
                query = query.eq("employee_id", employee_id)
            
            result = query.order("date", desc=True).execute()
            return result.data if result.data else []
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
        
        try:
            query = client.table(cls.TABLE_NAME).select("*").gte(
                "date", start_date.isoformat()
            ).lte("date", end_date.isoformat())
            
            if employee_id:
                query = query.eq("employee_id", employee_id)
            
            result = query.execute()
            records = result.data if result.data else []
            
            # Calculate statistics
            total_days = len(records)
            total_hours = sum(r.get('hours_worked', 0) or 0 for r in records)
            complete_days = sum(1 for r in records if r.get('punch_out'))
            
            return {
                "total_days": total_days,
                "complete_days": complete_days,
                "total_hours": round(total_hours, 2),
                "average_hours": round(total_hours / complete_days, 2) if complete_days > 0 else 0
            }
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}
