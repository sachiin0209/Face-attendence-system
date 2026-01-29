"""
User Model
Handles all user-related database operations
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from .database import Database


class UserModel:
    """User database operations"""
    
    TABLE_NAME = "users"
    
    @classmethod
    def _get_client(cls):
        return Database.get_client()
    
    @classmethod
    def create(cls, employee_id: str, name: str, email: str, 
               department: str = None, registered_by: str = None) -> Optional[Dict[str, Any]]:
        """
        Create a new user
        
        Args:
            employee_id: Unique employee identifier
            name: Full name
            email: Email address
            department: Department name
            registered_by: Admin ID who registered this user
        
        Returns:
            Created user record or None
        """
        client = cls._get_client()
        if not client:
            return None
        
        user_data = {
            "employee_id": employee_id,
            "name": name,
            "email": email,
            "department": department,
            "registered_by": registered_by,
            "is_registered": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = client.table(cls.TABLE_NAME).insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    @classmethod
    def get_by_employee_id(cls, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get user by employee ID"""
        client = cls._get_client()
        if not client:
            return None
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq("employee_id", employee_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by database ID"""
        client = cls._get_client()
        if not client:
            return None
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Get all users"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []
    
    @classmethod
    def get_registered(cls) -> List[Dict[str, Any]]:
        """Get all users with registered faces"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").eq("is_registered", True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching registered users: {e}")
            return []
    
    @classmethod
    def update_registration_status(cls, employee_id: str, is_registered: bool) -> bool:
        """Update user's face registration status"""
        client = cls._get_client()
        if not client:
            return False
        
        try:
            result = client.table(cls.TABLE_NAME).update({
                "is_registered": is_registered,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("employee_id", employee_id).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    @classmethod
    def delete(cls, employee_id: str) -> bool:
        """Delete a user"""
        client = cls._get_client()
        if not client:
            return False
        
        try:
            # First delete attendance records
            client.table("attendance").delete().eq("employee_id", employee_id).execute()
            # Then delete user
            result = client.table(cls.TABLE_NAME).delete().eq("employee_id", employee_id).execute()
            return len(result.data) > 0 if result.data else False
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        """Search users by name or employee ID"""
        client = cls._get_client()
        if not client:
            return []
        
        try:
            result = client.table(cls.TABLE_NAME).select("*").or_(
                f"name.ilike.%{query}%,employee_id.ilike.%{query}%"
            ).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error searching users: {e}")
            return []
