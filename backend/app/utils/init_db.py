# -*- coding: utf-8 -*-
from ..utils.database import Base, engine, SessionLocal
from ..schemas.database_models import User, DetectionTask, ParagraphResult
from sqlalchemy import text
from ..services.auth import get_password_hash

def init_db():
    """
    Initialize database
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Ensure new columns for existing SQLite tables (idempotent)
    try:
        with engine.connect() as conn:
            # orders.license_token
            result = conn.execute(text("PRAGMA table_info(orders)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if "license_token" not in existing_cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN license_token TEXT"))
                print("Added column orders.license_token")
    except Exception as e:
        print(f"DB schema ensure step skipped/failed: {e}")
    
    # Create admin user
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin_password = get_password_hash("admin123")
            admin = User(
                email="admin@example.com",
                username="Admin",
                hashed_password=admin_password
            )
            db.add(admin)
            db.commit()
            print("Admin user created")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 