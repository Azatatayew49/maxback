"""
Utility functions for sending push notifications throughout the Django app.
Import this module to send notifications from any view, signal, or background task.

Example usage:
    from device_tokens.utils import notify_all, notify_platform, notify_device
    
    # Send to all devices
    notify_all("New Announcement", "Check out the latest announcement!")
    
    # Send to specific platform
    notify_platform("android", "Android Update", "New features available for Android!")
    
    # Send with custom data
    notify_all(
        "New Promotion",
        "50% off today!",
        data={"screen": "promotions", "promotion_id": "123"}
    )
"""

from .firebase_service import (
    send_notification_to_all,
    send_notification_to_platform,
    send_notification_to_device,
    send_notification_to_token
)
from .models import DeviceToken


def notify_all(title, body, data=None, image_url=None):
    """
    Quick function to send notification to all active devices
    
    Args:
        title (str): Notification title
        body (str): Notification body text
        data (dict, optional): Custom data payload
        image_url (str, optional): Image URL for rich notification
    
    Returns:
        dict: Result with success/failure counts
    
    Example:
        >>> notify_all("Hello", "Welcome to our app!")
        {'message': 'Notification sent successfully', 'sent_to': 5, 'success': 5, 'failure': 0}
    """
    return send_notification_to_all(title, body, data, image_url)


def notify_platform(platform, title, body, data=None, image_url=None):
    """
    Send notification to all devices of a specific platform
    
    Args:
        platform (str): Target platform ('android', 'ios', or 'web')
        title (str): Notification title
        body (str): Notification body text
        data (dict, optional): Custom data payload
        image_url (str, optional): Image URL for rich notification
    
    Returns:
        dict: Result with success/failure counts
    
    Example:
        >>> notify_platform("android", "Android Only", "Special message for Android users")
        {'message': 'Notification sent to android devices', 'sent_to': 3, 'success': 3, 'failure': 0}
    """
    if platform not in ['android', 'ios', 'web']:
        return {'error': f'Invalid platform: {platform}. Must be android, ios, or web'}
    
    return send_notification_to_platform(platform, title, body, data, image_url)


def notify_device(device_id, title, body, data=None, image_url=None):
    """
    Send notification to a specific device by DeviceToken ID
    
    Args:
        device_id (int): DeviceToken model ID
        title (str): Notification title
        body (str): Notification body text
        data (dict, optional): Custom data payload
        image_url (str, optional): Image URL for rich notification
    
    Returns:
        dict: Result with success status
    
    Example:
        >>> notify_device(1, "Personal Message", "This message is just for you!")
        {'success': True, 'message_id': '...'}
    """
    return send_notification_to_device(device_id, title, body, data, image_url)


def notify_token(fcm_token, title, body, data=None, image_url=None):
    """
    Send notification directly to an FCM token
    
    Args:
        fcm_token (str): Firebase Cloud Messaging token
        title (str): Notification title
        body (str): Notification body text
        data (dict, optional): Custom data payload
        image_url (str, optional): Image URL for rich notification
    
    Returns:
        dict: Result with success status
    
    Example:
        >>> notify_token("dXJx...", "Direct Message", "Sent via FCM token")
        {'success': True, 'message_id': '...'}
    """
    return send_notification_to_token(fcm_token, title, body, data, image_url)


# Convenience functions for common notification scenarios

def notify_new_announcement(announcement):
    """
    Send notification about a new announcement
    
    Args:
        announcement: Announcement model instance
    
    Example:
        >>> from announcements.models import Announcement
        >>> announcement = Announcement.objects.get(id=1)
        >>> notify_new_announcement(announcement)
    """
    return notify_all(
        title="New Announcement",
        body=announcement.title,
        data={
            "screen": "announcement_detail",
            "announcement_id": str(announcement.id),
            "type": "announcement"
        }
    )


def notify_new_promotion(promotion):
    """
    Send notification about a new promotion
    
    Args:
        promotion: Promotion model instance
    
    Example:
        >>> from promotions.models import Promotion
        >>> promotion = Promotion.objects.get(id=1)
        >>> notify_new_promotion(promotion)
    """
    return notify_all(
        title="New Promotion!",
        body=promotion.title,
        data={
            "screen": "promotion_detail",
            "promotion_id": str(promotion.id),
            "type": "promotion"
        },
        image_url=promotion.image.url if promotion.image else None
    )


def notify_custom(title, body, screen=None, extra_data=None, image_url=None):
    """
    Send a custom notification with flexible parameters
    
    Args:
        title (str): Notification title
        body (str): Notification body text
        screen (str, optional): Target screen to navigate to
        extra_data (dict, optional): Additional custom data
        image_url (str, optional): Image URL for rich notification
    
    Example:
        >>> notify_custom(
        ...     "Custom Alert",
        ...     "Something happened!",
        ...     screen="home",
        ...     extra_data={"user_id": "123", "action": "update"}
        ... )
    """
    data = extra_data.copy() if extra_data else {}
    if screen:
        data['screen'] = screen
    
    return notify_all(title, body, data, image_url)
