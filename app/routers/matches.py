from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Dict, Any, List
import json
from uuid import UUID, uuid4

from app.models.real_match import RealMatch
from app.models.match import Match
from app.models.answer import Answer
from app.database import get_db
from app.services.auth_service import AuthService
from app.services.match_service import MatchService
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.services.swipe_service import SwipeService
from app.models.user import User
from app.dependencies import get_current_user
from datetime import datetime
from app.models.message import Message
from app.services.credit_service import CreditService
router = APIRouter()


def _require_chat_access(user: User):
    """
    Chat access requires an active subscription AND credits remaining.
    Premium (unlimited-credit) subscribers always pass.
    """
    from app.utils.constants import UserStatus

    has_subscription = user.subscription_status == UserStatus.PREMIUM
    has_credits = user.has_unlimited_credits or (user.credits_remaining or 0) > 0

    if not has_subscription or not has_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription with credits required to access chats.",
        )







# ============================================================
# MATCH ENDPOINTS
# ============================================================

@router.get("/")
async def get_my_matches(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all matches for current user
    """
    return MatchService.get_user_matches(db, current_user.id, limit)

@router.get("/casual")
async def get_casual_matches(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    return SwipeService.get_casual_matches(db, current_user.id, limit)    


@router.get("/{match_id}")
async def get_match_details(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get details of a specific match
    """
    if not match_id or match_id == "{}" or match_id == "null" or match_id == "undefined":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid match ID"
        )
    
    match = MatchService.get_match_by_id(db, match_id, current_user.id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
        
    match = MatchService.get_match_by_id(db, match_id, current_user.id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    other_user_id = match.get_other_user_id(current_user.id)
    other_user = UserService.get_user_by_id(db, other_user_id)
    
    return {
        "match_id": str(match.id),
        "matched_at": match.matched_at.isoformat(),
        "chat_unlocked": match.is_chat_unlocked,
        "chat_unlocked_at": match.chat_unlocked_at.isoformat() if match.chat_unlocked_at else None,
        "other_user": {
            "id": str(other_user.id) if other_user else None,
            "first_name": other_user.first_name if other_user else None,
            "last_name": other_user.last_name if other_user else None,
        } if other_user else None,
        "is_active": match.is_active,
        "message_count": match.message_count
    }


@router.delete("/{match_id}")
async def unmatch(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Unmatch (deactivate a match)
    """
    MatchService.unmatch(db, match_id, current_user.id)
    return {"message": "Unmatched successfully"}


@router.get("/{match_id}/messages")
async def get_match_messages(
    match_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get messages for a match
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.user_1_id != current_user.id and match.user_2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not part of this match")

    # ✅ Subscription + credits required to open a chat
    _require_chat_access(current_user)

    return MatchService.get_match_messages(db, match_id, current_user.id, limit, offset)


@router.post("/{match_id}/messages")
async def send_message(
    match_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Send a message in a match
    Body: { "content": "Hello!" }
    """
    content = request.get("content")
    message_type = request.get("message_type", "text")
    session_id = request.get("session_id")
    
    # Handle both string and dict content
    if isinstance(content, dict):
        content_text = content.get("content") or content.get("text") or str(content)
    else:
        content_text = content
    
    if not content_text or not content_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required"
        )
    
    # Check if chat is unlocked
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.user_1_id != current_user.id and match.user_2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not part of this match")
    
    if not match.chat_unlocked_at or datetime.utcnow() < match.chat_unlocked_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat is not unlocked yet. You must become a real match first."
        )
    
    # ✅ Get receiver
    receiver_id = match.user_2_id if match.user_1_id == current_user.id else match.user_1_id
    
    # ✅ Send message - ChatService.send_message returns a dict
    message_data = ChatService.send_message(
    db,
    match_id,
    current_user.id,
    receiver_id,
    content_text,
    message_type,
    None,  # media_url
    None,  # media_thumbnail
    session_id  # ✅ session_id goes here
)
    
    return message_data  # ✅ Return the dict directly

@router.post("/{match_id}/approve")
async def approve_match(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approve a match - unlocks chat when both users approve
    """
    result = MatchService.approve_match(db, match_id, current_user.id)
    return result


@router.get("/{match_id}/chat-status")
async def get_chat_status(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if chat is unlocked for a match
    """
    return MatchService.get_match_with_chat_status(db, match_id, current_user.id)


@router.get("/count")
async def get_match_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, int]:
    """
    Get total match count
    """
    count = MatchService.get_match_count(db, current_user.id)
    return {"count": count}


# ============================================================
# PENDING QUESTIONS
# ============================================================


@router.post("/questions/answer")
async def answer_question(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mark a question as answered
    Body: { "question_id": "user_id_0" }
    """
    print(f"Received request: {request}")
    
    question_id = request.get("question_id")
    if not question_id:
        print("No question_id provided")
        raise HTTPException(status_code=400, detail="question_id is required")
    
    print(f"question_id: {question_id}")
    print(f"current_user.id: {current_user.id} (type: {type(current_user.id)})")
    
    try:
        user_uuid = current_user.id
        if isinstance(user_uuid, str):
            user_uuid = UUID(user_uuid)
        print(f"user_uuid: {user_uuid} (type: {type(user_uuid)})")
        
        existing = db.query(Answer).filter(
            Answer.user_id == user_uuid,
            Answer.question_id == question_id
        ).first()
        print(f"Existing answer: {existing}")
        
        if not existing:
            new_answer = Answer(
                id=uuid4(),
                user_id=user_uuid,
                question_id=question_id,
                created_at=datetime.utcnow()
            )
            db.add(new_answer)
            db.commit()
            print(f"Created new answer: {new_answer.id}")
        else:
            print(f"Answer already exists")
        
        return {"message": "Question marked as answered", "success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error in answer_question: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.get("/answers/received")
async def get_received_answers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        user_uuid = current_user.id
        if isinstance(user_uuid, str):
            user_uuid = UUID(user_uuid)
        
        print(f"RECEIVED ANSWERS CALLED for user: {user_uuid}")
        print(f"user_uuid: {user_uuid}")
        print(f"Querying chat_questions with user_id = {user_uuid}")
        
        chat_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_uuid,
            ChatQuestion.answer_text.isnot(None),
            ChatQuestion.is_answered == True
        ).all()
        
        print(f"Found {len(chat_questions)} answered questions")
        for q in chat_questions:
            print(f"Processing question: {q.id}")
            print(f"   question_index: {q.question_index}")
            print(f"   answer_text: {q.answer_text}")
            print(f"   candidate_id: {q.candidate_id}")
        
        received_answers = []
        
        for q in chat_questions:
            other_user = db.query(UserModel).filter(UserModel.id == q.candidate_id).first()
            if not other_user:
                continue
            
            question_text = "Question"
            if current_user.custom_questions:
                try:
                    questions = json.loads(current_user.custom_questions)
                    if q.question_index < len(questions):
                        question_text = questions[q.question_index]
                except:
                    pass
            
            received_answers.append({
                "id": str(q.id),
                "question_id": q.question_id,
                "question": question_text,
                "answer": q.answer_text or "No answer provided",
                "from_user_id": str(other_user.id),
                "from_user_name": other_user.full_name,
                "answered_at": q.answered_at.isoformat() if q.answered_at else q.created_at.isoformat(),
                "read": False
            })
        
        print(f"Total received answers: {len(received_answers)}")
        
        return {
            "has_received": len(received_answers) > 0,
            "count": len(received_answers),
            "answers": received_answers
        }
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"has_received": False, "count": 0, "answers": []}


@router.get("/answers/received-test")
async def test_received_answers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Test endpoint to debug received answers"""
    try:
        user_uuid = current_user.id
        if isinstance(user_uuid, str):
            user_uuid = UUID(user_uuid)
        
        print(f"Testing for user: {user_uuid}")
        
        all_answers = db.query(Answer).all()
        print(f"Total answers in DB: {len(all_answers)}")
        
        for a in all_answers:
            print(f"   Answer: user_id={a.user_id}, question_id={a.question_id}, answer={a.answer}")
        
        my_question_pattern = f"{user_uuid}_%"
        answers_to_me = db.query(Answer).filter(
            Answer.question_id.like(my_question_pattern)
        ).all()
        print(f"Answers to your questions: {len(answers_to_me)}")
        
        return {
            "total_answers": len(all_answers),
            "answers_to_me": len(answers_to_me),
            "debug": "Check backend logs"
        }
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# ============================================================
# QUESTION GAME ENDPOINTS
# ============================================================

from app.services.question_game_service import QuestionGameService


@router.get("/game/start")
async def start_question_game(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Start or resume the question game
    """
    result = QuestionGameService.start_or_get_game(current_user.id, db)
    
    if result.get('status') == 'no_candidates':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidates available"
        )
    
    return result


@router.post("/game/answer")
async def submit_game_answer(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submit an answer to the current question
    Body: { "candidate_id": "...", "answer": "..." }
    """
    candidate_id = request.get("candidate_id")
    answer = request.get("answer")
    
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id is required")
    if not answer or not answer.strip():
        raise HTTPException(status_code=400, detail="answer is required")
    
    result = QuestionGameService.submit_question_answer(
        current_user.id,
        candidate_id,
        answer,
        db
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/game/rate")
async def rate_game_answers(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rate all 3 answers for a candidate
    Body: { "candidate_id": "...", "ratings": [4, 5, 3] }
    """
    candidate_id = request.get("candidate_id")
    ratings = request.get("ratings")
    
    if not candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id is required")
    if not ratings or not isinstance(ratings, list) or len(ratings) != 3:
        raise HTTPException(status_code=400, detail="Must provide exactly 3 ratings (1-5)")
    
    for r in ratings:
        if not isinstance(r, int) or r < 1 or r > 5:
            raise HTTPException(status_code=400, detail="Ratings must be integers between 1 and 5")
    
    result = QuestionGameService.rate_answers(
        current_user.id,
        candidate_id,
        ratings,
        db
    )
    
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/game/rate-single")
async def rate_single_answer(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Rate a single answer - no game record required
    Body: { "question_id": "...", "rating": 4 }
    """
    from app.models.chat_question import ChatQuestion
    from app.models.match_question_game import MatchQuestionGame
    from app.models.user import User
    from datetime import datetime
    from uuid import UUID, uuid4
    import json
    
    question_id = request.get("question_id")
    rating = request.get("rating")
    
    print(f"rate-single called with question_id: {question_id}, rating: {rating}")
    
    if not question_id:
        raise HTTPException(status_code=400, detail="question_id is required")
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating must be 1-5")
    
    try:
        user_uuid = UUID(current_user.id)
        
        question = db.query(ChatQuestion).filter(ChatQuestion.id == question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # ✅ DEDUCT 1 CREDIT on first rating of this question set
        already_rated = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == question.user_id,
            ChatQuestion.candidate_id == question.candidate_id,
            ChatQuestion.rating.isnot(None)
        ).count()
        
        if already_rated == 0:
            CreditService.spend_credits(
                db,
                user_id=current_user.id,
                amount=1,
                action="rate_answers",
            )
        
        question.rating = rating
        question.rated_at = datetime.utcnow()
        db.commit()
        
        game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == question.user_id,
            MatchQuestionGame.candidate_id == question.candidate_id,
            MatchQuestionGame.is_complete == False
        ).first()
        
        if game:
            all_questions = db.query(ChatQuestion).filter(
                ChatQuestion.user_id == question.user_id,
                ChatQuestion.candidate_id == question.candidate_id
            ).all()
            
            rated = [q for q in all_questions if q.is_answered and q.rating]
            
            if len(rated) >= 3:
                return QuestionGameService._calculate_final_score(game, db)
            
            next_question = db.query(ChatQuestion).filter(
                ChatQuestion.user_id == question.user_id,
                ChatQuestion.candidate_id == question.candidate_id,
                ChatQuestion.is_answered == False
            ).order_by(ChatQuestion.question_index).first()
            
            if next_question:
                return {
                    'status': 'next_question',
                    'question_id': next_question.id,
                    'question_text': next_question.question_text,
                    'question_index': next_question.question_index,
                    'total_questions': 3,
                    'progress': f'Question {next_question.question_index + 1} of 3'
                }
            
            return {
                'status': 'complete',
                'message': 'All questions answered and rated',
                'game_id': game.id
            }
        
        # ✅ No game record - handle potential match
        # Check if there are more questions to ask
        all_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == question.user_id,
            ChatQuestion.candidate_id == question.candidate_id
        ).all()
        
        answered = [q for q in all_questions if q.is_answered]
        rated = [q for q in all_questions if q.is_answered and q.rating]
        
        # Get the user who asked the question
        asker = db.query(User).filter(User.id == question.user_id).first()
        
        # Check if all 3 questions are answered AND rated
        if len(rated) >= 3:
            # All 3 rated - calculate score (create real match if applicable)
            # Create a game record to use existing calculation
            game = MatchQuestionGame(
                id=str(uuid4()).replace('-', ''),
                user_id=question.user_id,
                candidate_id=question.candidate_id,
                is_complete=False
            )
            db.add(game)
            db.commit()
            return QuestionGameService._calculate_final_score(game, db)
        print(f"🔍 ASKER: {asker}")
        print(f"🔍 ASKER EMAIL: {asker.email if asker else 'None'}")
        print(f"🔍 ASKER CUSTOM QUESTIONS: {asker.custom_questions if asker else 'None'}")
        
        # Check if there are more questions to ask
        if asker and asker.custom_questions:
            try:
                custom_questions = json.loads(asker.custom_questions)
                next_index = len(answered)  # 0, 1, 2
                
                if next_index < len(custom_questions):
                    # Create the next question
                    new_question = ChatQuestion(
                        id=str(uuid4()).replace('-', ''),
                        match_id=None,
                        user_id=question.user_id,
                        candidate_id=question.candidate_id,
                        question_index=next_index,
                        question_text=custom_questions[next_index],
                        is_answered=False
                    )
                    db.add(new_question)
                    db.commit()
                    
                    return {
                        'status': 'next_question',
                        'question_id': new_question.id,
                        'question_text': new_question.question_text,
                        'question_index': new_question.question_index,
                        'total_questions': 3,
                        'progress': f'Question {new_question.question_index + 1} of 3'
                    }
            except Exception as e:
                print(f"Error creating next question: {e}")
        
        # No more questions
        return {
            'status': 'complete',
            'message': 'All questions answered',
            'question_id': question_id,
            'rating': rating
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error in rate_single_answer: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questions/pending")
async def get_pending_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get items that need the current user's action:
    - Questions delivered to them that they haven't answered
    - Answers delivered to them that they haven't rated
    """
    try:
        from app.models.chat_question import ChatQuestion

        user_uuid = current_user.id
        if isinstance(user_uuid, str):
            user_uuid = UUID(user_uuid)
        user_uuid_str = str(user_uuid)
        print(f"User UUID: {user_uuid}")

        potential_matches = SwipeService.get_matches(db, current_user.id, 50)
        potential_ids = {m.get('id') for m in potential_matches if m.get('id')}
        print(f"Potential matches found: {len(potential_ids)}")

        pending_questions = []

        # 1. Questions delivered to me, not yet answered
        unanswered = db.query(ChatQuestion).filter(
            ChatQuestion.candidate_id == user_uuid_str,
            ChatQuestion.is_answered == False,
        ).all()
        for q in unanswered:
            if q.user_id not in potential_ids:
                continue
            other_user = db.query(User).filter(User.id == q.user_id).first()
            if not other_user:
                continue
            pending_questions.append({
                "id": f"{q.user_id}_{q.question_index}",
                "match_id": q.user_id,
                "match_name": other_user.full_name,
                "question": q.question_text,
                "answered": False,
            })

        # 2. Answers delivered to me, not yet rated
        unrated = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_uuid_str,
            ChatQuestion.is_answered == True,
            ChatQuestion.rating.is_(None),
        ).all()
        for q in unrated:
            if q.candidate_id not in potential_ids:
                continue
            other_user = db.query(User).filter(User.id == q.candidate_id).first()
            if not other_user:
                continue
            pending_questions.append({
                "id": f"{q.candidate_id}_{q.question_index}",
                "match_id": q.candidate_id,
                "match_name": other_user.full_name,
                "question": q.question_text,
                "answered": True,
            })

        print(f"Total pending questions: {len(pending_questions)}")
        return {
            "has_pending": len(pending_questions) > 0,
            "questions": pending_questions,
        }
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"has_pending": False, "questions": []}


@router.get("/game/questions/{candidate_id}")
async def get_game_questions(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all questions and answers for a game between two users"""
    from app.models.chat_question import ChatQuestion

    try:
        user_uuid = UUID(current_user.id)
        candidate_uuid = UUID(candidate_id)

        user_uuid_str = str(user_uuid)
        candidate_uuid_str = str(candidate_uuid)

        print(f"Getting questions between {user_uuid_str} and {candidate_uuid_str}")

        match = db.query(Match).filter(
            or_(
                and_(Match.user_1_id == user_uuid_str, Match.user_2_id == candidate_uuid_str),
                and_(Match.user_1_id == candidate_uuid_str, Match.user_2_id == user_uuid_str),
            )
        ).first()

        # ✅ Subscription + credits required to view questions
        _require_chat_access(current_user)

        questions = db.query(ChatQuestion).filter(
            or_(
                and_(ChatQuestion.user_id == user_uuid_str, ChatQuestion.candidate_id == candidate_uuid_str),
                and_(ChatQuestion.user_id == candidate_uuid_str, ChatQuestion.candidate_id == user_uuid_str)
            )
        ).order_by(ChatQuestion.question_index).all()

        print(f"Found {len(questions)} questions")

        return {
            "questions": [
                {
                    "id": str(q.id),
                    "user_id": str(q.user_id),
                    "candidate_id": str(q.candidate_id),
                    "question_index": q.question_index,
                    "question_text": q.question_text,
                    "answer_text": q.answer_text,
                    "rating": q.rating,
                    "is_answered": q.is_answered,
                    "created_at": q.created_at.isoformat(),
                    "answered_at": q.answered_at.isoformat() if q.answered_at else None,
                }
                for q in questions
            ],
            "user_id": user_uuid_str,
            "candidate_id": candidate_uuid_str,
        }
    except Exception as e:
        print(f"Error getting game questions: {e}")
        import traceback
        traceback.print_exc()
        return {"questions": []}


        
@router.get("/game/all-questions")
async def get_all_game_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all questions and answers for the current user (both asked and received).
    Only returns users who are also mutual potential matches (same rule as Home screen)."""
    from app.models.chat_question import ChatQuestion

    try:
        user_uuid = UUID(current_user.id)

        print(f"Looking for questions involving user: {user_uuid}")

        # ✅ Ask SwipeService for the real mutual matches
        valid_candidates = SwipeService.get_matches(db, current_user.id, 500)
        valid_user_ids = {str(c.get('id')) for c in valid_candidates if c.get('id')}
        print(f"Mutual matches: {len(valid_user_ids)}")

        questions = db.query(ChatQuestion).filter(
            or_(
                ChatQuestion.user_id == str(user_uuid),
                ChatQuestion.candidate_id == str(user_uuid)
            )
        ).all()

        print(f"Found {len(questions)} total chat questions")

        result = []
        for q in questions:
            if str(q.user_id) == str(user_uuid):
                other_id = str(q.candidate_id)
            else:
                other_id = str(q.user_id)

            # ✅ Skip if the other user isn't a mutual match
            if other_id not in valid_user_ids:
                print(f"🔴 Skipping non-mutual chat question: {other_id}")
                continue

            other_user = db.query(User).filter(User.id == other_id).first()
            other_name = other_user.full_name if other_user else "Unknown"

            result.append({
                "match_id": other_id,
                "match_name": other_name,
                "question_text": q.question_text,
                "answer_text": q.answer_text,
                "is_answered": q.is_answered,
                "question_index": q.question_index,
                "created_at": q.created_at.isoformat(),
            })

        print(f"Returning {len(result)} results")
        return result
    except Exception as e:
        print(f"Error getting all game questions: {e}")
        import traceback
        traceback.print_exc()
        return []



@router.post("/start-chat")
async def start_chat(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Find or create a Match between current_user and another user. Returns match_id."""
    other_user_id = request.get("other_user_id")
    if not other_user_id:
        raise HTTPException(status_code=400, detail="other_user_id is required")
    if other_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself")

    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Match).filter(
        or_(
            and_(Match.user_1_id == current_user.id, Match.user_2_id == other_user_id),
            and_(Match.user_1_id == other_user_id, Match.user_2_id == current_user.id),
        )
    ).first()

    if existing:
        return {"match_id": str(existing.id), "created": False}

    now = datetime.utcnow()
    new_match = Match(
        user_1_id=current_user.id,
        user_2_id=other_user_id,
        user_1_swiped_at=now,
        user_2_swiped_at=now,
        matched_at=now,
        chat_unlocked_at=now,
        is_active=True,
        initiator_id=current_user.id,
    )
    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return {"match_id": str(new_match.id), "created": True}


@router.get("/game/matches")
async def get_game_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all game matches for the current user
    Returns users who have completed the question game (all 3 questions answered and rated)
    """
    from app.models.chat_question import ChatQuestion
    from app.models.match_question_game import MatchQuestionGame
    from uuid import UUID
    
    try:
        user_uuid = str(UUID(current_user.id))
        print(f"🔍 Getting game matches for user: {user_uuid}")
        
        # Get all games where user is involved
        games = db.query(MatchQuestionGame).filter(
            or_(
                MatchQuestionGame.user_id == user_uuid,
                MatchQuestionGame.candidate_id == user_uuid
            )
        ).all()
        
        print(f"🔍 Found {len(games)} games")
        
        matches = []
        for game in games:
            # Determine the other user
            if game.user_id == user_uuid:
                other_user_id = game.candidate_id
            else:
                other_user_id = game.user_id
            
            # Get the other user's details
            other_user = db.query(User).filter(User.id == other_user_id).first()
            if not other_user:
                continue
            
            # Get all questions between these two users
            questions = db.query(ChatQuestion).filter(
                or_(
                    and_(ChatQuestion.user_id == user_uuid, ChatQuestion.candidate_id == other_user_id),
                    and_(ChatQuestion.user_id == other_user_id, ChatQuestion.candidate_id == user_uuid)
                )
            ).all()
            
            # Check if all questions are answered and rated
            answered = [q for q in questions if q.is_answered]
            rated = [q for q in questions if q.is_answered and q.rating is not None]
            
            # Calculate score if all 3 are rated
            score = 0
            if len(rated) >= 3:
                avg_rating = sum(q.rating for q in rated) / len(rated)
                score = min(100, int(avg_rating * 20))  # Convert to percentage
            
            matches.append({
                "user_id": other_user_id,
                "name": other_user.full_name or f"{other_user.first_name} {other_user.last_name or ''}".strip(),
                "score": score,
                "question_count": len(questions),
                "answered_count": len(answered),
                "rated_count": len(rated),
                "is_complete": len(rated) >= 3
            })
        
        return {
            "matches": matches,
            "total": len(matches)
        }
        
    except Exception as e:
        print(f"❌ Error getting game matches: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"matches": [], "total": 0}        


@router.post("/potential-match/answer")
async def potential_match_answer(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Save answer for a potential match
    Body: { "candidate_id": "...", "question_index": 0, "answer": "..." }
    """
    from app.models.chat_question import ChatQuestion
    from datetime import datetime
    
    candidate_id = request.get("candidate_id")
    question_index = request.get("question_index")
    answer = request.get("answer")
    
    if not candidate_id or question_index is None or not answer:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    existing = db.query(ChatQuestion).filter(
        ChatQuestion.user_id == candidate_id,
        ChatQuestion.candidate_id == current_user.id,
        ChatQuestion.question_index == question_index
    ).first()
    
    # ✅ DEDUCT 1 CREDIT on first answer to this user
    if not existing:
        CreditService.spend_credits(
            db,
            user_id=current_user.id,
            amount=1,
            action="answer_questions",
        )
    
    if existing:
        existing.answer_text = answer
        existing.is_answered = True
        existing.answered_at = datetime.utcnow()
    else:
        candidate = db.query(User).filter(User.id == candidate_id).first()
        if not candidate or not candidate.custom_questions:
            raise HTTPException(status_code=400, detail="No custom questions found")
        
        questions = json.loads(candidate.custom_questions)
        if question_index >= len(questions):
            raise HTTPException(status_code=400, detail="Invalid question index")
        
        new_question = ChatQuestion(
            id=str(uuid4()).replace('-', ''),
            match_id=None,
            user_id=candidate_id,
            candidate_id=current_user.id,
            question_index=question_index,
            question_text=questions[question_index],
            answer_text=answer,
            is_answered=True,
            created_at=datetime.utcnow(),
            answered_at=datetime.utcnow()
        )
        db.add(new_question)
    
    db.commit()
    
    return {"success": True, "message": "Answer saved"}

@router.post("/{match_id}/unlock")
async def unlock_chat(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unlock the chat for a match"""
    # Try to find match by ID first
    match = db.query(Match).filter(Match.id == match_id).first()
    
    # If not found, try to find by user IDs
    if not match:
        match = db.query(Match).filter(
            (Match.user_1_id == match_id) | (Match.user_2_id == match_id)
        ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.user_1_id != current_user.id and match.user_2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not part of this match")
    
    match.chat_unlocked_at = datetime.utcnow()  # ✅ This sets the timestamp
    match.chat_unlocked_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Chat unlocked successfully"}

@router.post("/{match_id}/read")
async def mark_messages_as_read(
    match_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mark all messages in a match as read for the current user
    """
    # Verify match exists and user is part of it
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match.user_1_id != current_user.id and match.user_2_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not part of this match")
    
    # Mark all unread messages as read
    count = db.query(Message).filter(
        Message.match_id == match_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    
    db.commit()
    
    return {
        "message": f"Marked {count} messages as read",
        "count": count
    }    

