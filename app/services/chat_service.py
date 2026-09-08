from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
import uuid
from app.models.message import Message
from app.models.match import Match
from app.models.user import User
from app.utils.constants import MessageType

class ChatService:
    """Service for chat message management"""
    
    @staticmethod
    def send_message(
        db: Session,
        match_id: str,
        sender_id: str,
        receiver_id: str,  # ✅ ADDED receiver_id parameter
        content: str,
        message_type: str = MessageType.TEXT,
        media_url: Optional[str] = None,
        media_thumbnail: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message in a match"""
        # Verify match exists and user is part of it
        match = db.query(Match).filter(
            Match.id == match_id,
            Match.is_active == True
        ).first()
        
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        if match.user_1_id != sender_id and match.user_2_id != sender_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this match")
        
        # ✅ Check if chat is unlocked using chat_unlocked_at
        if not match.chat_unlocked_at or datetime.utcnow() < match.chat_unlocked_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat is not unlocked yet. You must become a real match first."
            )
        
        # Check if blocked
        from app.services.report_service import ReportService
        if ReportService.is_blocked(db, receiver_id, sender_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot message this user"
            )
        
        # Create message
        message = Message(
            match_id=match_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            media_url=media_url,
            media_thumbnail=media_thumbnail,
            session_id=session_id
        )
        
        db.add(message)
        db.flush()
        
        # Update match
        match.last_message_at = datetime.utcnow()
        match.last_message_preview = content[:200] if content else "[Media]"
        match.message_count += 1
        match.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return {
            "id": str(message.id),
            "match_id": str(match_id),
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "message_type": message.message_type,
            "content": message.content,
            "media_url": message.media_url,
            "media_thumbnail": message.media_thumbnail,
            "is_read": message.is_read,
            "created_at": message.created_at.isoformat(),
            "session_id": session_id
        }
    
    @staticmethod
    def mark_message_as_read(db: Session, message_id: str, user_id: str) -> bool:
        """Mark a message as read"""
        message = db.query(Message).filter(
            Message.id == message_id,
            Message.receiver_id == user_id
        ).first()
        
        if not message:
            return False
        
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.commit()
        
        return True
    
    @staticmethod
    def mark_all_as_read(db: Session, match_id: str, user_id: str) -> int:
        """Mark all messages in a match as read"""
        count = db.query(Message).filter(
            Message.match_id == match_id,
            Message.receiver_id == user_id,
            Message.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        
        db.commit()
        return count
    
    @staticmethod
    def delete_message(db: Session, message_id: str, user_id: str) -> bool:
        """Delete a message (soft delete)"""
        message = db.query(Message).filter(
            Message.id == message_id,
            Message.sender_id == user_id
        ).first()
        
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        
        message.is_deleted = True
        message.content = "[This message was deleted]"
        db.commit()
        
        return True
    
    @staticmethod
    def get_unread_count(db: Session, user_id: str) -> int:
        """Get total unread message count for a user"""
        return db.query(Message).filter(
            Message.receiver_id == user_id,
            Message.is_read == False
        ).count()

    # ============================================================
    # QUESTION GAME METHODS (New Feature)
    # ============================================================
    
    @staticmethod
    def send_question(
        db: Session,
        match_id: str,
        sender_id: str,
        receiver_id: str,
        question: str,
        question_index: int
    ) -> Dict[str, Any]:
        """Send a question as a message in chat"""
        
        # Send as normal message with type "question"
        result = ChatService.send_message(
            db,
            match_id,
            sender_id,
            receiver_id,  # ✅ Pass receiver_id
            question,
            message_type="question"
        )
        
        # Store question in separate table for tracking
        from app.models.chat_question import ChatQuestion
        
        chat_question = ChatQuestion(
            id=str(uuid.uuid4()).replace('-', ''),
            match_id=match_id,
            user_id=sender_id,
            candidate_id=receiver_id,
            question_index=question_index,
            question_text=question,
            is_answered=False
        )
        db.add(chat_question)
        db.commit()
        
        return {
            **result,
            "is_question": True,
            "question_index": question_index,
            "question_id": chat_question.id
        }
    
    @staticmethod
    def submit_answer(
        db: Session,
        match_id: str,
        user_id: str,
        answer: str
    ) -> Dict[str, Any]:
        """Submit an answer to a question"""
        
        from app.models.chat_question import ChatQuestion
        
        # Find the latest unanswered question for this match
        chat_question = db.query(ChatQuestion).filter(
            ChatQuestion.match_id == match_id,
            ChatQuestion.candidate_id == user_id,
            ChatQuestion.is_answered == False
        ).order_by(ChatQuestion.created_at.desc()).first()
        
        if not chat_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active question to answer"
            )
        
        # Get match
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        
        # Get sender
        sender_id = match.user_2_id if match.user_1_id == user_id else match.user_1_id
        
        # Send answer as normal message
        result = ChatService.send_message(
            db,
            match_id,
            user_id,
            sender_id,  # ✅ Pass sender_id as receiver
            answer,
            message_type="answer"
        )
        
        # Update question
        chat_question.answer_text = answer
        chat_question.is_answered = True
        chat_question.answered_at = datetime.utcnow()
        db.commit()
        
        return {
            **result,
            "is_answer": True,
            "question_id": chat_question.id,
            "question_index": chat_question.question_index,
            "need_rating": True
        }
    
    @staticmethod
    def rate_answer(
        db: Session,
        question_id: str,
        rating: int
    ) -> Dict[str, Any]:
        """Rate an answer (1-5)"""
        
        from app.models.chat_question import ChatQuestion
        from app.models.user import User
        from app.models.real_match import RealMatch
        from app.models.match import Match
        from app.services.swipe_service import SwipeService
        import json
        
        chat_question = db.query(ChatQuestion).filter(
            ChatQuestion.id == question_id
        ).first()
        
        if not chat_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        # Save rating
        chat_question.rating = rating
        chat_question.rated_at = datetime.utcnow()
        db.commit()
        
        # Get all 3 questions for this match
        all_questions = db.query(ChatQuestion).filter(
            ChatQuestion.match_id == chat_question.match_id,
            ChatQuestion.user_id == chat_question.user_id,
            ChatQuestion.candidate_id == chat_question.candidate_id
        ).all()
        
        # Check if all 3 are answered and rated
        answered_rated = [q for q in all_questions if q.is_answered and q.rating]
        
        if len(answered_rated) < 3:
            # Not complete, get next question
            other_user = db.query(User).filter(User.id == chat_question.user_id).first()
            next_index = len(answered_rated)
            
            if other_user and other_user.custom_questions:
                try:
                    questions = json.loads(other_user.custom_questions)
                    if next_index < len(questions):
                        return {
                            "is_complete": False,
                            "next_question": questions[next_index],
                            "question_index": next_index,
                            "progress": f"Question {next_index + 1} of 3"
                        }
                except:
                    pass
            
            return {
                "is_complete": True,
                "message": "No more questions available"
            }
        
        # All 3 questions complete - calculate final score
        user = db.query(User).filter(User.id == chat_question.user_id).first()
        candidate = db.query(User).filter(User.id == chat_question.candidate_id).first()
        
        if not user or not candidate:
            return {"error": "User not found"}
        
        # Calculate 8-question score
        compatibility = SwipeService.calculate_compatibility(user, candidate)
        eight_q_score = compatibility['score']
        
        # Calculate custom question score (average of 3 ratings, 1-5 -> 0-100)
        ratings = [q.rating for q in answered_rated]
        avg_rating = sum(ratings) / len(ratings)
        custom_score = (avg_rating / 5) * 100
        
        # Final score (average of both)
        final_score = (eight_q_score + custom_score) / 2
        
        # Save to match_question_game for tracking
        from app.models.match_question_game import MatchQuestionGame
        
        game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == chat_question.user_id,
            MatchQuestionGame.candidate_id == chat_question.candidate_id
        ).first()
        
        if game:
            game.is_complete = True
            game.final_score = final_score
            db.commit()
        
        # If 65%+, save as real match AND UNLOCK CHAT
        if final_score >= 65:
            # Check if already exists
            existing = db.query(RealMatch).filter(
                RealMatch.user_id == chat_question.user_id,
                RealMatch.matched_user_id == chat_question.candidate_id
            ).first()
            
            if not existing:
                real_match = RealMatch(
                    id=str(uuid.uuid4()).replace('-', ''),
                    user_id=chat_question.user_id,
                    matched_user_id=chat_question.candidate_id,
                    final_score=final_score
                )
                db.add(real_match)
                
                # ✅ UNLOCK THE CHAT
                match = db.query(Match).filter(Match.id == chat_question.match_id).first()
                if match:
                    match.chat_unlocked_at = datetime.utcnow()
                
                db.commit()
            
            return {
                "is_complete": True,
                "final_score": final_score,
                "is_match": True,
                "message": f"🎉 Match! You and {candidate.full_name} are now a real match!"
            }
        else:
            return {
                "is_complete": True,
                "final_score": final_score,
                "is_match": False,
                "message": f"Score: {int(final_score)}%. Keep going!"
            }