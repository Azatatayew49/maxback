from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
import re
import os
from .image_utils import compress_image

def announcement_image_path(instance, filename):
    """
    Generate custom filename for announcement photos.
    Format: announcements/{announcement_id}_{image_number}.{extension}
    Example: announcements/59_1.jpg, announcements/59_2.jpg
    """
    # Get the file extension
    ext = filename.split('.')[-1]
    
    # Count existing photos for this announcement
    if instance.announcement_id:
        existing_photos = Photo.objects.filter(announcement_id=instance.announcement_id).count()
        image_number = existing_photos + 1
    else:
        image_number = 1
    
    # Generate new filename
    new_filename = f"{instance.announcement_id}_{image_number}.{ext}"
    return os.path.join('announcements', new_filename)

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="At")
    photo = models.ImageField(upload_to='categories/', verbose_name="Surat")

    def save(self, *args, **kwargs):
        # Only compress image if it's new or has been changed
        if self.pk is None:
            # New instance - compress if photo exists
            if self.photo:
                self.photo = compress_image(self.photo)
        else:
            # Existing instance - only compress if photo changed
            try:
                old_instance = Category.objects.get(pk=self.pk)
                if old_instance.photo != self.photo:
                    if self.photo:
                        self.photo = compress_image(self.photo)
            except Category.DoesNotExist:
                if self.photo:
                    self.photo = compress_image(self.photo)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Bölüm"
        verbose_name_plural = "Bölümler"

class Village(models.Model):
    name = models.CharField(max_length=100, verbose_name="At")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Ýer"
        verbose_name_plural = "Ýerler"

