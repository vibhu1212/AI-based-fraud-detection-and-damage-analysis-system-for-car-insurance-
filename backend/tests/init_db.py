"""
Initialize database with schema and seed data
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.models.base import Base, engine
from app.seed_data import seed_database

def init_database():
    """Initialize database schema and seed data"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    print("\nSeeding database with demo data...")
    seed_database()
    print("✅ Database seeded successfully")

if __name__ == "__main__":
    init_database()
