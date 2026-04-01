from rest_framework import serializers
from .models import Promotion


class PromotionSerializer(serializers.ModelSerializer):
    announcement_id = serializers.IntegerField(source='announcement.id')
    announcement_name = serializers.CharField(source='announcement.name')

    class Meta:
        model = Promotion
        fields = [
            'id',
            'announcement_id',
            'announcement_name',
            'photo',
            'frequency',
            'is_active',
            'priority',
        ]
