from django.core.management.base import BaseCommand
from contacts.models import Contact


class Command(BaseCommand):
    help = 'Create sample contact numbers'

    def handle(self, *args, **options):
        # Create sample contacts if they don't exist
        contacts_data = [
            {
                'label': 'Customer Support',
                'phone_number': '+1234567890',
                'order': 1,
                'is_active': True
            },
            {
                'label': 'Sales',
                'phone_number': '+1234567891',
                'order': 2,
                'is_active': True
            },
            {
                'label': 'Emergency',
                'phone_number': '+1234567892',
                'order': 3,
                'is_active': True
            },
        ]

        for contact_data in contacts_data:
            contact, created = Contact.objects.get_or_create(
                label=contact_data['label'],
                defaults=contact_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created contact: {contact.label}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Contact already exists: {contact.label}')
                )

        self.stdout.write(self.style.SUCCESS('Sample contacts creation completed!'))
