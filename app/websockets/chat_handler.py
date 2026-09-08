from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
import json
from typing import Dict, Any
from datetime import datetime

from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.services.match_service import MatchService
from app.services.chat_service import ChatService
from app.services.push_service import PushService
from app.websockets.chat_manager import chat_manager
from app.utils.constants import MessageType

async def handle_chat_websocket(websocket: WebSocket, match_id: str):
    """
    Handle WebSocket connection for real-time chat in a specific match
    """
    db = SessionLocal()
    
    try:
        # ============================================================
        # AUTHENTICATE USER
        # ============================================================
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
            return
        
        # Validate token and get user
        try:
            user = await AuthService.get_current_user(db, token)
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # ============================================================
        # VERIFY MATCH ACCESS
        # ============================================================
        match = MatchService.get_match_by_id(db, match_id, user.id)
        if not match:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Match not found or access denied")
            return
        
        # ============================================================
        # CONNECT TO WEBSOCKET
        # ============================================================
        await chat_manager.connect(match_id, str(user.id), websocket)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "match_id": match_id,
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send online users in the match
        online_users = chat_manager.get_online_users_in_match(match_id)
        await websocket.send_json({
            "type": "online_users",
            "users": list(online_users)
        })
        
        # ============================================================
        # MESSAGE LOOP
        # ============================================================
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process based on message type
                message_type = message_data.get("type", "message")
                
                if message_type == "message":
                    # Send a chat message
                    content = message_data.get("content", "")
                    media_url = message_data.get("media_url")
                    media_thumbnail = message_data.get("media_thumbnail")
                    msg_type = message_data.get("message_type", MessageType.TEXT)
                    
                    # Save message to database
                    message = ChatService.send_message(
                        db,
                        match_id,
                        user.id,
                        content,
                        msg_type,
                        media_url,
                        media_thumbnail
                    )
                    
                    # Get other user
                    other_user_id = match.get_other_user_id(user.id)
                    
                    # Broadcast to all users in the match
                    await chat_manager.broadcast_to_match(
                        match_id,
                        {
                            "type": "new_message",
                            "match_id": match_id,
                            "message": message
                        }
                    )
                    
                    # Send push notification to other user
                    if other_user_id:
                        await PushService.send_new_message_notification(
                            db,
                            other_user_id,
                            match_id,
                            user.first_name or "User",
                            content
                        )
                
                elif message_type == "typing":
                    # Typing indicator
                    is_typing = message_data.get("is_typing", True)
                    
                    # Broadcast typing status to others
                    await chat_manager.broadcast_to_match(
                        match_id,
                        {
                            "type": "typing",
                            "user_id": str(user.id),
                            "is_typing": is_typing
                        },
                        exclude_user_id=str(user.id)
                    )
                
                elif message_type == "read_receipt":
                    # Mark messages as read
                    message_ids = message_data.get("message_ids", [])
                    for msg_id in message_ids:
                        ChatService.mark_message_as_read(db, msg_id, user.id)
                    
                    # Broadcast read receipt
                    await chat_manager.broadcast_to_match(
                        match_id,
                        {
                            "type": "read_receipt",
                            "user_id": str(user.id),
                            "message_ids": message_ids,
                            "read_at": datetime.utcnow().isoformat()
                        },
                        exclude_user_id=str(user.id)
                    )
                
                elif message_type == "ping":
                    # Keep connection alive
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                continue
            except Exception as e:
                print(f"Error processing message: {e}")
                continue
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # ============================================================
        # DISCONNECT AND CLEANUP
        # ============================================================
        try:
            # Remove connection from manager
            chat_manager.disconnect(match_id, str(user.id))
            
            # Notify others that user went offline
            await chat_manager.broadcast_to_match(
                match_id,
                {
                    "type": "user_offline",
                    "user_id": str(user.id),
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user_id=str(user.id)
            )
            
            # Update user's online status in database
            if user:
                user.is_online = False
                user.last_active_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        finally:
            db.close()