from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import hashlib
import secrets
from app.models.database import User, get_db

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# HTTP Bearer for token authentication
security = HTTPBearer()

# Helper functions
def hash_password(password: str) -> str:
    """Simple password hashing using SHA256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((plain_password + salt).encode()).hexdigest() == password_hash
    except:
        return False

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, password: str):
    hashed_password = hash_password(password)
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user

def init_users():
    """Initialize default users if they don't exist"""
    from app.models.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Create default admin user
        admin_user = get_user_by_email(db, "admin@example.com")
        if not admin_user:
            create_user(db, "admin@example.com", "admin123")
            print("✅ Default admin user created: admin@example.com / admin123")
        else:
            print("ℹ️  Default admin user already exists")
        
        # Create Brinks admin user
        brinks_user = get_user_by_email(db, "admin@brinks.com")
        if not brinks_user:
            create_user(db, "admin@brinks.com", "brinks")
            print("✅ Brinks admin user created: admin@brinks.com / brinks")
        else:
            print("ℹ️  Brinks admin user already exists")
    except Exception as e:
        print(f"❌ Error initializing users: {e}")
    finally:
        db.close()