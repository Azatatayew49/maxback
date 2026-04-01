"""
Django management command to create an Announcement Manager user
Usage: python manage.py createmanager
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from announcements.models import Announcement, Photo
import getpass


class Command(BaseCommand):
    help = 'Create an Announcement Manager user with limited permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the manager',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the manager',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for input',
        )

    def create_announcement_manager_group(self):
        """Create or get the Announcement Manager group with appropriate permissions"""
        
        # Create or get the group
        group, created = Group.objects.get_or_create(name='Announcement Manager')
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created "Announcement Manager" group'))
        
        # Get content type for Announcement model
        announcement_content_type = ContentType.objects.get_for_model(Announcement)
        # Exclude delete permission - only admins can delete announcements
        announcement_permissions = Permission.objects.filter(
            content_type=announcement_content_type
        ).exclude(codename='delete_announcement')
        
        # Get content type for Photo model
        photo_content_type = ContentType.objects.get_for_model(Photo)
        photo_permissions = Permission.objects.filter(content_type=photo_content_type)
        
        # Combine all permissions
        all_permissions = list(announcement_permissions) + list(photo_permissions)
        
        # Add permissions to group
        group.permissions.set(all_permissions)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Added {len(all_permissions)} permissions ({announcement_permissions.count()} announcement + {photo_permissions.count()} photo)'))
        
        return group

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('Creating Announcement Manager User')
        self.stdout.write('=' * 60)
        self.stdout.write('')

        # Step 1: Ensure group exists
        self.create_announcement_manager_group()
        self.stdout.write('')

        # Step 2: Get username
        username = options.get('username')
        if not username:
            if options.get('noinput'):
                self.stderr.write(self.style.ERROR('Username is required when using --noinput'))
                return
            username = input('Username: ')
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(f'✗ User "{username}" already exists!'))
            return

        # Step 3: Get email
        email = options.get('email', '')
        if not email and not options.get('noinput'):
            email = input('Email address (optional): ')

        # Step 4: Get password
        if options.get('noinput'):
            self.stderr.write(self.style.ERROR('Password is required. Cannot use --noinput without providing password via environment or stdin'))
            return
        
        password = None
        while not password:
            password = getpass.getpass('Password: ')
            password2 = getpass.getpass('Password (again): ')
            
            if password != password2:
                self.stderr.write(self.style.ERROR('Passwords do not match. Please try again.'))
                password = None
                continue
            
            if len(password.strip()) < 3:
                self.stderr.write(self.style.ERROR('Password is too short. Please use at least 3 characters.'))
                password = None

        # Step 5: Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            is_staff=True,  # Must be staff to access admin
            is_superuser=False  # Not a superuser
        )
        
        # Get the group
        group = Group.objects.get(name='Announcement Manager')
        
        # Add user to group
        user.groups.add(group)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Created user "{username}"'))
        self.stdout.write(self.style.SUCCESS(f'✓ Added user to "Announcement Manager" group'))
        self.stdout.write('')
        self.stdout.write('📝 User can now login at: http://localhost:8000/admin/')
        self.stdout.write(f'   Username: {username}')
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('Setup complete!'))
        self.stdout.write('=' * 60)
