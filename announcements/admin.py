from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from .models import Announcement, Category, Village, Banner, Photo, Favorite, PendingAnnouncement, PendingAnnouncementPhoto, PendingAnnouncementEdit, PendingPhoto
from .manager_admin import manager_site

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 3  # Number of empty photo fields to display
    
    def get_readonly_fields(self, request, obj=None):
        """Photos are editable for both admins and managers"""
        return []
    
    def has_add_permission(self, request, obj=None):
        """Both admins and managers can add photos"""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Both admins and managers can delete photos"""
        return request.user.is_staff


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'priority', 'status_display', 'category', 'village', 'phone_number', 'expiration_date', 'created_by', 'created_at']
    list_filter = ['status', 'category', 'village', 'expiration_date', 'priority', 'created_by']
    search_fields = ['id', 'name', 'description', 'phone_number']
    inlines = [PhotoInline]
    readonly_fields = ('id', 'created_by', 'approved_by', 'approved_at', 'created_at', 'updated_at')
    actions = ['mark_as_active', 'mark_as_not_active']
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Customize status field to exclude 'expired' - it's set automatically"""
        if db_field.name == 'status':
            # Only show 'active' and 'not_active' choices
            kwargs['choices'] = [
                ('active', 'Işjeň'),
                ('not_active', 'Işjeň däl'),
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'active': '#28a745',  # Green
            'not_active': '#6c757d',  # Gray
            'expired': '#dc3545',  # Red
        }
        labels = {
            'active': 'Işjeň',
            'not_active': 'Işjeň däl',
            'expired': 'Möhleti gutardy',
        }
        color = colors.get(obj.status, '#000000')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color, label
        )
    status_display.short_description = 'Ýagdaý'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Admins: only metadata fields are readonly
        Managers: can edit main fields, but id, created_by, approved fields, and status are readonly
        """
        if request.user.is_superuser:
            return self.readonly_fields
        # Managers - allow editing main fields but not status
        return ('id', 'created_by', 'approved_by', 'approved_at', 'created_at', 'updated_at', 'status')
    
    def get_fieldsets(self, request, obj=None):
        """Return different fieldsets based on user permissions"""
        if request.user.is_superuser:
            # Admin sees all fields including approval
            return (
                (None, {
                    'fields': ('id', 'name', 'description', 'priority', 'category', 'village', 'expiration_date', 'status')
                }),
                ('Habarlaşmak maglumatlary', {
                    'fields': ('phone_number',),
                    'description': 'Diňe 8 san giriziň. Ýurt kody +993 awtomatiki goşular.'
                }),
                ('Maglumat', {
                    'fields': ('created_by', 'approved_by', 'approved_at', 'created_at', 'updated_at')
                }),
            )
        else:
            # Managers cannot add/edit announcements directly - they use pending announcements
            return (
                (None, {
                    'fields': ('id', 'name', 'description', 'priority', 'category', 'village', 'expiration_date', 'status')
                }),
                ('Habarlaşmak maglumatlary', {
                    'fields': ('phone_number',),
                    'description': 'Diňe 8 san giriziň. Ýurt kody +993 awtomatiki goşular.'
                }),
                ('Maglumat', {
                    'fields': ('created_at', 'updated_at'),
                    'classes': ('collapse',)
                }),
            )
    
    def get_inlines(self, request, obj=None):
        """Show photo inline for both admins and managers"""
        # Both admins and managers can see photos
        # Managers see them as readonly when editing (changes go to pending)
        return [PhotoInline]
    
    def has_view_permission(self, request, obj=None):
        """Managers can view announcements."""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Only admins can add announcements directly. Managers use pending announcements."""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Managers can edit (but changes go to pending). Admins edit directly."""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Only admins can delete announcements."""
        return request.user.is_superuser
    
    def save_model(self, request, obj, form, change):
        """
        Admins save directly.
        Managers: capture original, save temporarily (will revert in save_related)
        """
        if request.user.is_superuser:
            # Admin - save directly
            if not change:  # New object
                obj.created_by = request.user
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
            super().save_model(request, obj, form, change)
        else:
            # Manager - capture original state before saving
            if change:
                # Get original object from database BEFORE any changes
                original = Announcement.objects.get(pk=obj.pk)
                
                # Store original data (we'll revert to this later)
                request._manager_edit_data = {
                    'original_name': original.name,
                    'original_description': original.description,
                    'original_phone_number': original.phone_number,
                    'original_priority': original.priority,
                    'original_expiration_date': original.expiration_date,
                    'original_category': original.category,
                    'original_village': original.village,
                    'original_photos': list(original.photos.all()),
                    'announcement_id': obj.pk,
                    'new_data': {
                        'name': obj.name,
                        'description': obj.description,
                        'phone_number': obj.phone_number,
                        'priority': obj.priority,
                        'expiration_date': obj.expiration_date,
                        'category': obj.category,
                        'village': obj.village,
                    }
                }
                # Save the changes temporarily (required for formsets to work)
                super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """
        Called after save_model and save_formset.
        For managers: let Django save formsets (fixes AttributeError), then revert and create pending edit.
        """
        # Always call parent to let Django handle formsets properly
        super().save_related(request, form, formsets, change)
        
        # For managers: now create pending edit and revert changes
        if not request.user.is_superuser and hasattr(request, '_manager_edit_data') and change:
            edit_data = request._manager_edit_data
            new_data = edit_data['new_data']
            
            # Get the announcement and its current photos (after manager's changes)
            announcement = Announcement.objects.get(pk=edit_data['announcement_id'])
            current_photos = list(announcement.photos.all())
            
            # Create pending edit with proposed changes
            pending_edit = PendingAnnouncementEdit.objects.create(
                original_announcement=announcement,
                edited_by=request.user,
                **new_data
            )
            
            # Store the proposed photos in pending edit
            for photo in current_photos:
                PendingPhoto.objects.create(
                    pending_edit=pending_edit,
                    image=photo.image
                )
            
            # Now revert the announcement to original state
            announcement.name = edit_data['original_name']
            announcement.description = edit_data['original_description']
            announcement.phone_number = edit_data['original_phone_number']
            announcement.priority = edit_data['original_priority']
            announcement.expiration_date = edit_data['original_expiration_date']
            announcement.category = edit_data['original_category']
            announcement.village = edit_data['original_village']
            announcement.save()
            
            # Revert photos to original state
            original_photos = edit_data['original_photos']
            original_photo_ids = [p.id for p in original_photos]
            
            # Delete any photos added by manager
            for photo in current_photos:
                if photo.id not in original_photo_ids:
                    photo.delete()
            
            # Recreate any deleted photos
            current_photo_ids = [p.id for p in current_photos]
            for original_photo in original_photos:
                if original_photo.id not in current_photo_ids:
                    # Photo was deleted, recreate it
                    Photo.objects.create(
                        announcement=announcement,
                        image=original_photo.image
                    )
            
            self.message_user(
                request,
                f'Üýtgetmäňiz tassyklamak üçin ugradyldy #{pending_edit.id}',
                level='success'
            )
    
    def response_change(self, request, obj):
        """
        Override to redirect managers to list after creating pending edit
        """
        if not request.user.is_superuser:
            # Manager editing - photo changes were stored in save_formset
            # Now they're attached to the pending edit created in save_model
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            # Use the current admin site's namespace
            admin_site_name = self.admin_site.name
            return HttpResponseRedirect(reverse(f'{admin_site_name}:announcements_announcement_changelist'))
        # Admin - default behavior
        return super().response_change(request, obj)
    
    @admin.action(description='Saýlanan yglanmalary tassyklamak')
    def approve_announcements(self, request, queryset):
        """Approve announcements (admin only)"""
        if not request.user.is_superuser:
            self.message_user(request, "Yglanmalary tassyklamaga rugsat ýok", level='error')
            return
        
        updated = queryset.filter(status='waiting_approval').update(
            status='active',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"{updated} sany yglanyň tassyklandy")
    
    @admin.action(description='Saýlanan yglanmalary ret etmek')
    def reject_announcements(self, request, queryset):
        """Reject/delete announcements (admin only)"""
        if not request.user.is_superuser:
            self.message_user(request, "Yglanmalary ret etmäge rugsat ýok", level='error')
            return
        
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} sany yglanyň ret edildi we öçürildi")
    
    @admin.action(description='Saýlananlary işjeň diýip bellemek')
    def mark_as_active(self, request, queryset):
        """Mark selected announcements as active (admin only)"""
        if not request.user.is_superuser:
            self.message_user(request, "Ýagdaýy üýtgetmäge rugsat ýok", level='error')
            return
        
        # Don't activate expired announcements
        from django.utils import timezone
        queryset = queryset.exclude(expiration_date__lt=timezone.now().date())
        
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} sany yglanyň işjeň edildi")
    
    @admin.action(description='Saýlananlary işjeň däl diýip bellemek')
    def mark_as_not_active(self, request, queryset):
        """Mark selected announcements as not active (admin only)"""
        if not request.user.is_superuser:
            self.message_user(request, "Ýagdaýy üýtgetmäge rugsat ýok", level='error')
            return
        
        updated = queryset.update(status='not_active')
        self.message_user(request, f"{updated} sany yglanyň işjeň däl edildi")
    
    def get_actions(self, request):
        """Customize action labels and remove actions for managers"""
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            actions['delete_selected'] = (
                actions['delete_selected'][0],
                'delete_selected',
                'Saýlananlary POZ'
            )
        # Remove mark_as_active and mark_as_not_active actions for managers
        if not request.user.is_superuser:
            if 'mark_as_active' in actions:
                del actions['mark_as_active']
            if 'mark_as_not_active' in actions:
                del actions['mark_as_not_active']
        return actions

