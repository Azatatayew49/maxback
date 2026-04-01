from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.cache import cache
from django.conf import settings
from .models import Promotion
from .serializers import PromotionSerializer


class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'promotions_list'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        # Cache miss - fetch from database
        response = super().list(request, *args, **kwargs)
        
        # Store in cache
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('promotions', 1800)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response
