from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.cache import cache
from django.conf import settings
from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving contact numbers.
    Only active contacts are returned to frontend users.
    """
    queryset = Contact.objects.filter(is_active=True)
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Return only active contacts, ordered by order field"""
        return Contact.objects.filter(is_active=True).order_by('order', 'label')

    def list(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'contacts_list'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        # Cache miss - fetch from database
        response = super().list(request, *args, **kwargs)
        
        # Store in cache
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('contacts', 3600)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response
