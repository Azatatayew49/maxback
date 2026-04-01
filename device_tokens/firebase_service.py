import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import DeviceToken, NotificationLog


# Initialize Firebase Admin SDK
def initialize_firebase():
    if not firebase_admin._apps:
        # Path to the service account key file
        cred_path = os.path.join(settings.BASE_DIR.parent, 'maxim-b4fbb-firebase-adminsdk-fbsvc-9f6de1904c.json')
        
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': 'maxim-b4fbb',
                })
                print("Firebase initialized successfully")
                return True
            except Exception as e:
                print(f"Firebase initialization error: {e}")
                return False
        else:
            print(f"Firebase credentials file not found at: {cred_path}")
            return False
    return True


def send_notification_to_all(title, body, data=None, image_url=None):
    """
    Send push notification to all active devices
    
    Args:
        title: Notification title
        body: Notification body text
        data: Optional dictionary of custom data
        image_url: Optional image URL for notification
    
    Returns:
        Dictionary with results
    """
    if not initialize_firebase():
        return {
            'error': 'Firebase not initialized',
            'sent_to': 0,
            'success': 0,
            'failure': 0
        }
    
    # Get all active device tokens with FCM tokens
    devices = DeviceToken.objects.filter(is_active=True).exclude(fcm_token__isnull=True).exclude(fcm_token='')
    
    if not devices.exists():
        return {
            'message': 'No active devices with FCM tokens found',
            'sent_to': 0,
            'success': 0,
            'failure': 0
        }
    
    fcm_tokens = [device.fcm_token for device in devices]
    
    # Prepare notification
    notification = messaging.Notification(
        title=title,
        body=body,
        image=image_url if image_url else None
    )
    
    # Prepare data payload
    data_payload = data if data else {}
    
    # FCM has a limit of 500 tokens per batch
    BATCH_SIZE = 500
    total_tokens = len(fcm_tokens)
    total_success = 0
    total_failure = 0
    all_failed_tokens = []
    
    # Send notifications in batches
    try:
        for i in range(0, total_tokens, BATCH_SIZE):
            batch_tokens = fcm_tokens[i:i + BATCH_SIZE]
            
            # Create message for this batch
            message = messaging.MulticastMessage(
                notification=notification,
                data={k: str(v) for k, v in data_payload.items()},  # Convert all values to strings
                tokens=batch_tokens,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        click_action='FLUTTER_NOTIFICATION_CLICK'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1
                        )
                    )
                )
            )
            
            # Send this batch
            response = messaging.send_each_for_multicast(message)
            
            # Count successes and failures for this batch
            batch_success = sum(1 for resp in response.responses if resp.success)
            batch_failure = len(response.responses) - batch_success
            
            total_success += batch_success
            total_failure += batch_failure
            
            # Collect failed tokens from this batch
            if batch_failure > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        all_failed_tokens.append(batch_tokens[idx])
        
        # Deactivate all failed tokens
        if all_failed_tokens:
            DeviceToken.objects.filter(fcm_token__in=all_failed_tokens).update(is_active=False)
        
        # Log notification
        NotificationLog.objects.create(
            title=title,
            body=body,
            data=data_payload,
            sent_to=total_tokens,
            success_count=total_success,
            failure_count=total_failure
        )
        
        return {
            'message': 'Notification sent successfully',
            'sent_to': total_tokens,
            'success': total_success,
            'failure': total_failure,
            'batches': (total_tokens + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'sent_to': total_tokens,
            'success': total_success,
            'failure': total_tokens - total_success
        }


def send_notification_to_token(fcm_token, title, body, data=None, image_url=None):
    """
    Send push notification to a specific FCM token
    """
    if not initialize_firebase():
        return {'error': 'Firebase not initialized'}
    
    notification = messaging.Notification(
        title=title,
        body=body,
        image=image_url if image_url else None
    )
    
    data_payload = {k: str(v) for k, v in (data if data else {}).items()}
    
    message = messaging.Message(
        notification=notification,
        data=data_payload,
        token=fcm_token,
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                sound='default',
                click_action='FLUTTER_NOTIFICATION_CLICK'
            )
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound='default',
                    badge=1
                )
            )
        )
    )
    
    try:
        response = messaging.send(message)
        return {'success': True, 'message_id': response}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_notification_to_platform(platform, title, body, data=None, image_url=None):
    """
    Send push notification to all devices of a specific platform
    
    Args:
        platform: 'android', 'ios', or 'web'
        title: Notification title
        body: Notification body text
        data: Optional dictionary of custom data
        image_url: Optional image URL for notification
    
    Returns:
        Dictionary with results
    """
    if not initialize_firebase():
        return {
            'error': 'Firebase not initialized',
            'sent_to': 0,
            'success': 0,
            'failure': 0
        }
    
    # Get active device tokens for the specified platform
    devices = DeviceToken.objects.filter(
        is_active=True,
        platform=platform
    ).exclude(fcm_token__isnull=True).exclude(fcm_token='')
    
    if not devices.exists():
        return {
            'message': f'No active {platform} devices with FCM tokens found',
            'sent_to': 0,
            'success': 0,
            'failure': 0
        }
    
    fcm_tokens = [device.fcm_token for device in devices]
    
    # Prepare notification
    notification = messaging.Notification(
        title=title,
        body=body,
        image=image_url if image_url else None
    )
    
    # Prepare data payload
    data_payload = data if data else {}
    
    # Create message
    message = messaging.MulticastMessage(
        notification=notification,
        data={k: str(v) for k, v in data_payload.items()},
        tokens=fcm_tokens,
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                sound='default',
                click_action='FLUTTER_NOTIFICATION_CLICK'
            )
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound='default',
                    badge=1
                )
            )
        )
    )
    
    # Send notification
    try:
        # Use send_each_for_multicast for the new API (v7.x)
        response = messaging.send_each_for_multicast(message)
        
        # Count successes and failures
        success_count = sum(1 for resp in response.responses if resp.success)
        failure_count = len(response.responses) - success_count
        
        # Handle failed tokens
        if failure_count > 0:
            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_tokens.append(fcm_tokens[idx])
            
            # Optionally deactivate failed tokens
            DeviceToken.objects.filter(fcm_token__in=failed_tokens).update(is_active=False)
        
        # Log notification
        NotificationLog.objects.create(
            title=title,
            body=body,
            data=data_payload,
            sent_to=len(fcm_tokens),
            success_count=success_count,
            failure_count=failure_count
        )
        
        return {
            'message': f'Notification sent to {platform} devices',
            'sent_to': len(fcm_tokens),
            'success': success_count,
            'failure': failure_count
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'sent_to': len(fcm_tokens),
            'success': 0,
            'failure': len(fcm_tokens)
        }


def send_notification_to_device(device_id, title, body, data=None, image_url=None):
    """
    Send push notification to a specific device by DeviceToken ID
    
    Args:
        device_id: DeviceToken model ID
        title: Notification title
        body: Notification body text
        data: Optional dictionary of custom data
        image_url: Optional image URL for notification
    
    Returns:
        Dictionary with result
    """
    try:
        device = DeviceToken.objects.get(id=device_id, is_active=True)
        if not device.fcm_token:
            return {'error': 'Device has no FCM token'}
        
        result = send_notification_to_token(
            fcm_token=device.fcm_token,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )
        
        if result.get('success'):
            # Log notification
            NotificationLog.objects.create(
                title=title,
                body=body,
                data=data,
                sent_to=1,
                success_count=1,
                failure_count=0
            )
        
        return result
    
    except DeviceToken.DoesNotExist:
        return {'error': 'Device not found or inactive'}
