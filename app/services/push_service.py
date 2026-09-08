from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import os
import json
import requests

from app.models.user import User
from app.models.notification import Notification
from app.utils.constants import NotificationType

class PushService:
    """Service for push notifications"""
    
    # In-memory token storage (for MVP)
    # In production, store in database
    push_tokens = {}  # user_id -> list of tokens
    
    @staticmethod
    def register_token(user_id: str, token: str, device_type: str) -> bool:
        """Register a device push token"""
        if user_id not in PushService.push_tokens:
            PushService.push_tokens[user_id] = []
        
        # Avoid duplicates
        if token not in PushService.push_tokens[user_id]:
            PushService.push_tokens[user_id].append({
                "token": token,
                "device_type": device_type,
                "registered_at": datetime.utcnow().isoformat()
            })
        
        return True
    
    @staticmethod
    def unregister_token(user_id: str, token: str) -> bool:
        """Unregister a device push token"""
        if user_id in PushService.push_tokens:
            PushService.push_tokens[user_id] = [
                t for t in PushService.push_tokens[user_id]
                if t["token"] != token
            ]
        
        return True
    
    @staticmethod
    def get_user_tokens(user_id: str) -> List[str]:
        """Get all push tokens for a user"""
        if user_id not in PushService.push_tokens:
            return []
        return [t["token"] for t in PushService.push_tokens[user_id]]
    
    @staticmethod
    async def send_push_notification(
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        notification_type: str = NotificationType.NEW_MESSAGE
    ) -> bool:
        """Send a push notification to a user"""
        tokens = PushService.get_user_tokens(user_id)
        if not tokens:
            return False
        
        # Save notification in database
        from app.services.notification_service import NotificationService
        await NotificationService.create_notification(
            user_id, notification_type, title, body, data
        )
        
        # Send via FCM (Firebase Cloud Messaging)
        fcm_key = os.getenv("FCM_SERVER_KEY")
        if not fcm_key:
            return False
        
        success_count = 0
        for token in tokens:
            try:
                response = requests.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers={
                        "Authorization": f"key={fcm_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "to": token,
                        "notification": {
                            "title": title,
                            "body": body,
                            "sound": "default",
                            "badge": 1
                        },
                        "data": data or {}
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                    
            except Exception as e:
                print(f"Failed to send push: {e}")
        
        return success_count > 0
    
    @staticmethod
    async def send_new_match_notification(db: Session, user_id: str, match_id: str, other_user_name: str) -> bool:
        """Send new match notification"""
        title = "New Match! 🎉"
        body = f"You matched with {other_user_name}!"
        data = {
            "type": "new_match",
            "match_id": match_id
        }
        
        return await PushService.send_push_notification(
            user_id, title, body, data, NotificationType.NEW_MATCH
        )
    
    @staticmethod
    async def send_new_message_notification(db: Session, user_id: str, match_id: str, sender_name: str, message: str) -> bool:
        """Send new message notification"""
        title = f"New message from {sender_name}"
        body = message[:200] if message else "Sent a message"
        data = {
            "type": "new_message",
            "match_id": match_id
        }
        
        return await PushService.send_push_notification(
            user_id, title, body, data, NotificationType.NEW_MESSAGE
        )