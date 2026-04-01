from django.contrib.admin import AdminSite
from django.urls import reverse, path
from django.shortcuts import redirect
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponseRedirect, HttpResponseForbidden

class ManagerAdminSite(AdminSite):
    site_header = 'Dolandyryjy paneli'
    site_title = 'Dolandyryjy portaly'
    index_title = 'Dolandyryjy paneline hoş geldiňiz'
    site_url = None  # Remove "View site" link
    
    def logout(self, request, extra_context=None):
        """Custom logout that redirects to /manager/login/"""
        auth_logout(request)
        return HttpResponseRedirect('/manager/login/')
    
    def password_change(self, request, extra_context=None):
        """Block password change for managers"""
        return HttpResponseForbidden("Parol üýtgetmek administrator tarapyndan amala aşyrylmalydyr. Administrator bilen habarlaşyň.")
    
    def password_change_done(self, request, extra_context=None):
        """Block password change done page"""
        return HttpResponseForbidden("Parol üýtgetmek administrator tarapyndan amala aşyrylmalydyr. Administrator bilen habarlaşyň.")
    
    def each_context(self, request):
        """Override context to hide password change link"""
        context = super().each_context(request)
        # Remove password change URL from context for all users
        context['has_password_change'] = False
        context['password_change_url'] = None
        return context
    
    def password_change_url(self):
        """Override to return None and hide password change link"""
        return None

# Create manager site instance
manager_site = ManagerAdminSite(name='manager_admin')
