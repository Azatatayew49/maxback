from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.core.cache import cache
from django.conf import settings
from .models import Announcement, Category, Village, Banner, Favorite, Photo, PendingAnnouncement, PendingAnnouncementPhoto, PendingAnnouncementEdit, PendingPhoto
from .serializers import AnnouncementSerializer, CategorySerializer, VillageSerializer, BannerSerializer, FavoriteSerializer, PendingAnnouncementSerializer, PendingAnnouncementEditSerializer

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related('category', 'village').prefetch_related('photos')
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        from django.utils import timezone
        from django.db.models import Case, When, IntegerField, Q
        from difflib import SequenceMatcher
        
        # Get today's date for expiration check
        today = timezone.now().date()
        
        # Only show active announcements on frontend (not expired, not deactivated)
        # Also filter out announcements where expiration_date has passed
        queryset = self.queryset.filter(
            status='active',
            expiration_date__gte=today
        )
        
        # Filter by search query if provided
        search_query = self.request.query_params.get('search', None)
        if search_query:
            # First try exact/partial match
            exact_match = queryset.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )
            
            if exact_match.exists():
                queryset = exact_match
            else:
                # If no exact match, use fuzzy search on limited dataset
                # OPTIMIZATION: Only check 200 most recent announcements instead of ALL
                # This prevents loading 10,000+ records into memory
                limited_queryset = queryset.order_by('-created_at')[:200]
                all_announcements = list(limited_queryset)
                search_lower = search_query.lower()
                
                # Calculate similarity for each announcement
                matches = []
                for announcement in all_announcements:
                    name_lower = announcement.name.lower()
                    desc_lower = announcement.description.lower()
                    
                    # Check if any word in search query is similar to any word in name/description
                    name_similarity = self._calculate_text_similarity(search_lower, name_lower)
                    desc_similarity = self._calculate_text_similarity(search_lower, desc_lower)
                    
                    max_similarity = max(name_similarity, desc_similarity)
                    
                    # Include if similarity is above 60%
                    if max_similarity >= 0.6:
                        matches.append((announcement, max_similarity))
                
                # Sort by similarity and get announcement IDs
                matches.sort(key=lambda x: x[1], reverse=True)
                matched_ids = [a.id for a, _ in matches]
                
                if matched_ids:
                    queryset = queryset.filter(id__in=matched_ids)
                    # Preserve the similarity-based ordering
                    preserved_order = Case(*[When(id=id, then=pos) for pos, id in enumerate(matched_ids)])
                    queryset = queryset.annotate(similarity_order=preserved_order).order_by('similarity_order')
                    return queryset
                else:
                    # No fuzzy matches found
                    queryset = queryset.none()
        
        # Filter by category if provided in query params
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Order by priority: 0 goes last, higher numbers (1, 2, 3...) come first
        # Then order by created_at descending (newest first)
        queryset = queryset.annotate(
            priority_order=Case(
                When(priority=0, then=999999),
                default='priority',
                output_field=IntegerField()
            )
        ).order_by('priority_order', '-created_at')
        
        return queryset
    
    def _calculate_text_similarity(self, search_text, target_text):
        """Calculate similarity between search text and target text"""
        from difflib import SequenceMatcher
        
        # Split into words
        search_words = search_text.split()
        target_words = target_text.split()
        
        max_similarity = 0.0
        
        # Check similarity of each search word against each target word
        for search_word in search_words:
            for target_word in target_words:
                similarity = SequenceMatcher(None, search_word, target_word).ratio()
                max_similarity = max(max_similarity, similarity)
        
        # Also check if search text is a substring of target (partial match)
        if search_text in target_text:
            max_similarity = max(max_similarity, 0.8)
        
        return max_similarity
    
    def create(self, request, *args, **kwargs):
        # Check if user is authenticated and is a manager (staff but not superuser)
        user = request.user if hasattr(request, 'user') else None
        is_manager = user and user.is_authenticated and user.is_staff and not user.is_superuser
        
        if is_manager:
            # Manager creating announcement: create pending announcement instead
            data = request.data.copy()
            
            pending_announcement = PendingAnnouncement.objects.create(
                name=data.get('name'),
                description=data.get('description'),
                phone_number=data.get('phone_number'),
                priority=data.get('priority', 0),
                expiration_date=data.get('expiration_date'),
                category_id=data.get('category'),
                village_id=data.get('village'),
                message_to_admin=data.get('message_to_admin', ''),
                created_by=user
            )
            
            # Handle multiple photo uploads for pending announcement
            photos = request.FILES.getlist('photos')
            if photos:
                for photo in photos:
                    PendingAnnouncementPhoto.objects.create(pending_announcement=pending_announcement, image=photo)
            
            # Return pending announcement info
            return Response({
                'message': 'Announcement submitted for admin approval',
                'pending_announcement_id': pending_announcement.id,
                'status': 'pending_approval'
            }, status=status.HTTP_201_CREATED)
        else:
            # Admin creating announcement: create directly
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            announcement = serializer.save()
            
            # Handle multiple photo uploads
            photos = request.FILES.getlist('photos')
            for photo in photos:
                Photo.objects.create(announcement=announcement, image=photo)
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user is authenticated and is a manager (staff but not superuser)
        user = request.user if hasattr(request, 'user') else None
        is_manager = user and user.is_authenticated and user.is_staff and not user.is_superuser
        
        if is_manager:
            # Manager editing an announcement: create pending edit instead
            # Extract the data that would be updated
            data = request.data.copy()
            
            # Create pending edit with new data
            pending_edit = PendingAnnouncementEdit.objects.create(
                original_announcement=instance,
                name=data.get('name', instance.name),
                description=data.get('description', instance.description),
                phone_number=data.get('phone_number', instance.phone_number),
                priority=data.get('priority', instance.priority),
                expiration_date=data.get('expiration_date', instance.expiration_date),
                category_id=data.get('category', instance.category_id),
                village_id=data.get('village', instance.village_id),
                message_to_admin=data.get('message_to_admin', ''),
                edited_by=user
            )
            
            # Handle multiple photo uploads for pending edit
            photos = request.FILES.getlist('photos')
            if photos:
                for photo in photos:
                    PendingPhoto.objects.create(pending_edit=pending_edit, image=photo)
            
            # Return pending edit info
            return Response({
                'message': 'Edit submitted for admin approval',
                'pending_edit_id': pending_edit.id,
                'status': 'pending_approval',
                'original_announcement': AnnouncementSerializer(instance).data
            }, status=status.HTTP_200_OK)
        else:
            # Admin or manager editing non-active announcement: update directly
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            announcement = serializer.save()
            
            # Handle multiple photo uploads
            photos = request.FILES.getlist('photos')
            if photos:
                for photo in photos:
                    Photo.objects.create(announcement=announcement, image=photo)
            
            return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'categories_list'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        # Cache miss - fetch from database
        response = super().list(request, *args, **kwargs)
        
        # Store in cache
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('categories', 3600)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        cache.delete('categories_list')  # Clear cache on create
    
    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete('categories_list')  # Clear cache on update
    
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        cache.delete('categories_list')  # Clear cache on delete

