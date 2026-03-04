import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cartridge_tracker.settings')
application = get_wsgi_application()
