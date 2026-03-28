# Purpose: Helper functions to manage WhatsApp user onboarding state and personas.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.config import settings
from engine.core.models import WhatsAppUser

# Setup synchronous database connection
sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
engine = create_engine(sync_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_or_create_user(phone_number: str):
    """Fetches an existing user by phone number, or creates a new one if they don't exist."""
    session = SessionLocal()
    try:
        user = session.query(WhatsAppUser).filter(WhatsAppUser.phone_number == phone_number).first()
        if not user:
            # Create a brand new user
            user = WhatsAppUser(phone_number=phone_number, current_step='new', persona='General Public')
            session.add(user)
            session.commit()
            session.refresh(user)
        
        # Return a simple dictionary with their data
        return {
            "phone_number": user.phone_number, 
            "current_step": user.current_step, 
            "persona": user.persona
        }
    finally:
        session.close()

def update_user_state(phone_number: str, step: str = None, persona: str = None):
    """Updates the user's progress step or chosen persona."""
    session = SessionLocal()
    try:
        user = session.query(WhatsAppUser).filter(WhatsAppUser.phone_number == phone_number).first()
        if user:
            if step:
                user.current_step = step
            if persona:
                user.persona = persona
            session.commit()
    finally:
        session.close()