
import sys
import os
import uuid
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import sync_engine as engine, User
from rbac_system.repository import SQLAlchemyRBACRepository
from rbac_system.engine import RBACEngine

def seed():
    print("Seeding RBAC...")
    repo = SQLAlchemyRBACRepository(engine)
    rbac = RBACEngine(repo)
    
    # Create roles
    try:
        admin_role = rbac.create_role("Admin", "Full system access")
        print(f"Created role: {admin_role.name}")
    except Exception as e:
        print(f"Role 'Admin' might already exist: {e}")
        admin_role = rbac.get_role_by_name("Admin")

    try:
        manager_role = rbac.create_role("Manager", "Can manage tasks and trainees")
        print(f"Created role: {manager_role.name}")
    except Exception as e:
        print(f"Role 'Manager' might already exist: {e}")

    try:
        trainee_role = rbac.create_role("Trainee", "Can view and submit tasks")
        print(f"Created role: {trainee_role.name}")
    except Exception as e:
        print(f"Role 'Trainee' might already exist: {e}")

    # Assign Admin role to the specific user ID reporting 403
    target_user_id = "28974fb5-43d5-46b7-a456-35b29273dc44"
    
    # Check if user exists in our DB
    with Session(engine) as session:
        user = session.query(User).filter(User.id == uuid.UUID(target_user_id)).first()
        if user:
            print(f"Found user: {user.username}")
            try:
                rbac.assign_role_to_user(target_user_id, admin_role.id)
                print(f"Assigned 'Admin' role to user {user.username}")
            except Exception as e:
                print(f"Role might already be assigned: {e}")
        else:
            print(f"User with ID {target_user_id} not found in database. Please ensure they have logged in at least once.")

if __name__ == "__main__":
    seed()
