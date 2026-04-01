from rest_framework import serializers
from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'label', 'phone_number', 'is_active', 'order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
