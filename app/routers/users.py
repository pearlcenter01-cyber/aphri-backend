from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.photo import Photo
from app.dependencies import get_current_user
from app.services.user_service import UserService

router = APIRouter(prefix="/api/users", tags=["users"])


# ============================================================
# GET CURRENT USER PROFILE
# ============================================================
@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current user's full profile
    """
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    photos = db.query(Photo).filter(
        Photo.user_id == current_user.id
    ).order_by(Photo.order.asc()).all()

    photo_urls = [photo.url_thumbnail for photo in photos]

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "age": current_user.age,
        "gender": current_user.gender,
        "date_of_birth": current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,

        "looking_for": current_user.looking_for,
        "looking_for_gender": current_user.looking_for_gender,
        "intimate_type": current_user.intimate_type,
        "looking_for_age_min": current_user.looking_for_age_min,
        "looking_for_age_max": current_user.looking_for_age_max,

        "religion": current_user.religion,
        "religion_preferences": current_user.religion_preferences,

        "is_single_parent": current_user.is_single_parent,
        "is_divorced": current_user.is_divorced,
        "open_to_single_parent": current_user.open_to_single_parent,
        "open_to_divorced": current_user.open_to_divorced,

        "city": current_user.city,
        "country": current_user.country,
        "latitude": current_user.latitude,
        "longitude": current_user.longitude,

        "quote": current_user.quote,
        "has_voice_note": current_user.has_voice_note,
        "voice_note_url": current_user.voice_note_url,
        "has_quote": current_user.has_quote,

        "photos": photo_urls,

        "bio": profile.bio if profile else None,
        "headline": profile.headline if profile else None,
        "interests": profile.interests.split(",") if profile and profile.interests else [],

        "subscription_status": current_user.subscription_status.value,
        "is_verified": current_user.is_verified,
        "is_online": current_user.is_online,
        "last_active_at": current_user.last_active_at.isoformat() if current_user.last_active_at else None,

        "photos_revealed": current_user.photos_revealed,
        "photo_reveal_date": current_user.photo_reveal_date.isoformat() if current_user.photo_reveal_date else None,

        "compatibility_score_8q": current_user.compatibility_score_8q,
        "compatibility_score_custom": current_user.compatibility_score_custom,
        "compatibility_score_final": current_user.compatibility_score_final,

        "custom_questions": current_user.custom_questions,

        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }


# ============================================================
# GET USER BY ID
# ============================================================
@router.get("/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get another user's profile (limited visibility based on match status)
    """
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    from app.models.match import Match
    from sqlalchemy import or_, and_

    match = db.query(Match).filter(
        or_(
            and_(Match.user_1_id == current_user.id, Match.user_2_id == user_id),
            and_(Match.user_1_id == user_id, Match.user_2_id == current_user.id)
        ),
        Match.is_active == True
    ).first()

    is_matched = match is not None

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    photos = db.query(Photo).filter(
        Photo.user_id == user.id
    ).order_by(Photo.order.asc()).all()

    photo_urls = []
    can_see_photos = is_matched or (current_user.looking_for != "Serious Relationship") or user.photos_revealed

    if can_see_photos:
        photo_urls = [photo.url_thumbnail for photo in photos]
    else:
        photo_urls = ["placeholder_blurred" for _ in photos] if photos else []

    return {
        "id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "age": user.age,
        "gender": user.gender,
        "city": user.city,
        "country": user.country,

        "bio": profile.bio if profile else None,
        "headline": profile.headline if profile else None,
        "interests": profile.interests.split(",") if profile and profile.interests else [],

        "quote": user.quote,
        "has_voice_note": user.has_voice_note,
        "voice_note_url": user.voice_note_url,
        "has_quote": user.has_quote,

        "photos": photo_urls,
        "photos_revealed": can_see_photos,

        "compatibility_score": None,
        "is_matched": is_matched,

        "is_online": user.is_online,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
    }


# ============================================================
# UPDATE PROFILE
# ============================================================
@router.put("/me")
async def update_my_profile(
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update the current user's profile
    """
    updatable_fields = [
        "first_name", "last_name", "gender", "date_of_birth",
        "looking_for", "looking_for_gender", "intimate_type",
        "looking_for_age_min", "looking_for_age_max",
        "religion", "religion_preferences",
        "is_single_parent", "is_divorced", "open_to_single_parent", "open_to_divorced",
        "city", "country", "latitude", "longitude",
        "quote", "custom_questions"
    ]

    for field in updatable_fields:
        if field in profile_data and profile_data[field] is not None:
            setattr(current_user, field, profile_data[field])

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    profile_updatable = ["bio", "headline", "interests"]
    for field in profile_updatable:
        if field in profile_data and profile_data[field] is not None:
            if field == "interests" and isinstance(profile_data[field], list):
                setattr(profile, field, ",".join(profile_data[field]))
            else:
                setattr(profile, field, profile_data[field])

    db.commit()
    db.refresh(current_user)

    return {"message": "Profile updated successfully"}


# ============================================================
# UPDATE LOCATION
# ============================================================
@router.post("/me/location")
async def update_location(
    location_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update the user's location
    """
    if "latitude" in location_data:
        current_user.latitude = location_data["latitude"]
    if "longitude" in location_data:
        current_user.longitude = location_data["longitude"]
    if "city" in location_data:
        current_user.city = location_data["city"]
    if "country" in location_data:
        current_user.country = location_data["country"]

    current_user.location_updated_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Location updated successfully",
        "latitude": current_user.latitude,
        "longitude": current_user.longitude,
        "city": current_user.city,
        "country": current_user.country
    }


