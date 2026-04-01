"""
URL configuration for eziz_obam project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.urls import path, include
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from announcements.views import AnnouncementViewSet, CategoryViewSet, VillageViewSet, BannerViewSet, FavoriteViewSet, PendingAnnouncementViewSet, PendingAnnouncementEditViewSet
from promotions.views import PromotionViewSet
from device_tokens.views import DeviceTokenViewSet, NotificationLogViewSet
from contacts.views import ContactViewSet
from django.conf import settings
from django.conf.urls.static import static
from announcements.manager_admin import manager_site

def admin_logout(request):
    """Custom admin logout that redirects to login page"""
    auth_logout(request)
    return redirect('/admin/login/')

# Note: User admin is customized in announcements/admin.py as ManagerUserAdmin
# Group is kept hidden to simplify the admin interface

router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'villages', VillageViewSet)
router.register(r'banners', BannerViewSet)
router.register(r'favorites', FavoriteViewSet)
router.register(r'promotions', PromotionViewSet)
router.register(r'device-tokens', DeviceTokenViewSet)
router.register(r'notification-logs', NotificationLogViewSet)
router.register(r'pending-announcements', PendingAnnouncementViewSet)
router.register(r'pending-edits', PendingAnnouncementEditViewSet)
router.register(r'contacts', ContactViewSet)

urlpatterns = [
    path('admin/logout/', admin_logout, name='admin_logout'),
    path('admin/', admin.site.urls),
    path('manager/', manager_site.urls),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
