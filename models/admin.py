"""
Admin Model
Handles all admin-related database operations
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from .database import AdminDatabase


class AdminModel:
    """Admin database operations"""
    
    TABLE_NAME = "admins"
    LOG_TABLE = "admin_activity_log"
    
    @classmethod
    def _get_client(cls):
        return AdminDatabase.get_client()
    
    @classmethod
    def create(cls, admin_id: str, name: str, email: str, 
               role: str = "admin") -> Optional[Dict[str, Any]]:
        """
        Create a new admin
        
        Args:
            admin_id: Unique admin identifier
            name: Full name
            email: Email address
            role: 'admin' or 'super_admin'
        
        Returns:
            Created admin record or None
        """
        client = cls._get_client()
        if not client:
            return None
        
        admin_data = {
            "admin_id": admin_id,
            "name": name,
            "email": email,
            "role": role,
            "is_active": True,
            "is_registered": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = client.table(cls.TABLE_NAME).insert(admin_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating admin: {e}")
            return None
    
    @classmethod
    def get_by_admin_id(cls, admin_id: str) -> Optional[Dict[str, Any]]:
        """Get admin by admin ID"""
        client = cls._get_client()
        if not client:
            return None
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq("admin_id", admin_id).eq("is_active", True).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching admin: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Get all admins"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching admins: {e}")
            return []
    
    @classmethod
    def get_active_admins(cls) -> List[Dict[str, Any]]:
        """Get all active admins with registered faces"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq(
                "is_active", True
            ).eq("is_registered", True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching active admins: {e}")
            return []
    
    @classmethod
    def update_registration_status(cls, admin_id: str, is_registered: bool) -> bool:
        """Update admin's face registration status"""
        client = cls._get_client()
        if not client:
            return False
        
        try:
            result = client.table(cls.TABLE_NAME).update({
                "is_registered": is_registered,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("admin_id", admin_id).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error updating admin: {e}")
            return False
    
    @classmethod
    def deactivate(cls, admin_id: str) -> bool:
        """Deactivate an admin (soft delete)"""
        client = cls._get_client()
        if not client:
            return False
        
        try:
            result = client.table(cls.TABLE_NAME).update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("admin_id", admin_id).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error deactivating admin: {e}")
            return False
    
    @classmethod
    def log_activity(cls, admin_id: str, action: str, 
                     target_employee_id: str = None, details: dict = None) -> bool:
        """
        Log admin activity
        
        Args:
            admin_id: Admin who performed the action
            action: Action type (e.g., 'user_registration', 'user_deletion')
            target_employee_id: Employee affected by the action
            details: Additional details as JSON
        
        Returns:
            Success status
        """
        client = cls._get_client()
        if not client:
            return False
        
        log_data = {
            "admin_id": admin_id,
            "action": action,
            "target_employee_id": target_employee_id,
            "details": details or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            client.table(cls.LOG_TABLE).insert(log_data).execute()
            return True
        except Exception as e:
            print(f"Error logging admin activity: {e}")
            return False
    
    @classmethod
    def get_activity_log(cls, admin_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get admin activity log"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            query = client.table(cls.LOG_TABLE).select("*")
            if admin_id:
                query = query.eq("admin_id", admin_id)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching activity log: {e}")
            return []
    
    @classmethod
    def has_any_registered_admin(cls) -> bool:
        """Check if there's at least one registered admin"""
        client = cls._get_client()
        if not client:
            return False
        
        try:
            result = client.table(cls.TABLE_NAME).select("id").eq(
                "is_registered", True
            ).eq("is_active", True).limit(1).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error checking for registered admins: {e}")
            return False