# Custom User Admin for managing manager users
class ManagerUserAdmin(BaseUserAdmin):
    """Custom admin to manage manager users"""
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_manager', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Şahsy maglumat', {'fields': ('first_name', 'last_name', 'email')}),
        ('Rugsat', {
            'fields': ('is_active', 'is_staff', 'groups'),
            'description': 'Dolandyryjy rugsatlaryny bermek üçin ulanyjyny "Yglanyş dolandyryjysy" toparyna goşuň'
        }),
        ('Möhüm seneler', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'is_staff', 'is_active'),
        }),
        ('Dolandyryjy rugsatlary', {
            'classes': ('wide',),
            'fields': ('groups',),
            'description': 'Dolandyryjy rugsatlaryny bermek üçin "Yglanyş dolandyryjysy" toparyny saýlaň'
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def is_manager(self, obj):
        """Check if user is in Announcement Manager group"""
        is_in_group = obj.groups.filter(name='Announcement Manager').exists()
        if is_in_group:
            return format_html('<span style="color: #28A745; font-weight: bold;">✓ Dolandyryjy</span>')
        elif obj.is_superuser:
            return format_html('<span style="color: #007BFF; font-weight: bold;">★ Administrator</span>')
        else:
            return format_html('<span style="color: #6C757D;">Adaty ulanyjy</span>')
    is_manager.short_description = 'Rol'
    
    def get_queryset(self, request):
        """Only show staff users (managers and admins)"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            # Superusers can see all staff users
            return qs.filter(is_staff=True)
        else:
            # Non-superusers can only see themselves
            return qs.filter(id=request.user.id)
    
    def has_add_permission(self, request):
        """Only superusers can add manager users"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete users, and cannot delete themselves"""
        if not request.user.is_superuser:
            return False
        if obj and obj.id == request.user.id:
            return False
        return True
    
    def has_change_permission(self, request, obj=None):
        """Only superusers can edit users - managers cannot edit themselves"""
        return request.user.is_superuser
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change_view to prevent password change for non-superusers"""
        extra_context = extra_context or {}
        # Disable password change link for non-superusers
        if not request.user.is_superuser:
            extra_context['show_save'] = False
            extra_context['show_save_and_continue'] = False
        return super().change_view(request, object_id, form_url, extra_context)
    
    def save_model(self, request, obj, form, change):
        """Save the user model"""
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Handle groups after saving - ensure manager users have is_staff set to True"""
        super().save_related(request, form, formsets, change)
        
        obj = form.instance
        # After groups are saved, check if user is in Announcement Manager group
        if obj.groups.filter(name='Announcement Manager').exists():
            if not obj.is_staff:
                obj.is_staff = True
                obj.save(update_fields=['is_staff'])
    
    actions = ['make_manager', 'remove_manager', 'deactivate_users']
    
    @admin.action(description='Saýlanan ulanyjylary dolandyryjy toparyna goşmak')
    def make_manager(self, request, queryset):
        """Add users to Announcement Manager group"""
        if not request.user.is_superuser:
            self.message_user(request, "Bu işi ýerine ýetirmäge rugsat ýok", level='error')
            return
        
        manager_group, created = Group.objects.get_or_create(name='Announcement Manager')
        count = 0
        for user in queryset:
            if not user.is_superuser and not user.groups.filter(name='Announcement Manager').exists():
                user.groups.add(manager_group)
                user.is_staff = True
                user.save()
                count += 1
        
        self.message_user(request, f"{count} sany ulanyjy dolandyryjy toparyna goşuldy")
    
    @admin.action(description='Saýlanan ulanyjylary dolandyryjy toparyndan aýyrmak')
    def remove_manager(self, request, queryset):
        """Remove users from Announcement Manager group"""
        if not request.user.is_superuser:
            self.message_user(request, "Bu işi ýerine ýetirmäge rugsat ýok", level='error')
            return
        
        manager_group = Group.objects.filter(name='Announcement Manager').first()
        if not manager_group:
            self.message_user(request, "Dolandyryjy topary ýok", level='warning')
            return
        
        count = 0
        for user in queryset:
            if user.groups.filter(name='Announcement Manager').exists():
                user.groups.remove(manager_group)
                # Remove is_staff if they're not superuser and not in any other group
                if not user.is_superuser and user.groups.count() == 0:
                    user.is_staff = False
                user.save()
                count += 1
        
        self.message_user(request, f"{count} sany ulanyjy dolandyryjy toparyndan aýryldy")
    
    @admin.action(description='Saýlanan ulanyjylary öçürmek')
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        if not request.user.is_superuser:
            self.message_user(request, "Bu işi ýerine ýetirmäge rugsat ýok", level='error')
            return
        
        # Don't allow deactivating the current user
        queryset = queryset.exclude(id=request.user.id)
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} sany ulanyjy öçürildi")


# Unregister the default User admin and register our custom one
# Only do this for superusers to see
admin.site.unregister(User)
admin.site.register(User, ManagerUserAdmin)

class PendingAnnouncementPhotoInline(admin.TabularInline):
    model = PendingAnnouncementPhoto
    extra = 3  # Show 3 empty photo fields when creating
    
    def get_readonly_fields(self, request, obj=None):
        """Photos editable for owners and admins"""
        # Only pending_announcement field is readonly (set automatically)
        return []
    
    def has_add_permission(self, request, obj=None):
        """Allow managers to add photos to their own pending announcements, admins can add to all"""
        if request.user.is_superuser:
            return True
        # Managers can add photos to their own pending announcements
        if obj and obj.created_by == request.user:
            return True
        # When creating new (obj is None)
        if obj is None:
            return request.user.is_staff
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow managers to delete photos from their own pending announcements, admins can delete from all"""
        if request.user.is_superuser:
            return True
        # Managers can delete photos from their own pending announcements
        if obj and obj.created_by == request.user:
            return True
        # When creating new (obj is None)
        if obj is None:
            return request.user.is_staff
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow managers to change photos in their own pending announcements"""
        if request.user.is_superuser:
            return True
        # Managers can change photos in their own pending announcements
        if obj and obj.created_by == request.user:
            return True
        return False
    
    def has_view_permission(self, request, obj=None):
        """Allow everyone with staff access to view photos"""
        return request.user.is_staff

@admin.register(PendingAnnouncement)
class PendingAnnouncementAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'village', 'created_by', 'created_at', 'status_display']
    list_filter = ['created_at', 'created_by', 'category', 'village']
    search_fields = ['name', 'description']
    readonly_fields = ('created_by', 'created_at')
    inlines = [PendingAnnouncementPhotoInline]
    actions = ['approve_announcements', 'reject_announcements']
    
    def get_fieldsets(self, request, obj=None):
        """Show different fieldsets when creating vs viewing"""
        if obj:  # Editing existing object
            return (
                ('Garaşylýan yglanyş maglumaty', {
                    'fields': ('created_by', 'created_at')
                }),
                ("Dolandyryjynyň habary", {
                    'fields': ('message_to_admin',),
                    'description': "Dolandyryjynyň bu yglanyş barada düşündirimesi."
                }),
                ('Yglanyş maglumatlary', {
                    'fields': ('name', 'description', 'phone_number', 'priority', 'category', 'village', 'expiration_date'),
                    'description': 'Bu yglanyş administrator tassyklamagyna garaşylýar.'
                }),
            )
        else:  # Creating new object
            return (
                ('Yglanyş maglumatlary', {
                    'fields': ('name', 'description', 'phone_number', 'priority', 'category', 'village', 'expiration_date'),
                    'description': 'Täze yglanyşýň mağlumatlaryňy dolduryň. Administrator tassyklamasy üçin ugradylar.'
                }),
                ("Administratora habar", {
                    'fields': ('message_to_admin',),
                    'description': 'Mağlumly: Bu yglanyşy näme üçin goşmak isleýäňiziňizi düşündiriň.'
                }),
            )
    
    def get_queryset(self, request):
        """Admins see all, managers see only their own pending announcements"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            # Managers can only see their own pending announcements
            return qs.filter(created_by=request.user)
    
    def has_add_permission(self, request):
        """Managers can add pending announcements"""
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """Admins can edit all, managers can edit their own"""
        if request.user.is_superuser:
            return True
        # Managers can edit their own pending announcements
        if obj and obj.created_by == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Admins can delete, managers can delete their own"""
        if request.user.is_superuser:
            return True
        if obj and obj.created_by == request.user:
            return True
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Managers and admins can edit their fields, but created_by and created_at are readonly"""
        # Both admins and managers: only metadata fields are readonly
        return ('created_by', 'created_at')
    
    def get_actions(self, request):
        """Only admins can approve/reject"""
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            return {}
        return actions
    
    def status_display(self, obj):
        """Display pending status with color"""
        return format_html(
            '<span style="color: #FFA500; font-weight: bold;">●</span> Pending Approval'
        )
    status_display.short_description = 'Status'
    
    def has_module_permission(self, request):
        """Allow both admins and managers to see this module"""
        return request.user.is_staff
    
    def get_inlines(self, request, obj=None):
        """Show photo inline for both managers and admins"""
        return [PendingAnnouncementPhotoInline]
    
    def has_view_permission(self, request, obj=None):
        """Allow admins and managers to view pending announcements"""
        if request.user.is_superuser:
            return True
        # Managers can view their own pending announcements
        if obj and obj.created_by == request.user:
            return True
        # For list view (obj is None), allow access
        if obj is None:
            return request.user.is_staff
        return False
    
    def save_model(self, request, obj, form, change):
        """Set created_by on save"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.action(description='Saýlanan yglanmalary tassyklamak')
    def approve_announcements(self, request, queryset):
        """Approve pending announcements and create actual announcements"""
        if not request.user.is_superuser:
            self.message_user(request, "Diňe administratorlar yglanmalary tassyklap bilýer", level='error')
            return
        
        success_count = 0
        for pending_announcement in queryset:
            try:
                pending_announcement.approve(request.user)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"'{pending_announcement.name}' tassyklamakda ýalňyşma: {str(e)}", level='error')
        
        self.message_user(request, f"{success_count} sany yglanyş tassyklandy we çap edildi")
    
    @admin.action(description='Saýlanan yglanmalary ret etmek')
    def reject_announcements(self, request, queryset):
        """Reject and delete pending announcements"""
        if not request.user.is_superuser:
            self.message_user(request, "Diňe administratorlar yglanmalary ret edip bilýer", level='error')
            return
        
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} sany yglanyş ret edildi")

