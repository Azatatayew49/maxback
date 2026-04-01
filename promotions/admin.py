from django.contrib import admin
from django.utils.html import format_html
from django.core.cache import cache
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'photo_preview',
        'announcement',
        'frequency',
        'is_active',
        'priority',
        'created_at',
    ]
    list_display_links = ['id', 'photo_preview', 'announcement']
    list_filter = ['frequency', 'is_active', 'created_at', 'priority']
    search_fields = ['announcement__name', 'announcement__description']
    ordering = ['priority', '-created_at']
    list_editable = ['is_active', 'priority', 'frequency']
    readonly_fields = ['photo_preview_large', 'created_at', 'updated_at']
    raw_id_fields = ['announcement']  # Use ID input instead of dropdown
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        cache.delete('promotions_list')  # Clear cache when promotion is saved
    
    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        cache.delete('promotions_list')  # Clear cache when promotion is deleted
    
    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        cache.delete('promotions_list')  # Clear cache on bulk delete
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'announcement':
            kwargs['help_text'] = 'Enter announcement ID directly or use search button'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('announcement', 'photo', 'photo_preview_large')
        }),
        ('Display Settings', {
            'fields': ('frequency', 'priority', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def photo_preview(self, obj):
        """Small thumbnail for list view"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.photo.url
            )
        return "No Image"
    photo_preview.short_description = 'Preview'
    
    def photo_preview_large(self, obj):
        """Large preview for detail view"""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px; object-fit: contain; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return "No Image Uploaded"
    photo_preview_large.short_description = 'Photo Preview'
    
    actions = ['activate_promotions', 'deactivate_promotions', 'set_high_priority']
    
    def activate_promotions(self, request, queryset):
        """Activate selected promotions"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} promotion(s) activated.')
    activate_promotions.short_description = "Activate selected promotions"
    
    def deactivate_promotions(self, request, queryset):
        """Deactivate selected promotions"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} promotion(s) deactivated.')
    deactivate_promotions.short_description = "Deactivate selected promotions"
    
    def set_high_priority(self, request, queryset):
        """Set high priority for selected promotions"""
        updated = queryset.update(priority=1)
        self.message_user(request, f'{updated} promotion(s) set to high priority (1).')
    set_high_priority.short_description = "Set high priority (1)"
