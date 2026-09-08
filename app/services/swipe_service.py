from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import json
import math
import uuid

from app.models.user import User
from app.models.swipe import Swipe
from app.models.match import Match
from app.models.profile import Profile
from app.models.photo import Photo
from app.utils.constants import UserStatus, MatchStatus

class SwipeService:
    """Service for swipe and match logic"""
    
    @staticmethod
    def get_daily_swipe_count(db: Session, user_id: str) -> int:
        """Get number of swipes today for a user"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        count = db.query(Swipe).filter(
            Swipe.swiper_id == user_id,
            Swipe.created_at >= today_start
        ).count()
        
        return count
    
    @staticmethod
    def can_swipe(db: Session, user_id: str) -> bool:
        """Check if a user can swipe today"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Premium users have unlimited swipes
        if user.subscription_status.value == "premium":
            return True
        
        # Free users have limited swipes
        daily_swipes = SwipeService.get_daily_swipe_count(db, user_id)
        max_swipes = 1000  # Free tier limit
        
        return daily_swipes < max_swipes
    
    # ============================================================
    # COMPATIBILITY CALCULATION
    # ============================================================
    
    @staticmethod
    def calculate_compatibility(user1: User, user2: User) -> dict:
        """
        Calculate compatibility score between two users
        Returns: {
            'score': 0-100 (final score),
            'score_8q': 0-100,
            'score_custom': 0-100,
            'breakdown': {...}
        }
        """
        # Calculate 8 questions score
        score_8q = SwipeService.calculate_8q_score(user1, user2)
        
        # Calculate custom questions score
        score_custom = SwipeService.calculate_custom_score(user1, user2)
        
        # Final score is average of both
        final_score = int((score_8q['score'] + score_custom['score']) / 2) if score_custom['score'] > 0 else score_8q['score']
        
        return {
            'score': final_score,
            'score_8q': score_8q['score'],
            'score_custom': score_custom['score'],
            'breakdown': {
                '8q': score_8q['breakdown'],
                'custom': score_custom['breakdown']
            }
        }
    
    @staticmethod
    def calculate_8q_score(user1: User, user2: User) -> dict:
        """
        Calculate score from 8 compatibility questions
        """
        # Define weights for each question (1-3)
        weights = {
            'q1': 3,  # Core Need - Fundamental
            'q2': 3,  # Sex & Intimacy - Major dealbreaker
            'q3': 2,  # Conflict Style - Important
            'q4': 2,  # Success Response - Important
            'q5': 3,  # Gender Roles - Fundamental
            'q6': 3,  # Religion - Fundamental
            'q7': 2,  # Crisis Response - Important
            'q8': 2,  # Emotional Maturity - Important
        }
        
        # Get answers
        a1 = user1.get_compatibility_answers()
        a2 = user2.get_compatibility_answers()
        
        total_weight = 0
        weighted_matches = 0
        breakdown = {}
        
        for q, weight in weights.items():
            total_weight += weight
            
            if a1.get(q) and a2.get(q):
                # Perfect match
                if a1[q] == a2[q]:
                    weighted_matches += weight
                    breakdown[q] = {'match': True, 'weight': weight, 'score': weight}
                # Partial match patterns
                elif q == 'q1':  # Core Need
                    if (a1[q] == 'trust_honesty' and a2[q] == 'stability_security') or \
                       (a1[q] == 'stability_security' and a2[q] == 'trust_honesty'):
                        weighted_matches += weight * 0.7
                        breakdown[q] = {'match': 'partial', 'weight': weight, 'score': weight * 0.7}
                    elif (a1[q] == 'fun_excitement' and a2[q] == 'growth_challenge') or \
                         (a1[q] == 'growth_challenge' and a2[q] == 'fun_excitement'):
                        weighted_matches += weight * 0.7
                        breakdown[q] = {'match': 'partial', 'weight': weight, 'score': weight * 0.7}
                    else:
                        breakdown[q] = {'match': False, 'weight': weight, 'score': 0}
                elif q == 'q6':  # Religion
                    if (a1[q] == 'big_part' and a2[q] == 'spiritual') or \
                       (a1[q] == 'spiritual' and a2[q] == 'big_part'):
                        weighted_matches += weight * 0.5
                        breakdown[q] = {'match': 'partial', 'weight': weight, 'score': weight * 0.5}
                    else:
                        breakdown[q] = {'match': False, 'weight': weight, 'score': 0}
                else:
                    breakdown[q] = {'match': False, 'weight': weight, 'score': 0}
            else:
                breakdown[q] = {'match': False, 'weight': weight, 'score': 0}
        
        # Calculate percentage
        score_percentage = int((weighted_matches / total_weight) * 100) if total_weight > 0 else 0
        
        return {
            'score': score_percentage,
            'breakdown': breakdown
        }
    
    @staticmethod
    def calculate_custom_score(user1: User, user2: User) -> dict:
        """
        Calculate score from custom questions
        Both users must have custom questions and answers
        """
        # Get custom questions
        q1 = user1.custom_questions
        q2 = user2.custom_questions
        
        if not q1 or not q2:
            return {'score': 0, 'breakdown': {}}
        
        try:
            questions1 = json.loads(q1) if isinstance(q1, str) else q1
            questions2 = json.loads(q2) if isinstance(q2, str) else q2
        except:
            return {'score': 0, 'breakdown': {}}
        
        if not questions1 or not questions2:
            return {'score': 0, 'breakdown': {}}
        
        # Calculate match based on shared questions
        total = 0
        matched = 0
        
        # Simple: count how many questions are similar in length/meaning
        for i in range(min(len(questions1), len(questions2))):
            total += 1
            q1_text = questions1[i].lower().strip() if isinstance(questions1[i], str) else str(questions1[i]).lower().strip()
            q2_text = questions2[i].lower().strip() if isinstance(questions2[i], str) else str(questions2[i]).lower().strip()
            
            # Simple similarity check (word overlap)
            words1 = set(q1_text.split())
            words2 = set(q2_text.split())
            overlap = len(words1.intersection(words2))
            if overlap > 0:
                matched += 1
        
        score = int((matched / total) * 100) if total > 0 else 0
        
        return {
            'score': score,
            'breakdown': {'matched': matched, 'total': total}
        }
    
    # ============================================================
    # FILTERS
    # ============================================================
    
    @staticmethod
    def apply_filters(db: Session, user: User, query) -> any:
        """
        Apply all filters to a query
        Filters: gender, religion, life status, age, distance
        """
        # 🆕 GENDER FILTER
        if user.looking_for_gender == "men":
            query = query.filter(User.gender == "male")
        elif user.looking_for_gender == "women":
            query = query.filter(User.gender == "female")
        # If "everyone", no filter needed
        
        # Religion filter
        if user.religion_preferences:
            preferred_religions = user.religion_preferences.split(',')
            query = query.filter(User.religion.in_(preferred_religions))
        elif user.religion:
            query = query.filter(User.religion == user.religion)
        
        # Life status filters
        if not user.open_to_single_parent:
            query = query.filter(User.is_single_parent == False)
        if not user.open_to_divorced:
            query = query.filter(User.is_divorced == False)
        
        # Age range filter
        if user.looking_for_age_min:
            from datetime import datetime
            today = datetime.now()
            min_date = datetime(today.year - user.looking_for_age_max, 1, 1) if user.looking_for_age_max else None
            max_date = datetime(today.year - user.looking_for_age_min, 12, 31) if user.looking_for_age_min else None
            
            if min_date:
                query = query.filter(User.date_of_birth >= min_date)
            if max_date:
                query = query.filter(User.date_of_birth <= max_date)
        
        # Distance filter (if latitude/longitude available)
        if user.latitude and user.longitude:
            # This is a simplified distance filter
            # In production, use PostGIS or calculate with haversine
            # For now, we'll skip distance filtering
            pass
        
        return query
    
    # ============================================================
    # GET MATCHES
    # ============================================================
    
    @staticmethod
    def get_matches(db: Session, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all matches for a serious user (50%+ compatibility with filters)"""
        print(f"🔍 ========== GET_MATCHES START ==========")
        
        # Get current user
        user = db.query(User).filter(User.id == user_id).first()
        print(f"🔍 Current user: {user.email if user else 'None'}")
        
        if not user:
            return []
        
        # Only for serious users
        if user.looking_for != "Serious Relationship":
            print(f"🔍 User is not serious: {user.looking_for}")
            return []
        
        print(f"🔍 User looking_for: {user.looking_for}")
        print(f"🔍 User looking_for_gender: {user.looking_for_gender}")
        print(f"🔍 User religion: {user.religion}")
        print(f"🔍 User religion_preferences: {user.religion_preferences}")
        print(f"🔍 User open_to_single_parent: {user.open_to_single_parent}")
        print(f"🔍 User open_to_divorced: {user.open_to_divorced}")
        print(f"🔍 User looking_for_age_min: {user.looking_for_age_min}")
        print(f"🔍 User looking_for_age_max: {user.looking_for_age_max}")
        
        # Get all other serious users
        query = db.query(User).filter(
            User.id != user_id,
            User.is_active == True,
            User.subscription_status != "expired",
            User.looking_for == "Serious Relationship"
        )
        
        print(f"🔍 Before filters: {query.count()} users found")
        
        # ✅ APPLY FILTERS (gender, religion, life status, age)
        query = SwipeService.apply_filters(db, user, query)
        
        other_users = query.all()
        print(f"🔍 After filters: {len(other_users)} users found")
        
        # Calculate compatibility for each
        scored_candidates = []
        for candidate in other_users:
            print(f"🔍 Checking candidate: {candidate.email}")
            
            # Skip if candidate has no answers
            answers = candidate.get_compatibility_answers()
            print(f"   Answers: {answers}")
            if not any(answers.values()):
                print(f"   ❌ No answers for {candidate.email}")
                continue
            
            result = SwipeService.calculate_compatibility(user, candidate)
            score = result['score']
            print(f"   📊 Compatibility score: {score}")
            
            # Only include 50%+ matches
            if score >= 50:
                print(f"   ✅ {candidate.email} is a match! ({score}%)")
                scored_candidates.append({
                    'user': candidate,
                    'score': score,
                    'score_8q': result['score_8q'],
                    'score_custom': result['score_custom'],
                    'breakdown': result['breakdown']
                })
            else:
                print(f"   ❌ {candidate.email} score too low: {score}")
        
        print(f"🔍 Total matches found: {len(scored_candidates)}")
        print(f"🔍 ========== GET_MATCHES END ==========")
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Build result with photos and scores
        result = []
        for item in scored_candidates[:limit]:
            candidate = item['user']
            score = item['score']
            score_8q = item['score_8q']
            score_custom = item['score_custom']
            
            # Get candidate's photos
            photos = db.query(Photo).filter(
                Photo.user_id == candidate.id
            ).order_by(Photo.order.asc()).all()
            
            photo_urls = []
            for photo in photos:
                photo_urls.append(photo.url_thumbnail)
            
            # Get candidate's profile
            candidate_profile = db.query(Profile).filter(Profile.user_id == candidate.id).first()
            
            result.append({
                "id": str(candidate.id),
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "age": candidate.age,
                "gender": candidate.gender,
                "bio": candidate_profile.bio if candidate_profile else None,
                "headline": candidate_profile.headline if candidate_profile else None,
                "interests": candidate_profile.interests.split(",") if candidate_profile and candidate_profile.interests else [],
                "is_online": candidate.is_online,
                "distance": None,
                "photos": photo_urls,
                "compatibility_score": score,
                "score_8q": score_8q,
                "score_custom": score_custom,
                "custom_questions": json.loads(candidate.custom_questions) if candidate.custom_questions else [],
                "photos_revealed": user.photos_revealed,
                "photo_reveal_date": user.photo_reveal_date.isoformat() if user.photo_reveal_date else None
            })
        
        return result
    
    @staticmethod
    def get_candidates(db: Session, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get candidates based on user type"""
        # Get current user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # ============================================================
        # SERIOUS RELATIONSHIP: Show only 50%+ matches
        # ============================================================
        if user.looking_for == "Serious Relationship":
            return SwipeService.get_matches(db, user_id, limit)
        
        # ============================================================
        # CASUAL USERS: Show all active casual users
        # ============================================================
        else:
            looking_for_gender = user.looking_for_gender
            
            # Get users who have blocked the current user
            from app.services.report_service import ReportService
            blocked_by_ids = ReportService.get_users_who_blocked(db, user_id)
            blocked_ids = ReportService.get_blocked_users(db, user_id)
            
            query = db.query(User).filter(
                User.id != user_id,
                User.is_active == True,
                User.subscription_status != "expired",
                User.looking_for == "Intimate Connection",
                ~User.id.in_(blocked_by_ids) if blocked_by_ids else True,
                ~User.id.in_(blocked_ids) if blocked_ids else True,
            )
            
            # Filter by gender preference
            if looking_for_gender == "men":
                query = query.filter(User.gender == "male")
            elif looking_for_gender == "women":
                query = query.filter(User.gender == "female")
            
            candidates = query.all()
            
            # Build result
            result = []
            for candidate in candidates[:limit]:
                photos = db.query(Photo).filter(
                    Photo.user_id == candidate.id
                ).order_by(Photo.order.asc()).all()
                photo_urls = [photo.url_thumbnail for photo in photos]
                
                candidate_profile = db.query(Profile).filter(Profile.user_id == candidate.id).first()
                
                result.append({
                    "id": str(candidate.id),
                    "first_name": candidate.first_name,
                    "last_name": candidate.last_name,
                    "age": candidate.age,
                    "gender": candidate.gender,
                    "bio": candidate_profile.bio if candidate_profile else None,
                    "headline": candidate_profile.headline if candidate_profile else None,
                    "interests": candidate_profile.interests.split(",") if candidate_profile and candidate_profile.interests else [],
                    "is_online": candidate.is_online,
                    "distance": None,
                    "photos": photo_urls
                })
            
            return result
    
    # ============================================================
    # SWIPE
    # ============================================================
    
    @staticmethod
    def create_swipe(db: Session, swiper_id: str, swiped_id: str, direction: str) -> Dict[str, Any]:
        """Create a swipe and check for match"""
        print(f"🔍 create_swipe called with: swiper_id={swiper_id}, swiped_id={swiped_id}, direction={direction}")
        
        if swiper_id == swiped_id:
            print("❌ Cannot swipe on yourself")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot swipe on yourself"
            )
        
        # Validate users
        swiper = db.query(User).filter(User.id == swiper_id).first()
        swiped = db.query(User).filter(User.id == swiped_id).first()
        print(f"✅ swiper found: {swiper is not None}, swiped found: {swiped is not None}")
        
        if not swiper or not swiped:
            print("❌ User not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if swiper can swipe (rate limiting)
        can_swipe = SwipeService.can_swipe(db, swiper_id)
        print(f"✅ can_swipe: {can_swipe}")
        
        if not can_swipe:
            print("❌ Daily swipe limit reached")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily swipe limit reached. Upgrade to premium for unlimited swipes."
            )
        
        # Check if blocked
        from app.services.report_service import ReportService
        is_blocked = ReportService.is_blocked(db, swiped_id, swiper_id)
        print(f"✅ is_blocked: {is_blocked}")
        
        if is_blocked:
            print("❌ User blocked")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot swipe on this user"
            )
        
        # Create swipe
        swipe = Swipe(
            id=str(uuid.uuid4()),
            swiper_id=swiper_id,
            swiped_id=swiped_id,
            direction=direction
        )
        db.add(swipe)
        db.flush()
        print(f"✅ Swipe created: {swipe.id}")
        
        result = {
            "swipe_id": str(swipe.id),
            "direction": direction,
            "is_match": False,
            "match": None
        }
        
        # If it's a like, check if the other person already liked back
        if direction == "like":
            mutual_swipe = db.query(Swipe).filter(
                Swipe.swiper_id == swiped_id,
                Swipe.swiped_id == swiper_id,
                Swipe.direction == "like"
            ).first()
            print(f"✅ mutual_swipe: {mutual_swipe is not None}")
            
            if mutual_swipe:
                # It's a match!
                match = Match(
                    id=str(uuid.uuid4()),
                    user_1_id=swiper_id,
                    user_2_id=swiped_id,
                    user_1_swiped_at=swipe.created_at,
                    user_2_swiped_at=mutual_swipe.created_at,
                    status=MatchStatus.MATCHED
                )
                db.add(match)
                db.flush()
                
                # Update swipe statuses
                swipe.status = "matched"
                mutual_swipe.status = "matched"
                
                db.commit()
                db.refresh(match)
                
                result["is_match"] = True
                result["match"] = {
                    "match_id": str(match.id),
                    "matched_at": match.matched_at.isoformat()
                }
                print(f"✅ Match created: {match.id}")
        
        db.commit()
        db.refresh(swipe)
        print(f"✅ Swipe complete: {swipe.id}")
        
        return result
    
    @staticmethod
    def get_swipe_history(db: Session, user_id: str, limit: int = 50) -> list:
        """Get swipe history for a user"""
        swipes = db.query(Swipe).filter(
            Swipe.swiper_id == user_id
        ).order_by(Swipe.created_at.desc()).limit(limit).all()
        
        result = []
        for swipe in swipes:
            swiped_user = db.query(User).filter(User.id == swipe.swiped_id).first()
            result.append({
                "swipe_id": str(swipe.id),
                "direction": swipe.direction,
                "status": swipe.status,
                "swiped_user": {
                    "id": str(swiped_user.id) if swiped_user else None,
                    "name": f"{swiped_user.first_name} {swiped_user.last_name}" if swiped_user else None
                } if swiped_user else None,
                "created_at": swipe.created_at.isoformat()
            })
        
        return result

    # ============================================================
    # CASUAL MATCHING
    # ============================================================
    
    @staticmethod
    def get_casual_matches(db: Session, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get casual matches for a user based on vibe, city, and sub-categories"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.looking_for != "Casual Dating":
            return []
    
        candidates = db.query(User).filter(
            User.id != user_id,
            User.is_active == True,
            User.looking_for == "Casual Dating",
            User.city == user.city,
            User.vibe == user.vibe,
        ).all()
    
        scored = []
        for candidate in candidates:
            if candidate.age < user.looking_for_age_min or candidate.age > user.looking_for_age_max:
                continue
            if user.looking_for_gender == "men" and candidate.gender != "male":
                continue
            if user.looking_for_gender == "women" and candidate.gender != "female":
                continue
        
            subA = set(user.vibe_subcategories or [])
            subB = set(candidate.vibe_subcategories or [])
            common = subA.intersection(subB)
            max_subs = max(len(subA), len(subB), 1)
            sub_score = (len(common) / max_subs) * 50
        
            middle_age = (user.looking_for_age_min + user.looking_for_age_max) / 2
            age_score = max(10 - abs(candidate.age - middle_age), 0)
        
            total_score = sub_score + age_score
        
            # Get candidate's photos
            photos = db.query(Photo).filter(
                Photo.user_id == candidate.id
            ).order_by(Photo.order.asc()).all()
        
            photo_urls = []
            for photo in photos:
                photo_urls.append(photo.url_thumbnail)
        
            # Get candidate's profile
            candidate_profile = db.query(Profile).filter(Profile.user_id == candidate.id).first()
        
            scored.append({
                "id": str(candidate.id),
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "age": candidate.age,
                "gender": candidate.gender,
                "bio": candidate_profile.bio if candidate_profile else None,
                "headline": candidate_profile.headline if candidate_profile else None,
                "interests": candidate_profile.interests.split(",") if candidate_profile and candidate_profile.interests else [],
                "is_online": candidate.is_online,
                "distance": None,
                "photos": photo_urls,
                "vibe": candidate.vibe,
                "vibe_subcategories": candidate.vibe_subcategories.split(",") if candidate.vibe_subcategories else [],
                "city": candidate.city,
                "compatibility_score": round(total_score),
            })
    
        scored.sort(key=lambda x: x['compatibility_score'], reverse=True)
        return scored[:limit]