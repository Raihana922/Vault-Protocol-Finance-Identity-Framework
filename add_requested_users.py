from app import app
from models import db, User
from werkzeug.security import generate_password_hash

def add_requested_users():
    with app.app_context():
        print("Injecting requested users into Finance DB...")
        
        users_to_add = [
            {
                "email": "25177@yenepoya.edu.in",
                "name": "Yenepoya Admin",
                "role": "Admin",
                "pass": "Rai@yenepoya."
            },
            {
                "email": "raihanaanzar2@gmail.com",
                "name": "Raihana Anzar 2",
                "role": "Analyst",
                "pass": "Rai@yenepoya."
            },
            {
                "email": "raihanaanzar@gmail.com",
                "name": "Raihana Anzar",
                "role": "Auditor",
                "pass": "Rai@yenepoya."
            }
        ]
        
        for u_data in users_to_add:
            existing_user = User.query.filter_by(email=u_data["email"]).first()
            if existing_user:
                print(f"  [SKIPPED] User {u_data['email']} already exists.")
                # Optionally update password/role if requested, but let's be safe
                continue
                
            password = u_data["pass"]
            pass_prefix = password[:2] if len(password) >= 2 else password
            pass_suffix = password[-2:] if len(password) >= 2 else password
            
            new_user = User(
                full_name=u_data["name"],
                email=u_data["email"],
                password_hash=generate_password_hash(password, method='scrypt'),
                pass_prefix=pass_prefix,
                pass_suffix=pass_suffix,
                role=u_data["role"]
            )
            db.session.add(new_user)
            print(f"  [OK] Added {u_data['role']}: {u_data['email']}")
            
        db.session.commit()
        print("\nInjection complete.")

if __name__ == "__main__":
    add_requested_users()
