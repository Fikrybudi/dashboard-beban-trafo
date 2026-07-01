# PythonAnywhere WSGI configuration
# Jangan di-edit via sini — nanti di-set otomatis oleh PythonAnywhere Web App setup

import sys
import os

# PythonAnywhere: arahkan ke folder project
project_home = '/home/[USERNAME]/dashboard_beban'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