# ============================================================
# CHECK PHOTO REVEAL STATUS
# ============================================================
@router.get("/me/photo-reveal-status")
async def get_photo_reveal_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if the user's photos are revealed
    """
    is_revealed = current_user.photos_revealed
    reveal_time = None

    if current_user.photo_reveal_date:
        reveal_time = current_user.photo_reveal_date.isoformat()
        time_remaining = int((current_user.photo_reveal_date - datetime.utcnow()).total_seconds() / 60)
        if time_remaining < 0:
            time_remaining = 0
    else:
        time_remaining = None

    return {
        "photos_revealed": is_revealed,
        "photo_reveal_date": reveal_time,
        "time_remaining_minutes": time_remaining,
        "message": "Your photos are revealed!" if is_revealed else f"Your photos will be revealed in {time_remaining} minutes"
    }


# ============================================================
# DELETE ACCOUNT
# ============================================================
@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Permanently delete the current user's account and all related data.
    """
    from app.models.match import Match
    from app.models.message import Message
    from app.models.swipe import Swipe
    from app.models.chat_question import ChatQuestion
    from app.models.match_question_game import MatchQuestionGame
    from app.models.real_match import RealMatch
    from app.models.compatibility import (
        CompatibilitySession, CompatibilityQuestion, CompatibilityResponse,
    )
    from sqlalchemy import text

    user_id = str(current_user.id)

    # ---- ORM tables ----
    db.query(Message).filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).delete(synchronize_session=False)

    db.query(ChatQuestion).filter(
        (ChatQuestion.user_id == user_id) | (ChatQuestion.candidate_id == user_id)
    ).delete(synchronize_session=False)

    db.query(MatchQuestionGame).filter(
        (MatchQuestionGame.user_id == user_id) | (MatchQuestionGame.candidate_id == user_id)
    ).delete(synchronize_session=False)

    db.query(RealMatch).filter(
        (RealMatch.user_id == user_id) | (RealMatch.matched_user_id == user_id)
    ).delete(synchronize_session=False)

    db.query(Swipe).filter(
        (Swipe.swiper_id == user_id) | (Swipe.swiped_id == user_id)
    ).delete(synchronize_session=False)

    db.query(Match).filter(
        (Match.user_1_id == user_id) | (Match.user_2_id == user_id)
    ).delete(synchronize_session=False)

    # ---- Compatibility sessions and their children ----
    sessions = db.query(CompatibilitySession).filter(
        (CompatibilitySession.user_id == user_id) |
        (CompatibilitySession.partner_id == user_id)
    ).all()
    session_ids = [s.id for s in sessions]
    if session_ids:
        db.query(CompatibilityResponse).filter(
            CompatibilityResponse.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        db.query(CompatibilityQuestion).filter(
            CompatibilityQuestion.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        db.query(CompatibilitySession).filter(
            CompatibilitySession.id.in_(session_ids)
        ).delete(synchronize_session=False)

    # Also clean orphan responses by user
    db.query(CompatibilityResponse).filter(
        CompatibilityResponse.user_id == user_id
    ).delete(synchronize_session=False)

    # ---- Raw-SQL tables (no ORM models imported in this file) ----
    for table, col in [
        ("casual_questions", "asker_id"),
        ("subscriptions", "user_id"),
        ("notifications", "user_id"),
        ("payments", "user_id"),
    ]:
        db.execute(text(f"DELETE FROM {table} WHERE {col} = :uid"), {"uid": user_id})

    for table, col_a, col_b in [
        ("reports", "reported_id", "reporter_id"),
        ("blocks", "blocked_id", "blocker_id"),
        ("casual_responses", "responder_id", "responder_id"),
        ("casual_payments", "partner_id", "user_id"),
    ]:
        db.execute(
            text(f"DELETE FROM {table} WHERE {col_a} = :uid OR {col_b} = :uid"),
            {"uid": user_id},
        )

    # ---- Photos and profile ----
    db.query(Photo).filter(Photo.user_id == user_id).delete(synchronize_session=False)
    db.query(Profile).filter(Profile.user_id == user_id).delete(synchronize_session=False)

    # ---- The user ----
    db.delete(current_user)
    db.commit()

    return {"message": "Account permanently deleted."}