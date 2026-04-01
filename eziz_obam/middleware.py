from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response.status_code = 200
        
        return response


class RestrictAdminOnManagerMiddleware:
    """
    Middleware to prevent the 'admin' user from accessing /manager/ URL.
    This ensures admin user can only access through /admin/ URL.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if accessing /manager/ path
        if request.path.startswith('/manager/'):
            # If user is authenticated and username is 'admin'
            if request.user.is_authenticated and request.user.username == 'admin':
                # Log them out and redirect back to /manager/ with error message
                logout(request)
                messages.error(request, 'Please enter the correct username and password. Note that both fields may be case-sensitive.')
                return redirect('/manager/')
        
        response = self.get_response(request)
        return response