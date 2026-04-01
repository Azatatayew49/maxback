from django.db import models


class Contact(models.Model):
    label = models.CharField(max_length=100, verbose_name="Bellik", help_text="Habarlaşmak belliklerini girióiň (mysal: 'Goldaw', 'Satýw')")
    phone_number = models.CharField(max_length=20, verbose_name="Telefon", help_text="Telefon belgisi ýurt kody bilen")
    is_active = models.BooleanField(default=True, verbose_name="Işjeň", help_text="Bu habarlaşmak ulanyjýlara görezilýärmi")
    order = models.IntegerField(default=0, verbose_name="Tertip", help_text="Görkeziliş tertibi (pes sanlar ilki gökezilýär)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Haçan goşuldy")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Haçan üýtgedildi")

    class Meta:
        ordering = ['order', 'label']
        verbose_name = 'Habarlaşmak belgisi'
        verbose_name_plural = 'Habarlaşmak belgileri'

    def __str__(self):
        return f"{self.label}: {self.phone_number}"
