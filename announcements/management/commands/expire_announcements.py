from django.core.management.base import BaseCommand
from django.utils import timezone
from announcements.models import Announcement


class Command(BaseCommand):
    help = 'Updates announcements status to expired if expiration_date has passed'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find all active announcements that have expired
        expired_announcements = Announcement.objects.filter(
            status='active',
            expiration_date__lt=today
        )
        
        count = expired_announcements.count()
        
        if count > 0:
            expired_announcements.update(status='expired')
            self.stdout.write(
                self.style.SUCCESS(f'Successfully marked {count} announcement(s) as expired')
            )
            
            # List the expired announcements
            for announcement in expired_announcements:
                self.stdout.write(f'  - {announcement.id}: {announcement.name}')
        else:
            self.stdout.write(
                self.style.SUCCESS('No announcements to expire')
            )
