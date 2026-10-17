import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, init_db

# Initialize database on each cold start
init_db()

def handler(environ, start_response):
    return app(environ, start_response)
