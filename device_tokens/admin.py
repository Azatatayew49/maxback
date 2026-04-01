from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from django import forms
from .models import DeviceToken, NotificationLog
from .firebase_service import send_notification_to_all, send_notification_to_platform


class SendNotificationForm(forms.Form):
    PLATFORM_CHOICES = [
        ('all', 'All Platforms'),
        ('android', 'Android Only'),
        ('ios', 'iOS Only'),
        ('web', 'Web Only'),
    ]
    
    NAVIGATION_CHOICES = [
        ('home', 'Home Screen'),
        ('announcement_detail', 'Announcement Detail Screen'),
    ]
    
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'size': '60', 'placeholder': 'Notification Title'})
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 60, 'placeholder': 'Notification Message'})
    )
    platform = forms.ChoiceField(
        choices=PLATFORM_CHOICES,
        initial='all',
        help_text='Select which platform(s) to send the notification to'
    )
    navigation_type = forms.ChoiceField(
        choices=NAVIGATION_CHOICES,
        initial='home',
        help_text='Select where to navigate when notification is tapped',
        label='Navigate To'
    )
    announcement_id = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Enter announcement ID'}),
        help_text='Required when navigating to Announcement Detail Screen',
        label='Announcement ID'
    )
    image_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'size': '60', 'placeholder': 'https://example.com/image.jpg'}),
        help_text='Optional: Image URL for rich notification'
    )
    extra_data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 60, 'placeholder': '{"key": "value"}'}),
        help_text='Optional: Additional JSON data to include with notification'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        navigation_type = cleaned_data.get('navigation_type')
        announcement_id = cleaned_data.get('announcement_id')
        
        if navigation_type == 'announcement_detail' and not announcement_id:
            raise forms.ValidationError(
                'Announcement ID is required when navigating to Announcement Detail Screen'
            )
        
        return cleaned_data


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['token_preview', 'platform', 'is_active', 'created_at', 'updated_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['token', 'fcm_token']
    readonly_fields = ['created_at', 'updated_at']
    
    def token_preview(self, obj):
        return f"{obj.token[:30]}..." if len(obj.token) > 30 else obj.token
    token_preview.short_description = 'Device Token'
    
    def has_add_permission(self, request):
        return False
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-notification/', self.admin_site.admin_view(self.send_notification_view), name='send_notification'),
        ]
        return custom_urls + urls
    
    def send_notification_view(self, request):
        if request.method == 'POST':
            form = SendNotificationForm(request.POST)
            if form.is_valid():
                title = form.cleaned_data['title']
                body = form.cleaned_data['body']
                platform = form.cleaned_data['platform']
                navigation_type = form.cleaned_data.get('navigation_type', 'home')
                announcement_id = form.cleaned_data.get('announcement_id')
                extra_data = form.cleaned_data.get('extra_data')
                image_url = form.cleaned_data.get('image_url')
                
                # Prepare data payload with navigation
                data = {
                    'navigation_type': navigation_type
                }
                
                if announcement_id and navigation_type == 'announcement_detail':
                    data['announcement_id'] = str(announcement_id)
                
                # Parse extra JSON data if provided
                if extra_data:
                    import json
                    try:
                        extra_json = json.loads(extra_data)
                        data.update(extra_json)
                    except json.JSONDecodeError:
                        self.message_user(request, 'Invalid JSON in extra data field', level='error')
                        return render(request, 'admin/send_notification.html', {'form': form})
                
                # Send notification
                if platform == 'all':
                    result = send_notification_to_all(title, body, data, image_url)
                else:
                    result = send_notification_to_platform(platform, title, body, data, image_url)
                
                # Show result message
                if 'error' in result:
                    self.message_user(request, f"Error: {result['error']}", level='error')
                else:
                    nav_info = f"→ {navigation_type}"
                    if announcement_id:
                        nav_info += f" (ID: {announcement_id})"
                    success_msg = f"✓ Notification sent! {nav_info} | Delivered to {result['success']}/{result['sent_to']} devices"
                    if result.get('failure', 0) > 0:
                        success_msg += f" ({result['failure']} failed)"
                    self.message_user(request, success_msg, level='success')
                
                return redirect('..')
        else:
            form = SendNotificationForm()
        
        # Get device stats
        total_devices = DeviceToken.objects.filter(is_active=True).exclude(
            fcm_token__isnull=True
        ).exclude(fcm_token='').count()
        
        android_count = DeviceToken.objects.filter(
            platform='android', is_active=True
        ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()
        
        ios_count = DeviceToken.objects.filter(
            platform='ios', is_active=True
        ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()
        
        web_count = DeviceToken.objects.filter(
            platform='web', is_active=True
        ).exclude(fcm_token__isnull=True).exclude(fcm_token='').count()
        
        context = {
            'form': form,
            'title': 'Send Push Notification',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'site_url': '/',
            'total_devices': total_devices,
            'android_count': android_count,
            'ios_count': ios_count,
            'web_count': web_count,
        }
        
        return render(request, 'admin/send_notification.html', context)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['send_notification_url'] = 'send-notification/'
        return super().changelist_view(request, extra_context)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['title', 'sent_to', 'success_count', 'failure_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'body']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def add_view(self, request, form_url='', extra_context=None):
        # Redirect to send notification page instead of add form
        return redirect('../../device_tokens/devicetoken/send-notification/')
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['add_url_override'] = '../../device_tokens/devicetoken/send-notification/'
        return super().changelist_view(request, extra_context)
