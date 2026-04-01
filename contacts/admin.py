from django.contrib import admin
from django.core.cache import cache
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['label', 'phone_number', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['label', 'phone_number']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'label']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete('contacts_list')  # Clear cache when contact is saved
    
    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        cache.delete('contacts_list')  # Clear cache when contact is deleted
    
    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        cache.delete('contacts_list')  # Clear cache on bulk delete
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('label', 'phone_number')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order')
        }),
    )
