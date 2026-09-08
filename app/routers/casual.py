from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.casual import CasualQuestion, CasualResponse
from app.models.photo import Photo
from app.models.profile import Profile
from app.dependencies import get_current_user
from app.utils.constants import UserStatus

router = APIRouter(prefix="/api/casual", tags=["casual"])


# ============================================================
# POST A QUESTION
# ============================================================
@router.post("/questions")
async def post_question(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Post a "Who's ready for fun?" question
    Limit: 1 question per day
    """
    # Check if user already has an active question
    existing_question = db.query(CasualQuestion).filter(
        CasualQuestion.asker_id == current_user.id,
        CasualQuestion.is_active == True,
        CasualQuestion.expires_at > datetime.utcnow()
    ).first()
    
    if existing_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active question. Delete it or wait for it to expire."
        )
    
    # Check daily limit (1 question per day)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_questions = db.query(CasualQuestion).filter(
        CasualQuestion.asker_id == current_user.id,
        CasualQuestion.created_at >= today_start
    ).count()
    
    if todays_questions >= 1:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You can only post 1 question per day. Try again tomorrow."
        )
    
    # Create question (expires in 12 hours)
    expires_at = datetime.utcnow() + timedelta(hours=12)
    
    question = CasualQuestion(
        asker_id=current_user.id,
        question_text="Who's ready for fun today?",
        expires_at=expires_at
    )
    
    db.add(question)
    db.commit()
    db.refresh(question)
    
    return {
        "id": str(question.id),
        "question": question.question_text,
        "expires_at": expires_at.isoformat(),
        "message": "Your question has been posted! It will expire in 12 hours."
    }


# ============================================================
# GET ACTIVE QUESTIONS
# ============================================================
@router.get("/questions")
async def get_active_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all active questions from other casual users
    """
    # Only casual users see casual questions
    if current_user.looking_for != "Intimate Connection":
        return []
    
    # Get active questions from other users
    questions = db.query(CasualQuestion).filter(
        CasualQuestion.asker_id != current_user.id,
        CasualQuestion.is_active == True,
        CasualQuestion.expires_at > datetime.utcnow()
    ).order_by(CasualQuestion.created_at.desc()).all()
    
    result = []
    for q in questions:
        # Check if current user already responded
        existing_response = db.query(CasualResponse).filter(
            CasualResponse.question_id == q.id,
            CasualResponse.responder_id == current_user.id
        ).first()
        
        # Get response count
        response_count = db.query(CasualResponse).filter(
            CasualResponse.question_id == q.id
        ).count()
        
        result.append({
            "id": str(q.id),
            "question": q.question_text,
            "expires_at": q.expires_at.isoformat(),
            "time_remaining": int((q.expires_at - datetime.utcnow()).total_seconds() / 60),  # minutes
            "response_count": response_count,
            "has_responded": existing_response is not None,
            "is_anonymous": True  # Always anonymous until response
        })
    
    return result


# ============================================================
# GET MY ACTIVE QUESTION
# ============================================================
@router.get("/questions/my")
async def get_my_question(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current user's active question with responses
    """
    question = db.query(CasualQuestion).filter(
        CasualQuestion.asker_id == current_user.id,
        CasualQuestion.is_active == True,
        CasualQuestion.expires_at > datetime.utcnow()
    ).first()
    
    if not question:
        return {
            "has_active_question": False,
            "message": "You don't have an active question."
        }
    
    # Get responses
    responses = db.query(CasualResponse).filter(
        CasualResponse.question_id == question.id
    ).all()
    
    response_data = []
    for resp in responses:
        responder = db.query(User).filter(User.id == resp.responder_id).first()
        
        # Get responder's photos
        photos = db.query(Photo).filter(
            Photo.user_id == resp.responder_id
        ).order_by(Photo.order.asc()).all()
        photo_urls = [photo.url_thumbnail for photo in photos]
        
        # Get responder's profile
        profile = db.query(Profile).filter(Profile.user_id == resp.responder_id).first()
        
        response_data.append({
            "id": str(resp.id),
            "responder_id": str(resp.responder_id),
            "response_type": resp.response_type,
            "is_selected": resp.is_selected,
            "is_accepted": resp.is_accepted,
            "user": {
                "first_name": responder.first_name if responder else None,
                "last_name": responder.last_name if responder else None,
                "age": responder.age if responder else None,
                "gender": responder.gender if responder else None,
                "bio": profile.bio if profile else None,
                "photos": photo_urls
            } if responder else None,
            "created_at": resp.created_at.isoformat()
        })
    
    return {
        "has_active_question": True,
        "id": str(question.id),
        "question": question.question_text,
        "expires_at": question.expires_at.isoformat(),
        "time_remaining": int((question.expires_at - datetime.utcnow()).total_seconds() / 60),
        "responses": response_data,
        "response_count": len(response_data)
    }


# ============================================================
# RESPOND TO A QUESTION
# ============================================================
@router.post("/respond")
async def respond_to_question(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Respond to a casual question
    Body: { "question_id": "...", "response_type": "payment" | "mutual_fun" }
    """
    question_id = request.get("question_id")
    response_type = request.get("response_type")
    
    if not question_id or not response_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing question_id or response_type"
        )
    
    if response_type not in ["payment", "mutual_fun"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="response_type must be 'payment' or 'mutual_fun'"
        )
    
    # Get question
    question = db.query(CasualQuestion).filter(
        CasualQuestion.id == question_id,
        CasualQuestion.is_active == True,
        CasualQuestion.expires_at > datetime.utcnow()
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found or expired"
        )
    
    # Can't respond to own question
    if question.asker_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot respond to your own question"
        )
    
    # Check if already responded
    existing_response = db.query(CasualResponse).filter(
        CasualResponse.question_id == question_id,
        CasualResponse.responder_id == current_user.id
    ).first()
    
    if existing_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already responded to this question"
        )
    
    # Create response
    response = CasualResponse(
        question_id=question_id,
        responder_id=current_user.id,
        response_type=response_type
    )
    
    db.add(response)
    db.commit()
    db.refresh(response)
    
    return {
        "id": str(response.id),
        "question_id": str(question_id),
        "response_type": response_type,
        "message": "Your response has been sent!"
    }


