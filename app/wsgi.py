"""
app/wsgi.py
===========
WSGI entry point برای gunicorn در Render.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
application = get_wsgi_application()
