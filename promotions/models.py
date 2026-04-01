from django.db import models
from announcements.models import Announcement
from announcements.image_utils import compress_image


class Promotion(models.Model):
    FREQUENCY_CHOICES = [
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('always', 'Always'),
    ]

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        verbose_name="Bildiriş",
        related_name='promotions',
    )
    photo = models.ImageField(upload_to='promotions/', verbose_name="Surat")
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='always',
        verbose_name="Ýygylygy",
    )
    is_active = models.BooleanField(default=True, verbose_name="Işjeň")
    priority = models.IntegerField(default=0, verbose_name="Ileri tutma", help_text="Pes saný ilki gökezilýär (0 = ileri tutma ýok)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Haçan üýtgedildi")

    def save(self, *args, **kwargs):
        # Compress image if it's too large
        if self.photo:
            self.photo = compress_image(self.photo)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['priority', '-created_at']
        verbose_name = "Mahabat"
        verbose_name_plural = "Mahabatlar"

    def __str__(self):
        return f"Promotion for {self.announcement.name}"
