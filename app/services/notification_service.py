from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.notification import Notification
from app.models.user import User
from app.utils.constants import NotificationType

class NotificationService:
    """Service for in-app notifications"""
    
    @staticmethod
    async def create_notification(
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        target_id: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> Notification:
        """Create an in-app notification"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            target_id=target_id,
            target_type=target_type,
            data_payload=json.dumps(data) if data else None
        )
        
        # In a real app, you'd save to database
        # For now, we'll just return the object
        
        return notification
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        only_unread: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        query = db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if only_unread:
            query = query.filter(Notification.is_read == False)
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        result = []
        for notification in notifications:
            result.append({
                "id": str(notification.id),
                "type": notification.notification_type,
                "title": notification.title,
                "body": notification.body,
                "data": json.loads(notification.data_payload) if notification.data_payload else None,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def mark_notification_as_read(db: Session, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if not notification:
            return False
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        
        return True
    
    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        
        db.commit()
        return count
    
    @staticmethod
    def get_unread_count(db: Session, user_id: str) -> int:
        """Get unread notification count for a user"""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()