class Announcement(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('not_active', 'Not Active'),
        ('expired', 'Expired'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Bildiriş")
    description = models.TextField(verbose_name="Düşündiriş")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon", help_text="Diňe 8 san giriziň. Ýurt kody +993 awtomatiki goşular.")
    priority = models.PositiveIntegerField(default=0, verbose_name="Ileri tutma", help_text="0 = Ileri tutma ýok, 1 = Iň ýokary, 2 = Ikinji, we ş.m.", db_index=True)
    expiration_date = models.DateField(verbose_name="Möhleti", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Ýagdaý", help_text="Işjeň bildirişler frontend-de görkezilýär", db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Bölüm")
    village = models.ForeignKey(Village, on_delete=models.CASCADE, verbose_name="Ýer")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Kim goşdy", related_name='created_announcements')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kim tassyklady", related_name='approved_announcements')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Haçan tassyklandy")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Haçan üýtgedildi")

    def clean(self):
        super().clean()
        if self.phone_number:
            # Remove any spaces, dashes, or special characters
            cleaned = re.sub(r'[^\d+]', '', self.phone_number)
            
            # If it starts with +993, extract the 8 digits
            if cleaned.startswith('+993'):
                digits = cleaned[4:]
            elif cleaned.startswith('993'):
                digits = cleaned[3:]
            else:
                digits = cleaned.lstrip('+')
            
            # Validate that we have exactly 8 digits
            if not re.match(r'^\d{8}$', digits):
                raise ValidationError({'phone_number': 'Phone number must be exactly 8 digits after country code +993'})
            
            # Store in format +993XXXXXXXX
            self.phone_number = f'+993{digits}'

    def save(self, *args, **kwargs):
        self.full_clean()
        # Automatically set status to expired if expiration date has passed
        if self.expiration_date < timezone.now().date():
            self.status = 'expired'
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if announcement has expired"""
        return self.expiration_date < timezone.now().date() or self.status == 'expired'

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Bildiriş"
        verbose_name_plural = "Bildirişler"
        indexes = [
            # Optimize main listing query: status + priority + created_at
            models.Index(fields=['status', '-priority', '-created_at'], name='ann_status_priority_idx'),
            # Optimize category filtering: status + category + created_at
            models.Index(fields=['status', 'category', '-created_at'], name='ann_status_cat_idx'),
            # Optimize expiration checks: expiration_date + status
            models.Index(fields=['expiration_date', 'status'], name='ann_exp_status_idx'),
        ]

class Photo(models.Model):
    image = models.ImageField(upload_to=announcement_image_path, verbose_name="Surat")
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, verbose_name="Bildiriş", related_name='photos', db_index=True)

    def save(self, *args, **kwargs):
        # Only compress image if it's new or has been changed
        if self.pk is None:
            # New instance - compress if image exists
            if self.image:
                self.image = compress_image(self.image)
        else:
            # Existing instance - only compress if image changed
            try:
                old_instance = Photo.objects.get(pk=self.pk)
                if old_instance.image != self.image:
                    if self.image:
                        self.image = compress_image(self.image)
            except Photo.DoesNotExist:
                if self.image:
                    self.image = compress_image(self.image)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Surat"
        verbose_name_plural = "Suratlar"

class Banner(models.Model):
    photo = models.ImageField(upload_to='banners/', verbose_name="Surat")
    announcement = models.OneToOneField(Announcement, on_delete=models.CASCADE, verbose_name="Bildiriş")

    def save(self, *args, **kwargs):
        # Only compress image if it's new or has been changed
        if self.pk is None:
            # New instance - compress if photo exists
            if self.photo:
                self.photo = compress_image(self.photo)
        else:
            # Existing instance - only compress if photo changed
            try:
                old_instance = Banner.objects.get(pk=self.pk)
                if old_instance.photo != self.photo:
                    if self.photo:
                        self.photo = compress_image(self.photo)
            except Banner.DoesNotExist:
                if self.photo:
                    self.photo = compress_image(self.photo)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Bannerler"

class Favorite(models.Model):
    device_token = models.CharField(max_length=255, verbose_name="Enjam tokeni", db_index=True)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, verbose_name="Bildiriş")

    class Meta:
        unique_together = ('device_token', 'announcement')
        verbose_name = "Saýlanan"
        verbose_name_plural = "Saýlananlar"

class PendingAnnouncement(models.Model):
    """
    Stores new announcements created by managers that require admin approval.
    When approved, a real Announcement is created and this pending announcement is deleted.
    """
    name = models.CharField(max_length=200, verbose_name="Bildiriş")
    description = models.TextField(verbose_name="Düşündiriş")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    priority = models.PositiveIntegerField(default=0, verbose_name="Ileri tutma")
    expiration_date = models.DateField(verbose_name="Möhleti")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Bölüm")
    village = models.ForeignKey(Village, on_delete=models.CASCADE, verbose_name="Ýer")
    
    # Manager's message to admin explaining why to add this announcement
    message_to_admin = models.TextField(blank=True, verbose_name="Administratora habar", help_text="Bu bildirişiň sebäbini düşündiriň")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Kim goşdy", related_name='pending_announcements')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy", db_index=True)
    
    def clean(self):
        super().clean()
        if self.phone_number:
            # Remove any spaces, dashes, or special characters
            cleaned = re.sub(r'[^\d+]', '', self.phone_number)
            
            # If it starts with +993, extract the 8 digits
            if cleaned.startswith('+993'):
                digits = cleaned[4:]
            elif cleaned.startswith('993'):
                digits = cleaned[3:]
            else:
                digits = cleaned.lstrip('+')
            
            # Validate that we have exactly 8 digits
            if not re.match(r'^\d{8}$', digits):
                raise ValidationError({'phone_number': 'Phone number must be exactly 8 digits after country code +993'})
            
            # Store in format +993XXXXXXXX
            self.phone_number = f'+993{digits}'
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def approve(self, admin_user):
        """Create the actual announcement and delete this pending announcement."""
        announcement = Announcement.objects.create(
            name=self.name,
            description=self.description,
            phone_number=self.phone_number,
            priority=self.priority,
            expiration_date=self.expiration_date,
            category=self.category,
            village=self.village,
            created_by=self.created_by,
            approved_by=admin_user,
            approved_at=timezone.now()
        )
        
        # Copy photos if any
        for pending_photo in self.pending_photos.all():
            Photo.objects.create(
                announcement=announcement,
                image=pending_photo.image
            )
        
        # Delete this pending announcement
        self.delete()
        
        return announcement
    
    def reject(self):
        """Reject the pending announcement and delete it."""
        self.delete()
    
    def __str__(self):
        return f"Pending: {self.name} by {self.created_by}"
    
    class Meta:
        verbose_name = "Garaşylýan bildiriş"
        verbose_name_plural = "Garaşylýan bildirişler"
        ordering = ['-created_at']

class PendingAnnouncementPhoto(models.Model):
    """Photos associated with pending announcements."""
    image = models.ImageField(upload_to='announcements/pending/', verbose_name="Surat")
    pending_announcement = models.ForeignKey(PendingAnnouncement, on_delete=models.CASCADE, verbose_name="Garaşylýan bildiriş", related_name='pending_photos')

    def save(self, *args, **kwargs):
        # Only compress image if it's new or has been changed
        if self.pk is None:
            # New instance - compress if image exists
            if self.image:
                self.image = compress_image(self.image)
        else:
            # Existing instance - only compress if image changed
            try:
                old_instance = PendingAnnouncementPhoto.objects.get(pk=self.pk)
                if old_instance.image != self.image:
                    if self.image:
                        self.image = compress_image(self.image)
            except PendingAnnouncementPhoto.DoesNotExist:
                if self.image:
                    self.image = compress_image(self.image)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Garaşylýan bildirişiň suraty"
        verbose_name_plural = "Garaşylýan bildirişiň suratlary"

class PendingAnnouncementEdit(models.Model):
    """
    Stores pending edits made by managers that require admin approval.
    When approved, the original announcement is updated and this pending edit is deleted.
    """
    original_announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, verbose_name="Asyl bildiriş", related_name='pending_edits')
    
    # Fields that can be edited
    name = models.CharField(max_length=200, verbose_name="Bildiriş")
    description = models.TextField(verbose_name="Düşündiriş")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon")
    priority = models.PositiveIntegerField(default=0, verbose_name="Ileri tutma")
    expiration_date = models.DateField(verbose_name="Möhleti")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Bölüm")
    village = models.ForeignKey(Village, on_delete=models.CASCADE, verbose_name="Ýer")
    
    # Manager's message to admin explaining why to edit this announcement
    message_to_admin = models.TextField(blank=True, verbose_name="Administratora habar", help_text="Bu üýtgetmeleriň sebäbini düşündiriň")
    
    # Metadata
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Kim üýtgetdi", related_name='pending_edits')
    edited_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan üýtgedildi", db_index=True)
    
    def clean(self):
        super().clean()
        if self.phone_number:
            # Remove any spaces, dashes, or special characters
            cleaned = re.sub(r'[^\d+]', '', self.phone_number)
            
            # If it starts with +993, extract the 8 digits
            if cleaned.startswith('+993'):
                digits = cleaned[4:]
            elif cleaned.startswith('993'):
                digits = cleaned[3:]
            else:
                digits = cleaned.lstrip('+')
            
            # Validate that we have exactly 8 digits
            if not re.match(r'^\d{8}$', digits):
                raise ValidationError({'phone_number': 'Phone number must be exactly 8 digits after country code +993'})
            
            # Store in format +993XXXXXXXX
            self.phone_number = f'+993{digits}'
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def approve(self, admin_user):
        """Apply the pending changes to the original announcement and delete this pending edit."""
        announcement = self.original_announcement
        announcement.name = self.name
        announcement.description = self.description
        announcement.phone_number = self.phone_number
        announcement.priority = self.priority
        announcement.expiration_date = self.expiration_date
        announcement.category = self.category
        announcement.village = self.village
        announcement.approved_by = admin_user
        announcement.approved_at = timezone.now()
        announcement.save()
        
        # Copy photos if any
        for pending_photo in self.pending_photos.all():
            Photo.objects.create(
                announcement=announcement,
                image=pending_photo.image
            )
        
        # Delete this pending edit
        self.delete()
        
        return announcement
    
    def reject(self):
        """Reject the pending edit and delete it."""
        self.delete()
    
    def __str__(self):
        return f"Pending edit for: {self.original_announcement.name} by {self.edited_by}"
    
    class Meta:
        verbose_name = "Garaşylýan üýtgetme"
        verbose_name_plural = "Garaşylýan üýtgetmeler"
        ordering = ['-edited_at']

class PendingPhoto(models.Model):
    """Photos associated with pending announcement edits."""
    image = models.ImageField(upload_to='announcements/pending/', verbose_name="Surat")
    pending_edit = models.ForeignKey(PendingAnnouncementEdit, on_delete=models.CASCADE, verbose_name="Garaşylýan üýtgetme", related_name='pending_photos')

    def save(self, *args, **kwargs):
        # Only compress image if it's new or has been changed
        if self.pk is None:
            # New instance - compress if image exists
            if self.image:
                self.image = compress_image(self.image)
        else:
            # Existing instance - only compress if image changed
            try:
                old_instance = PendingPhoto.objects.get(pk=self.pk)
                if old_instance.image != self.image:
                    if self.image:
                        self.image = compress_image(self.image)
            except PendingPhoto.DoesNotExist:
                if self.image:
                    self.image = compress_image(self.image)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Garaşylýan üýtgetmeniň suraty"
        verbose_name_plural = "Garaşylýan üýtgetmeniň suratlary"
