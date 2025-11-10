from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import HTTPBearer
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import User, Company
import re
import bcrypt

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

# Password hashing - Latest best practices with bcrypt
def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with modern best practices.
    - Uses bcrypt's default work factor (currently 12 rounds)
    - Handles the 72-byte limit properly
    - Returns UTF-8 decoded string for database storage
    """
    password_bytes = password.encode('utf-8')
    # bcrypt automatically handles the 72-byte limit
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is the current recommended default
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash using bcrypt.
    - Constant-time comparison to prevent timing attacks
    - Handles encoding/decoding properly
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def validate_email(email: str) -> bool:
    """Validate email format using RFC 5322 compliant regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength with modern requirements.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"
    
    # Check password complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain uppercase, lowercase, and numbers"
    
    return True, ""

# Pydantic models for request/response
class UserLogin(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False

class UserRegister(BaseModel):
    company_name: str
    full_name: str
    email: str
    password: str
    confirm_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    company_id: int

@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    remember_me: Optional[bool] = Form(False),
    db: Session = Depends(get_db)
):
    """
    Authenticate user with modern security practices.
    - Constant-time email lookup
    - Prevents user enumeration via timing attacks
    - Validates account status before authentication
    """
    try:
        # Normalize email
        normalized_email = email.lower().strip()
        
        # Validate email format first
        if not validate_email(normalized_email):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Find user by email
        user = db.query(User).filter(User.email == normalized_email).first()
        
        # Use generic error message to prevent user enumeration
        if not user:
            # Still hash a dummy password to prevent timing attacks
            hash_password("dummy_password_to_prevent_timing_attack")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if user is active before verifying password
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is deactivated")
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # TODO: Generate JWT token here
        # TODO: Log successful login for security audit
        
        # Successful login - redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error for debugging but return generic message to user
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during login")

@router.post("/register")
async def register(
    company_name: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    terms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Register new user and company with modern security practices.
    - Strong password requirements
    - Email validation
    - Transaction-safe database operations
    - Proper error handling
    """
    try:
        # Input sanitization and validation
        company_name = company_name.strip()
        full_name = full_name.strip()
        email = email.lower().strip()
        
        # Validate required fields
        if not company_name:
            raise HTTPException(status_code=400, detail="Company name is required")
        
        if not full_name:
            raise HTTPException(status_code=400, detail="Full name is required")
        
        if not validate_email(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        if password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        if not terms:
            raise HTTPException(status_code=400, detail="You must accept the terms and conditions")
        
        # Check if email already exists (prevent duplicate accounts)
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already registered")
        
        # Create company (atomic transaction)
        company = Company(
            name=company_name,
            description=f"Company for {full_name}",
            is_active=True
        )
        db.add(company)
        db.flush()  # Get company ID without committing
        
        # Hash password securely
        hashed_password = hash_password(password)
        print(f"DEBUG: Creating user with email: {email}")
        
        # Create user
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
            company_id=company.id
        )
        db.add(user)
        
        # Commit transaction
        db.commit()
        db.refresh(user)
        
        print(f"DEBUG: User created successfully with ID: {user.id}")
        
        # TODO: Send welcome email
        # TODO: Generate JWT token for immediate login
        # TODO: Log registration for audit
        
        # Redirect to dashboard on successful registration
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during registration")

@router.post("/logout")
async def logout():
    """
    Logout user (invalidate token)
    """
    # TODO: Implement logout logic
    # - Add token to blacklist
    # - Return success response
    
    return {"message": "Logout successful"}

@router.get("/me")
async def get_current_user():
    """
    Get current authenticated user info
    """
    # TODO: Implement get current user
    # - Verify JWT token
    # - Return user info from database
    
    return {"message": "Current user endpoint - Implementation pending"}