class PendingPhotoInline(admin.TabularInline):
    model = PendingPhoto
    extra = 3  # Show 3 empty photo fields when creating
    
    def get_readonly_fields(self, request, obj=None):
        """Photos editable for owners and admins"""
        return []
    
    def has_add_permission(self, request, obj=None):
        """Allow managers to add photos to their own pending edits, admins can add to all"""
        if request.user.is_superuser:
            return True
        # Managers can add photos to their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow managers to delete photos from their own pending edits, admins can delete from all"""
        if request.user.is_superuser:
            return True
        # Managers can delete photos from their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow managers to change photos in their own pending edits"""
        if request.user.is_superuser:
            return True
        # Managers can change photos in their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        return False
    
    def has_view_permission(self, request, obj=None):
        """Allow everyone with staff access to view photos"""
        return request.user.is_staff

@admin.register(PendingAnnouncementEdit)
class PendingAnnouncementEditAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_announcement_link', 'name', 'edited_by', 'edited_at', 'status_display']
    list_filter = ['edited_at', 'edited_by', 'category', 'village']
    search_fields = ['name', 'description', 'original_announcement__name']
    readonly_fields = ('original_announcement', 'edited_by', 'edited_at', 'view_changes')
    inlines = [PendingPhotoInline]
    actions = ['approve_edits', 'reject_edits']
    
    fieldsets = (
        ('Garaşylýan üýtgetme maglumaty', {
            'fields': ('original_announcement', 'edited_by', 'edited_at', 'view_changes')
        }),
        ("Dolandyryjynyň habary", {
            'fields': ('message_to_admin',),
            'description': "Dolandyryjynyň bu üýtgetme barada düşündirimesi."
        }),
        ('Teklip edildi üýtgetmeler', {
            'fields': ('name', 'description', 'phone_number', 'priority', 'category', 'village', 'expiration_date'),
            'description': 'Bu dolandyryjynyň teklip eden üýtgetmeleri.'
        }),
    )
    
    def original_announcement_link(self, obj):
        """Display clickable link to original announcement"""
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:announcements_announcement_change', args=[obj.original_announcement.id])
        return format_html('<a href="{}">{}</a>', url, obj.original_announcement.name)
    original_announcement_link.short_description = 'Asyl yglanyş'
    
    def status_display(self, obj):
        """Display pending status with color"""
        return format_html(
            '<span style="color: #FFA500; font-weight: bold;">●</span> Pending Approval'
        )
    status_display.short_description = 'Status'
    
    def view_changes(self, obj):
        """Display comparison of changes"""
        if not obj.id:
            return "Üýtgetmeleri görmek üçin saklaň"
        
        original = obj.original_announcement
        changes = []
        
        if original.name != obj.name:
            changes.append(f"<b>Ady:</b><br>Geldi: {original.name}<br>Täze: {obj.name}")
        if original.description != obj.description:
            changes.append(f"<b>Beyan:</b><br>Geldi: {original.description[:100]}...<br>Täze: {obj.description[:100]}...")
        if original.phone_number != obj.phone_number:
            changes.append(f"<b>Telefon:</b> {original.phone_number} → {obj.phone_number}")
        if original.priority != obj.priority:
            changes.append(f"<b>Ileri tutma:</b> {original.priority} → {obj.priority}")
        if original.category != obj.category:
            changes.append(f"<b>Kategoriýasy:</b> {original.category} → {obj.category}")
        if original.village != obj.village:
            changes.append(f"<b>Oba:</b> {original.village} → {obj.village}")
        if original.expiration_date != obj.expiration_date:
            changes.append(f"<b>Möhleti:</b> {original.expiration_date} → {obj.expiration_date}")
        
        if not changes:
            return format_html('<span style="color: #6C757D;">Üýtgetme tapylmady</span>')
        
        return format_html('<div style="line-height: 1.8;">{}</div>', '<br><br>'.join(changes))
    view_changes.short_description = 'Üýtgetmeleriň gysgacha mazmuny'
    
    def get_queryset(self, request):
        """Admins see all, managers see only their own pending edits"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            # Managers can only see their own pending edits
            return qs.filter(edited_by=request.user)
    
    def has_add_permission(self, request):
        """Prevent manual creation - these are created by the system"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Admins can edit all, managers can edit their own"""
        if request.user.is_superuser:
            return True
        # Managers can edit their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Admins can delete all, managers can delete their own"""
        if request.user.is_superuser:
            return True
        # Managers can delete their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        return False
    
    def has_module_permission(self, request):
        """Allow both admins and managers to see this module"""
        return request.user.is_staff
    
    def get_inlines(self, request, obj=None):
        """Show photo inline for both managers and admins"""
        return [PendingPhotoInline]
    
    def has_view_permission(self, request, obj=None):
        """Allow admins and managers to view pending edits"""
        if request.user.is_superuser:
            return True
        # Managers can view their own pending edits
        if obj and obj.edited_by == request.user:
            return True
        # For list view (obj is None), allow access
        if obj is None:
            return request.user.is_staff
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Metadata fields are readonly, managers can edit main fields"""
        # Both admins and managers: only metadata fields are readonly
        return ('original_announcement', 'edited_by', 'edited_at', 'view_changes')
    
    def get_actions(self, request):
        """Only admins can approve/reject"""
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            return {}
        return actions
    
    @admin.action(description='Saýlanan üýtgetmeleri tassyklamak')
    def approve_edits(self, request, queryset):
        """Approve pending edits and apply changes"""
        if not request.user.is_superuser:
            self.message_user(request, "Diňe administratorlar üýtgetmeleri tassyklap bilýer", level='error')
            return
        
        success_count = 0
        for pending_edit in queryset:
            try:
                pending_edit.approve(request.user)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"'{pending_edit.name}' üçin üýtgetmeni tassyklamakda ýalňyşma: {str(e)}", level='error')
        
        self.message_user(request, f"{success_count} sany üýtgetme tassyklandy")
    
    @admin.action(description='Saýlanan üýtgetmeleri ret etmek')
    def reject_edits(self, request, queryset):
        """Reject and delete pending edits"""
        if not request.user.is_superuser:
            self.message_user(request, "Diňe administratorlar üýtgetmeleri ret edip bilýer", level='error')
            return
        
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} sany üýtgetme ret edildi")

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['id', 'announcement', 'image_preview', 'image']
    list_filter = ['announcement__category', 'announcement__village']
    search_fields = ['announcement__id', 'announcement__name']
    raw_id_fields = ['announcement']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'
    
    def has_add_permission(self, request):
        """Only admins can add photos"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Only admins can change photos"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only admins can delete photos"""
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        """Only admins can view photos"""
        return request.user.is_superuser

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['id', 'announcement', 'photo']
    raw_id_fields = ['announcement']  # Use ID input instead of dropdown
    search_fields = ['announcement__id', 'announcement__name']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'announcement':
            kwargs['help_text'] = 'Yglanyş ID-ni goniüi giri ziň ýada gozleg dü wmesini ulanyň'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Category)
admin.site.register(Village)
admin.site.register(Favorite)

# Register models to manager site as well
manager_site.register(User, ManagerUserAdmin)
manager_site.register(Announcement, AnnouncementAdmin)
manager_site.register(Category)
manager_site.register(Village)
manager_site.register(Banner, BannerAdmin)
# Photo removed from manager panel
manager_site.register(Favorite)
manager_site.register(PendingAnnouncement, PendingAnnouncementAdmin)
manager_site.register(PendingAnnouncementEdit, PendingAnnouncementEditAdmin)
