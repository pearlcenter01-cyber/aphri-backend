from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.services.match_service import MatchService
from app.websockets.chat_manager import chat_manager

async def handle_typing_websocket(websocket: WebSocket, match_id: str):
    """
    Handle WebSocket connection specifically for typing indicators
    This is separate from the main chat WebSocket for better performance
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
        # VERIFY MATCH ACCESS
        # ============================================================
        match = MatchService.get_match_by_id(db, match_id, user.id)
        if not match:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Match not found or access denied")
            return
        
        # ============================================================
        # CONNECT
        # ============================================================
        await websocket.accept()
        
        # ============================================================
        # TYPING INDICATOR LOOP
        # ============================================================
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                is_typing = message_data.get("is_typing", False)
                
                # Broadcast typing status to others in the match
                await chat_manager.broadcast_to_match(
                    match_id,
                    {
                        "type": "typing",
                        "user_id": str(user.id),
                        "is_typing": is_typing,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    exclude_user_id=str(user.id)
                )
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Typing WebSocket error: {e}")
                continue
    
    except WebSocketDisconnect:
        pass
    finally:
        db.close()