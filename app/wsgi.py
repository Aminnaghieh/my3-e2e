import os
from django.core.wsgi import get_wsgi_application

# توجه: چون پوشه شما اسمش app هست، اینجا هم app.settings نوشته شده
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

application = get_wsgi_application()
