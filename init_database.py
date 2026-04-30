"""
Run this script ONCE to create the database.
Usage: python init_database.py
"""
from app import app
from database import init_db

if __name__ == '__main__':
    with app.app_context():
        init_db(app)
        print("✅ Database created successfully at instance/saas.db")