#!/usr/bin/env python3
"""
Create initial admin user for RazZ Backend Security System.

This script creates the first admin user for the system.
"""
import asyncio
import os
import sys
import getpass
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session, create_db_and_tables
from app.services.user_service import UserService
from app.models.user import UserCreate


async def create_admin_user():
    """Create the initial admin user."""
    print("🔐 RazZ Backend - Create Admin User")
    print("=" * 40)
    
    # Ensure database tables exist
    await create_db_and_tables()
    
    async with async_session() as session:
        user_service = UserService(session)
        
        # Check if any users exist
        existing_users = await user_service.get_users(limit=1)
        if existing_users:
            print("⚠️  Users already exist in the database.")
            response = input("Do you want to create another admin user? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return
        
        print("\nEnter admin user details:")
        
        # Get user input
        while True:
            email = input("Email: ").strip()
            if email and "@" in email:
                # Check if email already exists
                existing_user = await user_service.get_user_by_email(email)
                if existing_user:
                    print("❌ Email already exists. Please use a different email.")
                    continue
                break
            print("❌ Please enter a valid email address.")
        
        while True:
            username = input("Username: ").strip()
            if len(username) >= 3:
                # Check if username already exists
                existing_user = await user_service.get_user_by_username(username)
                if existing_user:
                    print("❌ Username already exists. Please use a different username.")
                    continue
                break
            print("❌ Username must be at least 3 characters long.")
        
        full_name = input("Full Name (optional): ").strip() or None
        
        while True:
            password = getpass.getpass("Password (min 8 characters): ")
            if len(password) >= 8:
                break
            print("❌ Password must be at least 8 characters long.")
        
        while True:
            confirm_password = getpass.getpass("Confirm Password: ")
            if password == confirm_password:
                break
            print("❌ Passwords do not match.")
        
        try:
            # Create admin user
            user_create = UserCreate(
                email=email,
                username=username,
                full_name=full_name,
                password=password,
                is_active=True,
                is_superuser=True
            )
            
            admin_user = await user_service.create_user(user_create)
            
            print("\n✅ Admin user created successfully!")
            print(f"   ID: {admin_user.id}")
            print(f"   Email: {admin_user.email}")
            print(f"   Username: {admin_user.username}")
            print(f"   Full Name: {admin_user.full_name}")
            print(f"   Created: {admin_user.created_at}")
            
            print("\n🚀 You can now login to the system with these credentials.")
            
        except Exception as e:
            print(f"\n❌ Error creating admin user: {e}")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
