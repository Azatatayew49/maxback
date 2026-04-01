from django.core.management.base import BaseCommand
from device_tokens.firebase_service import send_notification_to_all, send_notification_to_platform
from device_tokens.models import DeviceToken


class Command(BaseCommand):
    help = 'Send a test push notification to registered devices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--title',
            type=str,
            default='Test Notification',
            help='Notification title'
        )
        parser.add_argument(
            '--body',
            type=str,
            default='This is a test notification from your Django backend!',
            help='Notification body text'
        )
        parser.add_argument(
            '--platform',
            type=str,
            choices=['android', 'ios', 'web', 'all'],
            default='all',
            help='Target platform (android, ios, web, or all)'
        )
        parser.add_argument(
            '--data',
            type=str,
            help='JSON string of custom data to include (e.g., \'{"screen": "home", "id": "123"}\')'
        )
        parser.add_argument(
            '--image',
            type=str,
            help='Image URL for the notification'
        )

    def handle(self, *args, **options):
        title = options['title']
        body = options['body']
        platform = options['platform']
        image_url = options.get('image')
        
        # Parse custom data if provided
        data = {}
        if options.get('data'):
            import json
            try:
                data = json.loads(options['data'])
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR('Invalid JSON in --data parameter'))
                return
        
        # Check if any devices are registered
        total_devices = DeviceToken.objects.filter(is_active=True).exclude(
            fcm_token__isnull=True
        ).exclude(fcm_token='').count()
        
        if total_devices == 0:
            self.stdout.write(self.style.WARNING('No active devices with FCM tokens found!'))
            self.stdout.write('Make sure devices have registered their tokens first.')
            return
        
        self.stdout.write(f'Found {total_devices} active device(s) with FCM tokens')
        self.stdout.write(f'Sending notification to {platform} devices...')
        self.stdout.write(f'Title: {title}')
        self.stdout.write(f'Body: {body}')
        if data:
            self.stdout.write(f'Data: {data}')
        if image_url:
            self.stdout.write(f'Image: {image_url}')
        
        # Send notification
        if platform == 'all':
            result = send_notification_to_all(
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
        else:
            result = send_notification_to_platform(
                platform=platform,
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
        
        # Display results
        self.stdout.write('\n' + '='*50)
        if 'error' in result:
            self.stdout.write(self.style.ERROR(f'Error: {result["error"]}'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ Notification sent successfully!'))
            self.stdout.write(f'Sent to: {result["sent_to"]} device(s)')
            self.stdout.write(self.style.SUCCESS(f'Success: {result["success"]}'))
            if result['failure'] > 0:
                self.stdout.write(self.style.WARNING(f'Failed: {result["failure"]}'))
        self.stdout.write('='*50)
