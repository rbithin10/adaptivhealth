"""
Update Admin Password Script
Run this to update the admin password to "Password123"
"""
from sqlalchemy import text
from app.database import engine
from app.services.auth_service import AuthService

def update_admin_password():
    new_password = "Password123"
    hashed_password = AuthService.hash_password(new_password)
    
    with engine.connect() as conn:
        # First get the admin user_id
        user_result = conn.execute(
            text("SELECT user_id FROM users WHERE email = 'adaptivhealth@gmail.com'")
        )
        user = user_result.fetchone()
        
        if not user:
            print("Admin user not found. Run create_admin.py first.")
            return
        
        user_id = user[0]
        
        # Update the password in auth_credentials table
        result = conn.execute(
            text("""
                UPDATE auth_credentials 
                SET hashed_password = :hashed_password 
                WHERE user_id = :user_id
            """),
            {"hashed_password": hashed_password, "user_id": user_id}
        )
        conn.commit()
        
        if result.rowcount > 0:
            print(f"Password updated for admin (user_id: {user_id})")
            print(f"New password: {new_password}")
        else:
            print("Auth credentials not found for admin. Creating...")
            conn.execute(
                text("""
                    INSERT INTO auth_credentials (user_id, hashed_password, failed_login_attempts)
                    VALUES (:user_id, :hashed_password, 0)
                """),
                {"user_id": user_id, "hashed_password": hashed_password}
            )
            conn.commit()
            print(f"Auth credentials created for admin (user_id: {user_id})")
            print(f"Password: {new_password}")

if __name__ == "__main__":
    update_admin_password()
