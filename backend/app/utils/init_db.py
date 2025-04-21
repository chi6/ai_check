# -*- coding: utf-8 -*-
from ..utils.database import Base, engine, SessionLocal
from ..schemas.database_models import User, DetectionTask, ParagraphResult
from ..services.auth import get_password_hash

def init_db():
    """
    Initialize database
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    
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