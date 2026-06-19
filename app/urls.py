from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # تمام درخواست‌های api/ به فایل core/urls.py فرستاده میشن
    path('api/', include('core.urls')),
    
    # صفحه اصلی مینی‌اپ (index.html) رو سرو می‌کنه
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]
