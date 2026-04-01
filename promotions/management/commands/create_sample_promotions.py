"""
Example script to create sample promotions for testing
Run this after creating some announcements in the admin panel
"""

from django.core.management.base import BaseCommand
from announcements.models import Announcement
from promotions.models import Promotion


class Command(BaseCommand):
    help = 'Creates sample promotions for testing'

    def handle(self, *args, **options):
        # Get the first 3 announcements
        announcements = Announcement.objects.all()[:3]
        
        if not announcements:
            self.stdout.write(
                self.style.ERROR('No announcements found. Create some first!')
            )
            return

        # Create promotions with different frequencies
        frequencies = ['once', 'daily', 'weekly']
        
        for idx, announcement in enumerate(announcements):
            promotion, created = Promotion.objects.get_or_create(
                announcement=announcement,
                defaults={
                    'frequency': frequencies[idx % len(frequencies)],
                    'priority': (len(announcements) - idx) * 10,
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created promotion for: {announcement.name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Promotion already exists for: {announcement.name}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                '\nSample promotions created! '
                'Remember to upload images in the admin panel.'
            )
        )
