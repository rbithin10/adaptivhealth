"""
Script to create an admin account in the database.
"""

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.auth_credential import AuthCredential
from app.services.auth_service import pwd_context
from datetime import datetime, timezone

# Ensure all tables exist
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Check if admin already exists
    existing_admin = db.query(User).filter(
        User.email == "adaptivhealth@gmail.com"
    ).first()
    
    if existing_admin:
        print(f"✗ Admin user already exists with ID: {existing_admin.user_id}")
        db.close()
        exit(1)
    
    # Create admin user
    admin_user = User(
        email="adaptivhealth@gmail.com",
        full_name="Adaptiv Health Admin",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(admin_user)
    db.flush()  # Flush to get the user_id
    
    # Create auth credential with hashed password
    hashed_password = pwd_context.hash("Password123")
    
    auth_credential = AuthCredential(
        user_id=admin_user.user_id,
        hashed_password=hashed_password,
        failed_login_attempts=0,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(auth_credential)
    
    # Commit all changes
    db.commit()
    
    print("✓ Admin account created successfully!")
    print(f"  Email: adaptivhealth@gmail.com")
    print(f"  Password: Password123")
    print(f"  Role: admin")
    print(f"  User ID: {admin_user.user_id}")
    
except Exception as e:
    db.rollback()
    print(f"✗ Error creating admin account: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    db.close()