# ============================================================
# SELECT A RESPONDER
# ============================================================
@router.post("/select")
async def select_responder(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Select a responder from your question
    Body: { "response_id": "...", "accept": true }
    """
    response_id = request.get("response_id")
    accept = request.get("accept", True)
    
    if not response_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing response_id"
        )
    
    # Get response
    response = db.query(CasualResponse).filter(
        CasualResponse.id == response_id
    ).first()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found"
        )
    
    # Check if user owns the question
    question = db.query(CasualQuestion).filter(
        CasualQuestion.id == response.question_id,
        CasualQuestion.asker_id == current_user.id,
        CasualQuestion.is_active == True
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this question or it's expired"
        )
    
    # Mark response as selected
    response.is_selected = True
    response.is_accepted = accept
    
    # Get the responder's info
    responder = db.query(User).filter(User.id == response.responder_id).first()
    
    db.commit()
    
    return {
        "message": f"You selected {responder.first_name} {responder.last_name}!",
        "responder_id": str(response.responder_id),
        "response_type": response.response_type,
        "is_accepted": response.is_accepted,
        "phone_number": responder.phone if response.is_accepted else None,
        "note": "Phone number revealed after acceptance. Contact them via WhatsApp or Telegram."
    }


# ============================================================
# DELETE A QUESTION
# ============================================================
@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete your active question
    """
    question = db.query(CasualQuestion).filter(
        CasualQuestion.id == question_id,
        CasualQuestion.asker_id == current_user.id
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Soft delete - just mark inactive
    question.is_active = False
    db.commit()
    
    return {
        "message": "Your question has been deleted.",
        "id": str(question_id)
    }


# ============================================================
# GET RESPONSES FOR MY QUESTION
# ============================================================
@router.get("/questions/{question_id}/responses")
async def get_question_responses(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all responses for a question you own
    """
    question = db.query(CasualQuestion).filter(
        CasualQuestion.id == question_id,
        CasualQuestion.asker_id == current_user.id
    ).first()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    responses = db.query(CasualResponse).filter(
        CasualResponse.question_id == question_id
    ).all()
    
    result = []
    for resp in responses:
        responder = db.query(User).filter(User.id == resp.responder_id).first()
        
        # Get responder's photos
        photos = db.query(Photo).filter(
            Photo.user_id == resp.responder_id
        ).order_by(Photo.order.asc()).all()
        photo_urls = [photo.url_thumbnail for photo in photos]
        
        # Get responder's profile
        profile = db.query(Profile).filter(Profile.user_id == resp.responder_id).first()
        
        result.append({
            "id": str(resp.id),
            "response_type": resp.response_type,
            "is_selected": resp.is_selected,
            "is_accepted": resp.is_accepted,
            "responder": {
                "id": str(resp.responder_id),
                "first_name": responder.first_name if responder else None,
                "last_name": responder.last_name if responder else None,
                "age": responder.age if responder else None,
                "gender": responder.gender if responder else None,
                "bio": profile.bio if profile else None,
                "photos": photo_urls
            } if responder else None,
            "created_at": resp.created_at.isoformat()
        })
    
    return result