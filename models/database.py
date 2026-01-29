"""
Database Connection Module
Handles Supabase connections for main and admin databases
"""
from supabase import create_client, Client
from typing import Optional
from config import Config


class Database:
    """Main database connection for users and attendance"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get or create Supabase client singleton"""
        if cls._instance is None:
            if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
                return None
            try:
                cls._instance = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            except Exception as e:
                print(f"Failed to connect to main database: {e}")
                return None
        return cls._instance
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if database is connected"""
        return cls.get_client() is not None


class AdminDatabase:
    """Separate database connection for admin data"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get or create Admin Supabase client singleton"""
        if cls._instance is None:
            if not Config.ADMIN_SUPABASE_URL or not Config.ADMIN_SUPABASE_KEY:
                return None
            try:
                cls._instance = create_client(Config.ADMIN_SUPABASE_URL, Config.ADMIN_SUPABASE_KEY)
            except Exception as e:
                print(f"Failed to connect to admin database: {e}")
                return None
        return cls._instance
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if admin database is connected"""
        return cls.get_client() is not None


# SQL to create tables in Supabase (run this in Supabase SQL Editor)
CREATE_TABLES_SQL = """
-- ================================================
-- MAIN DATABASE TABLES (Users & Attendance)
-- ================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department VARCHAR(100),
    is_registered BOOLEAN DEFAULT FALSE,
    registered_by VARCHAR(50),  -- Admin who registered this user
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL REFERENCES users(employee_id),
    date DATE NOT NULL,
    punch_in TIMESTAMP WITH TIME ZONE,
    punch_out TIMESTAMP WITH TIME ZONE,
    confidence_in FLOAT,
    confidence_out FLOAT,
    hours_worked FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(employee_id, date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_attendance_employee_id ON attendance(employee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_users_employee_id ON users(employee_id);

-- ================================================
-- ADMIN DATABASE TABLES (Can be same or separate DB)
-- ================================================

-- Admins table
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',  -- 'admin' or 'super_admin'
    is_active BOOLEAN DEFAULT TRUE,
    is_registered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Admin activity log
CREATE TABLE IF NOT EXISTS admin_activity_log (
    id SERIAL PRIMARY KEY,
    admin_id VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,  -- 'user_registration', 'user_deletion', etc.
    target_employee_id VARCHAR(50),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for admin tables
CREATE INDEX IF NOT EXISTS idx_admins_admin_id ON admins(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_admin_id ON admin_activity_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_created_at ON admin_activity_log(created_at);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_activity_log ENABLE ROW LEVEL SECURITY;

-- Policies (adjust based on your security requirements)
CREATE POLICY "Enable all access" ON users FOR ALL USING (true);
CREATE POLICY "Enable all access" ON attendance FOR ALL USING (true);
CREATE POLICY "Enable all access" ON admins FOR ALL USING (true);
CREATE POLICY "Enable all access" ON admin_activity_log FOR ALL USING (true);
"""
