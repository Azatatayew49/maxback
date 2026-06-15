import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

os.environ['DJANGO_SETTINGS_MODULE'] = 'eziz_obam.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