class VillageViewSet(viewsets.ModelViewSet):
    queryset = Village.objects.all()
    serializer_class = VillageSerializer

    def list(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'villages_list'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        # Cache miss - fetch from database
        response = super().list(request, *args, **kwargs)
        
        # Store in cache
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('villages', 86400)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        cache.delete('villages_list')  # Clear cache on create
    
    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete('villages_list')  # Clear cache on update
    
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        cache.delete('villages_list')  # Clear cache on delete

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.select_related('announcement')
    serializer_class = BannerSerializer

    def list(self, request, *args, **kwargs):
        # Try to get from cache first
        cache_key = 'banners_list'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return Response(cached_data)
        
        # Cache miss - fetch from database
        response = super().list(request, *args, **kwargs)
        
        # Store in cache
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('banners', 1800)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        cache.delete('banners_list')  # Clear cache on create
    
    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete('banners_list')  # Clear cache on update
    
    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        cache.delete('banners_list')  # Clear cache on delete

class FavoriteViewSet(viewsets.ModelViewSet):
    queryset = Favorite.objects.select_related('announcement__category', 'announcement__village').prefetch_related('announcement__photos')
    serializer_class = FavoriteSerializer

    def get_queryset(self):
        """Filter favorites by device_token if provided in query params"""
        from django.utils import timezone
        
        queryset = self.queryset
        device_token = self.request.query_params.get('device_token', None)
        if device_token:
            queryset = queryset.filter(device_token=device_token)
        
        # Also filter out favorites with expired announcements
        today = timezone.now().date()
        queryset = queryset.filter(
            announcement__status='active',
            announcement__expiration_date__gte=today
        )
        
        return queryset

    def create(self, request, *args, **kwargs):
        from rest_framework import status
        print("Received data:", request.data)
        
        # Check if favorite already exists
        device_token = request.data.get('device_token')
        announcement_id = request.data.get('announcement_id')
        
        if device_token and announcement_id:
            existing = Favorite.objects.filter(
                device_token=device_token,
                announcement_id=announcement_id
            ).first()
            
            if existing:
                # Already exists, return the existing one
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        return super().create(request, *args, **kwargs)

class PendingAnnouncementEditViewSet(viewsets.ModelViewSet):
    queryset = PendingAnnouncementEdit.objects.select_related('original_announcement__category', 'original_announcement__village', 'edited_by', 'category', 'village').prefetch_related('original_announcement__photos', 'pending_photos')
    serializer_class = PendingAnnouncementEditSerializer
    
    def get_queryset(self):
        """Order by most recent first"""
        return self.queryset.order_by('-edited_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending edit and apply changes to the original announcement."""
        pending_edit = self.get_object()
        
        # Check if user is admin
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only admins can approve edits'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Apply the changes
        updated_announcement = pending_edit.approve(request.user)
        
        return Response({
            'message': 'Edit approved and applied successfully',
            'announcement': AnnouncementSerializer(updated_announcement).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending edit and delete it."""
        pending_edit = self.get_object()
        
        # Check if user is admin
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only admins can reject edits'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        original_announcement_name = pending_edit.original_announcement.name
        pending_edit.reject()
        
        return Response({
            'message': f'Edit for "{original_announcement_name}" rejected and deleted'
        }, status=status.HTTP_200_OK)

class PendingAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = PendingAnnouncement.objects.select_related('category', 'village', 'created_by').prefetch_related('pending_photos')
    serializer_class = PendingAnnouncementSerializer
    
    def get_queryset(self):
        """Order by most recent first"""
        return self.queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending announcement and create the actual announcement."""
        pending_announcement = self.get_object()
        
        # Check if user is admin
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only admins can approve announcements'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create the announcement
        announcement = pending_announcement.approve(request.user)
        
        return Response({
            'message': 'Announcement approved and published successfully',
            'announcement': AnnouncementSerializer(announcement).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending announcement and delete it."""
        pending_announcement = self.get_object()
        
        # Check if user is admin
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only admins can reject announcements'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        announcement_name = pending_announcement.name
        pending_announcement.reject()
        
        return Response({
            'message': f'Announcement "{announcement_name}" rejected and deleted'
        }, status=status.HTTP_200_OK)
