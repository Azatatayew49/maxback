from rest_framework import serializers
from .models import DeviceToken, NotificationLog


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['id', 'token', 'fcm_token', 'platform', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class NotificationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    data = serializers.JSONField(required=False, default=dict)
    image_url = serializers.URLField(required=False, allow_blank=True)
    navigation_type = serializers.ChoiceField(
        choices=['home', 'announcement_detail'],
        required=False,
        default='home',
        help_text="Navigation destination: 'home' for home screen, 'announcement_detail' for announcement detail screen"
    )
    announcement_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Required when navigation_type is 'announcement_detail'"
    )
    
    def validate(self, data):
        navigation_type = data.get('navigation_type', 'home')
        announcement_id = data.get('announcement_id')
        
        if navigation_type == 'announcement_detail' and not announcement_id:
            raise serializers.ValidationError(
                "announcement_id is required when navigation_type is 'announcement_detail'"
            )
        
        return data


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ['id', 'title', 'body', 'data', 'sent_to', 'success_count', 'failure_count', 'created_at']
