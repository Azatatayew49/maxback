from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DeviceToken, NotificationLog
from .serializers import DeviceTokenSerializer, NotificationSerializer, NotificationLogSerializer
from .firebase_service import send_notification_to_all, send_notification_to_platform, send_notification_to_device


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    
    def create(self, request, *args, **kwargs):
        """Register or update a device token"""
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if token exists
        device_token, created = DeviceToken.objects.get_or_create(
            token=token,
            defaults={
                'fcm_token': request.data.get('fcm_token', ''),
                'platform': request.data.get('platform', 'android'),
                'is_active': True
            }
        )
        
        if not created:
            # Update existing token
            device_token.fcm_token = request.data.get('fcm_token', device_token.fcm_token)
            device_token.platform = request.data.get('platform', device_token.platform)
            device_token.is_active = True
            device_token.save()
        
        serializer = self.get_serializer(device_token)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """Send notification to all active devices"""
        serializer = NotificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare data payload with navigation information
        data_payload = serializer.validated_data.get('data', {})
        data_payload['navigation_type'] = serializer.validated_data.get('navigation_type', 'home')
        if serializer.validated_data.get('announcement_id'):
            data_payload['announcement_id'] = str(serializer.validated_data['announcement_id'])
        
        result = send_notification_to_all(
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            data=data_payload,
            image_url=serializer.validated_data.get('image_url')
        )
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='send-to-platform')
    def send_to_platform(self, request):
        """Send notification to all devices of a specific platform"""
        serializer = NotificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        platform = request.data.get('platform', 'android')
        if platform not in ['android', 'ios', 'web']:
            return Response(
                {'error': 'Invalid platform. Must be android, ios, or web'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare data payload with navigation information
        data_payload = serializer.validated_data.get('data', {})
        data_payload['navigation_type'] = serializer.validated_data.get('navigation_type', 'home')
        if serializer.validated_data.get('announcement_id'):
            data_payload['announcement_id'] = str(serializer.validated_data['announcement_id'])
        
        result = send_notification_to_platform(
            platform=platform,
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            data=data_payload,
            image_url=serializer.validated_data.get('image_url')
        )
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='send-notification')
    def send_to_device(self, request, pk=None):
        """Send notification to a specific device"""
        serializer = NotificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare data payload with navigation information
        data_payload = serializer.validated_data.get('data', {})
        data_payload['navigation_type'] = serializer.validated_data.get('navigation_type', 'home')
        if serializer.validated_data.get('announcement_id'):
            data_payload['announcement_id'] = str(serializer.validated_data['announcement_id'])
        
        result = send_notification_to_device(
            device_id=pk,
            title=serializer.validated_data['title'],
            body=serializer.validated_data['body'],
            data=data_payload,
            image_url=serializer.validated_data.get('image_url')
        )
        
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get device token statistics"""
        total = DeviceToken.objects.count()
        active = DeviceToken.objects.filter(is_active=True).count()
        by_platform = {}
        for platform in ['android', 'ios', 'web']:
            by_platform[platform] = DeviceToken.objects.filter(
                platform=platform,
                is_active=True
            ).count()
        
        return Response({
            'total_devices': total,
            'active_devices': active,
            'inactive_devices': total - active,
            'by_platform': by_platform
        })


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
