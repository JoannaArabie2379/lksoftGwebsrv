#!/usr/bin/env python3
"""
ИГС Portal - WSGI Entry Point for Production
"""

import os
import sys

# Add application directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application, init_db

# Initialize database on first request
with application.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization warning: {e}")

if __name__ == '__main__':
    application.run()
