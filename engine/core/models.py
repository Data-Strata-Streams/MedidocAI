# Purpose: Define the SQL Database Schema for the entire MedidocAI project.
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Generic(Base):
    __tablename__ = 'generics'
    id = Column(Integer, primary_key=True)
    generic_name = Column(String, unique=True, nullable=False)
    total_local_brands = Column(Integer)
    brands = relationship("Brand", back_populates="generic")
    profile = relationship("ClinicalProfile", back_populates="generic", uselist=False)

class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True)
    generic_id = Column(Integer, ForeignKey('generics.id'))
    brand_name = Column(String)
    manufacturer = Column(String)
    price = Column(String)
    exact_formula = Column(String)
    generic = relationship("Generic", back_populates="brands")

class ClinicalProfile(Base):
    __tablename__ = 'clinical_profiles'
    id = Column(Integer, primary_key=True)
    generic_id = Column(Integer, ForeignKey('generics.id'))
    indications = Column(Text)
    mechanism = Column(Text)
    side_effects = Column(Text)
    warnings = Column(Text)
    contraindications = Column(Text)
    dosage = Column(Text)
    black_box = Column(Text)
    generic = relationship("Generic", back_populates="profile")
# Purpose: Added MedicalTerm table to store AI-generated simple definitions for tooltips.
class MedicalTerm(Base):
    __tablename__ = 'medical_terms'
    id = Column(Integer, primary_key=True)
    term = Column(String, unique=True, nullable=False, index=True)
    definition = Column(Text, nullable=False)

# Purpose: Define the WhatsAppUser table to track onboarding state and assigned personas.
class WhatsAppUser(Base):
    __tablename__ = 'whatsapp_users'
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    
    # Tracks where they are in the menu: 'new', 'asking_persona', 'completed'
    current_step = Column(String, default='new') 
    
    # Stores their choice: 'General Public', 'Student', 'HCP'
    persona = Column(String, default='General Public') 