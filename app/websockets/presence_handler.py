from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.websockets.chat_manager import chat_manager

async def handle_presence_websocket(websocket: WebSocket):
    """
    Handle WebSocket connection for presence/online status
    This tracks user online/offline status across all matches
    """
    db = SessionLocal()
    
    try:
        # ============================================================
        # AUTHENTICATE USER
        # ============================================================
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
            return
        
        try:
            user = await AuthService.get_current_user(db, token)
            if not user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # ============================================================
        # CONNECT
        # ============================================================
        await websocket.accept()
        
        # Update user status to online
        user.is_online = True
        user.last_active_at = datetime.utcnow()
        db.commit()
        
        # Get all user's matches
        user_matches = chat_manager.get_all_user_matches(str(user.id))
        
        # Notify all matches that user is online
        for match_id in user_matches:
            await chat_manager.broadcast_to_match(
                match_id,
                {
                    "type": "user_online",
                    "user_id": str(user.id),
                    "timestamp": datetime.utcnow().isoformat()
                },
                exclude_user_id=str(user.id)
            )
        
        # Send initial presence info
        await websocket.send_json({
            "type": "presence_init",
            "user_id": str(user.id),
            "status": "online",
            "matches": list(user_matches)
        })
        
        # ============================================================
        # PRESENCE LOOP
        # ============================================================
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                action = message_data.get("action")
                
                if action == "heartbeat":
                    # Update last active timestamp
                    user.last_active_at = datetime.utcnow()
                    db.commit()
                    
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif action == "update_status":
                    # Manual status update
                    status = message_data.get("status", "online")
                    
                    if status == "offline":
                        user.is_online = False
                        db.commit()
                        
                        # Notify all matches
                        user_matches = chat_manager.get_all_user_matches(str(user.id))
                        for match_id in user_matches:
                            await chat_manager.broadcast_to_match(
                                match_id,
                                {
                                    "type": "user_offline",
                                    "user_id": str(user.id),
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                exclude_user_id=str(user.id)
                            )
                    else:
                        user.is_online = True
                        user.last_active_at = datetime.utcnow()
                        db.commit()
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Presence WebSocket error: {e}")
                continue
    
    except WebSocketDisconnect:
        pass
    finally:
        # ============================================================
        # DISCONNECT - MARK USER OFFLINE
        # ============================================================
        try:
            # Update user status to offline
            user.is_online = False
            user.last_active_at = datetime.utcnow()
            db.commit()
            
            # Get all user's matches
            user_matches = chat_manager.get_all_user_matches(str(user.id))
            
            # Notify all matches that user is offline
            for match_id in user_matches:
                await chat_manager.broadcast_to_match(
                    match_id,
                    {
                        "type": "user_offline",
                        "user_id": str(user.id),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    exclude_user_id=str(user.id)
                )
        except Exception:
            pass
        finally:
            db.close()