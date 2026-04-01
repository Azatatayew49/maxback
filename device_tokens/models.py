from django.db import models


class DeviceToken(models.Model):
    token = models.CharField(max_length=255, unique=True, verbose_name="Token")
    fcm_token = models.TextField(blank=True, null=True, verbose_name="FCM Token")
    platform = models.CharField(max_length=20, verbose_name="Platforma", choices=[
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ], default='android')
    is_active = models.BooleanField(default=True, verbose_name="Işjeň")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Haçan üýtgedildi")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Enjam tokeni"
        verbose_name_plural = "Enjam tokenleri"

    def __str__(self):
        return f"{self.token[:20]}... ({self.platform})"


class NotificationLog(models.Model):
    title = models.CharField(max_length=255, verbose_name="Başlyk")
    body = models.TextField(verbose_name="Tekst")
    data = models.JSONField(blank=True, null=True, verbose_name="Maglumat")
    sent_to = models.IntegerField(default=0, verbose_name="Iberilenler")
    success_count = models.IntegerField(default=0, verbose_name="Ýetenýeterler")
    failure_count = models.IntegerField(default=0, verbose_name="Ýetenýtmeşlemeler")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bildiriş logsy"
        verbose_name_plural = "Bildiriş logslary"

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
