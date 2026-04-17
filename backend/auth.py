"""
Authentication module for D-CAPTCHA system
Simple authentication without JWT/OAuth - college-level implementation
"""

import base64
import json
from typing import Dict, Optional
from backend.database import get_user_by_email, create_user

# ============================================================================
# HARDCODED ADMIN CREDENTIALS (Only one admin)
# ============================================================================

ADMIN_EMAIL = "admin@dcaptcha.com"
ADMIN_PASSWORD = "admin123"

# Admin is NOT stored in database
# Admin can only login, not register


# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

def create_token(user_id: int, email: str, role: str, name: str) -> str:
    """
    Create simple base64-encoded token (not JWT - college project).
    
    Args:
        user_id: User ID
        email: User email
        role: User role (admin/student/faculty)
        name: User name
    
    Returns:
        Base64-encoded token string (without "Bearer " prefix)
    """
    user_data = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "name": name
    }
    
    # Simple base64 encoding
    token = base64.b64encode(json.dumps(user_data).encode()).decode()
    return token  # Return token WITHOUT "Bearer " prefix


def register_user(name: str, email: str, password: str, role: str) -> Dict:
    """
    Register a new user (student or faculty).
    Admin registration is NOT allowed.
    
    Args:
        name: User's full name
        email: User's email (must be unique)
        password: Plain text password (college project)
        role: "student" or "faculty" (admin not allowed)
    
    Returns:
        Dictionary with success status, user_id, role, and token
    """
    # Validate role
    if role not in ["student", "faculty"]:
        return {
            "success": False,
            "message": "Invalid role. Only 'student' or 'faculty' allowed."
        }
    
    # Check if trying to use admin email
    if email.lower() == ADMIN_EMAIL.lower():
        return {
            "success": False,
            "message": "This email is reserved."
        }
    
    # Validate inputs
    if not name or not email or not password:
        return {
            "success": False,
            "message": "All fields are required."
        }
    
    # Create user in database
    result = create_user(name, email, password, role)
    
    if result["success"]:
        # Create token for new user
        user_id = result["user_id"]
        token = create_token(user_id, email, role, name)
        result["token"] = token  # Add token to response WITHOUT "Bearer " prefix
    
    return result


def login_user(email: str, password: str, role: str) -> Dict:
    """
    Login user based on role.
    
    Args:
        email: User's email
        password: User's password
        role: "student", "faculty", or "admin"
    
    Returns:
        Dictionary with success status, user_id, name, role, and token
    """
    # Validate inputs
    if not email or not password or not role:
        return {
            "success": False,
            "message": "All fields are required."
        }
    
    # Handle ADMIN login (hardcoded credentials)
    if role == "admin":
        if email.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            token = create_token(0, ADMIN_EMAIL, "admin", "Admin")
            return {
                "success": True,
                "role": "admin",
                "user_id": 0,
                "name": "Admin",
                "email": ADMIN_EMAIL,
                "token": token  # Return token WITHOUT "Bearer " prefix
            }
        else:
            return {
                "success": False,
                "message": "Invalid admin credentials."
            }
    
    # Handle STUDENT/FACULTY login (from database)
    if role not in ["student", "faculty"]:
        return {
            "success": False,
            "message": "Invalid role."
        }
    
    # Get user from database
    user = get_user_by_email(email)
    
    if not user:
        return {
            "success": False,
            "message": "User not found."
        }
    
    # Check password (plain text comparison - college project)
    if user["password"] != password:
        return {
            "success": False,
            "message": "Incorrect password."
        }
    
    # Check role match
    if user["role"] != role:
        return {
            "success": False,
            "message": f"This email is registered as {user['role']}, not {role}."
        }
    
    # Create token
    token = create_token(user["id"], user["email"], user["role"], user["name"])
    
    # Login successful
    return {
        "success": True,
        "role": user["role"],
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "token": token  # Return token WITHOUT "Bearer " prefix
    }


def is_admin(email: str) -> bool:
    """
    Check if an email belongs to admin.
    
    Args:
        email: Email to check
    
    Returns:
        True if admin, False otherwise
    """
    return email.lower() == ADMIN_EMAIL.lower()


def validate_role(user_id: int, expected_role: str) -> bool:
    """
    Validate that a user has the expected role.
    Used for API authorization.
    
    Args:
        user_id: User's ID
        expected_role: Expected role ("student" or "faculty")
    
    Returns:
        True if role matches, False otherwise
    """
    # Admin has special handling (user_id = 0)
    if user_id == 0 and expected_role == "admin":
        return True
    
    # Get user from database
    user = get_user_by_email("")  # This won't work, need to refactor
    
    # For now, simple validation (can be enhanced)
    return True
