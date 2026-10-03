from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4
import json
from sqlalchemy import or_, and_
from app.database import get_db
from app.dependencies import get_current_user
from app.services.ai_service import AIService
from app.models.user import User
from app.models.compatibility import (
    CompatibilitySession, 
    CompatibilityQuestion, 
    CompatibilityResponse
)
from app.models.match import Match
from app.models.message import Message

print("🔴🔴🔴 COMPATIBILITY ROUTER MODULE LOADED!")

router = APIRouter(tags=["Compatibility"])  # ✅ Remove prefix here

def _ensure_invitation_message(db, sender, partner_id, session_id):
    """
    Ensure a compatibility_request Message exists between sender and partner
    for this session. Idempotent — safe to call on every request.
    """
    existing_msg = db.query(Message).filter(
        Message.session_id == session_id,
        Message.message_type == 'compatibility_request',
    ).first()
    if existing_msg:
        print(f"🔴 Invitation message already exists: {existing_msg.id}")
        return

    match = db.query(Match).filter(
        or_(
            and_(Match.user_1_id == sender.id, Match.user_2_id == partner_id),
            and_(Match.user_1_id == partner_id, Match.user_2_id == sender.id),
        )
    ).first()

    now = datetime.utcnow()
    if not match:
        match = Match(
            id=str(uuid4()),
            user_1_id=sender.id,
            user_2_id=partner_id,
            user_1_swiped_at=now,
            user_2_swiped_at=now,
            matched_at=now,
            chat_unlocked_at=now,
            is_active=True,
            initiator_id=sender.id,
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        print(f"🔴 Match row created for invitation: {match.id}")
    else:
        if not match.chat_unlocked_at:
            match.chat_unlocked_at = now
            db.commit()
        print(f"🔴 Using existing match: {match.id}")

    sender_name = (
        getattr(sender, 'first_name', None)
        or getattr(sender, 'full_name', None)
        or 'Someone'
    )

    invitation = Message(
        id=str(uuid4()).replace('-', ''),
        match_id=str(match.id),
        sender_id=sender.id,
        receiver_id=partner_id,
        content=f"{sender_name} wants to explore deep compatibility with you!",
        message_type='compatibility_request',
        session_id=session_id,
        is_read=False,
    )
    db.add(invitation)
    db.commit()
    print(f"🔴 Invitation message inserted: {invitation.id} session={session_id}")

@router.post("/request")
async def request_compatibility(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a guided compatibility request to a partner
    Body: { "partner_id": "..." }
    """
    print("🔴🔴🔴 request_compatibility CALLED")
    
    partner_id = request.get("partner_id")
    print(f"🔴 partner_id: {partner_id}")
    
    if not partner_id:
        raise HTTPException(status_code=400, detail="partner_id is required")
    
        # Check if ANY session exists between the two users, in either direction.
    # Only one compatibility session per pair is allowed.
    existing = db.query(CompatibilitySession).filter(
        or_(
            and_(
                CompatibilitySession.user_id == current_user.id,
                CompatibilitySession.partner_id == partner_id,
            ),
            and_(
                CompatibilitySession.user_id == partner_id,
                CompatibilitySession.partner_id == current_user.id,
            ),
        ),
        CompatibilitySession.status.in_(["pending", "both_agreed", "answering", "complete"])
    ).first()
    
    if existing:
        print(f"🔴 Session already exists: {existing.id}, status: {existing.status}")
        _ensure_invitation_message(db, current_user, partner_id, existing.id)
        return {
            "message": "Compatibility request already sent",
            "session_id": existing.id,
            "status": existing.status
        }
    
    # Create new session
    session = CompatibilitySession(
        id=str(uuid4()).replace('-', ''),
        user_id=current_user.id,
        partner_id=partner_id,
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    print(f"🔴 New session created: {session.id}")

    _ensure_invitation_message(db, current_user, partner_id, session.id)

    return {
        "message": "Compatibility request sent",
        "session_id": session.id,
        "status": session.status
    }

@router.post("/request/respond")
async def respond_compatibility(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Respond to a compatibility request
    Body: { "session_id": "...", "agree": true/false }
    """
    print("🔴🔴🔴 respond_compatibility CALLED")
    
    session_id = request.get("session_id")
    agree = request.get("agree", False)
    language = request.get("language") or "en"
    print(f"🔴 LANGUAGE FROM REQUEST: {language!r}")
    
    print(f"🔴 session_id: {session_id}")
    print(f"🔴 agree: {agree}")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    session = db.query(CompatibilitySession).filter(
        CompatibilitySession.id == session_id,
        or_(
            CompatibilitySession.user_id == current_user.id,
            CompatibilitySession.partner_id == current_user.id,
        )
    ).first()
    
    if not session:
        print(f"❌ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"🔴 Session found: {session.id}, status: {session.status}")

    if session.status != "pending":
        print(f"🔴 Session already responded, status: {session.status}")
        return {
            "message": "Request already handled",
            "session_id": session.id,
            "status": session.status,
        }
    
    if not agree:
        session.status = "declined"
        db.commit()
        print("🔴 Request declined")
        return {"message": "Request declined"}
    
    session.status = "both_agreed"
    session.agreed_at = datetime.utcnow()
    db.commit()
    
    print("🔴 Session status updated to both_agreed")


    # If questions already exist for this session, don't generate again
    existing_questions = db.query(CompatibilityQuestion).filter(
        CompatibilityQuestion.session_id == session.id
    ).order_by(CompatibilityQuestion.question_index).all()

    if existing_questions:
        print(f"🔴 Session already has {len(existing_questions)} questions, returning them")
        result = []
        for q in existing_questions:
            options = []
            if q.options:
                try:
                    options = json.loads(q.options)
                except:
                    options = []
            result.append({
                "id": q.id,
                "text": q.question_text,
                "options": options,
                "method": q.category or "General"
            })
        return {
            "message": "Request accepted",
            "session_id": session.id,
            "questions": result
        }





    
    # Get user profiles directly from database
    print("🔴 Fetching user profiles...")
    user = db.query(User).filter(User.id == session.user_id).first()
    partner = db.query(User).filter(User.id == session.partner_id).first()
    
    print(f"🔴 User: {user.email if user else 'None'}")
    print(f"🔴 Partner: {partner.email if partner else 'None'}")
    
    user_profile = {
        "looking_for": user.looking_for if user else "Serious Relationship",
        "age": user.age if user else None,
        "traits": "Unknown"
    }
    partner_profile = {
        "looking_for": partner.looking_for if partner else "Serious Relationship",
        "age": partner.age if partner else None,
        "traits": "Unknown"
    }
    
    print(f"🔴 user_profile: {user_profile}")
    print(f"🔴 partner_profile: {partner_profile}")
    
    # Generate questions with AI
    print("🔴🔴🔴 ABOUT TO CALL AIService.generate_compatibility_questions")
    
    try:
        questions = AIService.generate_compatibility_questions(
            user_profile,
            partner_profile,
            language=language,
            session_id=session.id,
        )
        print(f"🔴🔴🔴 QUESTIONS GENERATED SUCCESSFULLY: {len(questions)} questions")
        if questions:
            print(f"🔴 First question: {questions[0].get('question', 'None')[:50]}...")
    except Exception as e:
        print(f"❌❌❌ ERROR generating questions: {e}")
        import traceback
        traceback.print_exc()
   
        raise HTTPException(status_code=500, detail="Failed to load compatibility questions")

    # Hard cap: never store more than 5 questions
    questions = questions[:5]
    print(f"🔴 Final question count after cap: {len(questions)}")

    # ✅ FIX 1: wipe old responses before saving new questions
    db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session.id
    ).delete(synchronize_session=False)
    db.commit()

    # Save questions to database
    print("🔴 Saving questions to database...")
    for idx, q in enumerate(questions):
        db.add(CompatibilityQuestion(
            id=str(uuid4()).replace('-', ''),
            session_id=session.id,
            question_text=q.get('question', ''),
            question_text_am=q.get('question_am', ''),
            options=json.dumps(q.get('options', [])) if q.get('options') else None,
            options_am=json.dumps(q.get('options_am', [])) if q.get('options_am') else None,
            category=q.get('method', 'General'),
            question_index=idx,
        ))
        print(f"🔴 Saved question {idx+1}: {(q.get('question') or '')[:60]}")

    db.commit()
    print("🔴 All questions saved to database")
    
    # Return questions with options to the frontend
    return {
        "message": "Request accepted",
        "session_id": session.id,
        "questions": questions
    }

@router.get("/questions/{session_id}")
async def get_compatibility_questions(
    session_id: str,
    language: str = "en",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get compatibility questions for a session.
    Self-heals: if the session is both_agreed but no questions exist, generates them in English.
    """
    print(f"🔴 get_compatibility_questions CALLED for session: {session_id}")

    session = db.query(CompatibilitySession).filter(
        CompatibilitySession.id == session_id,
        (CompatibilitySession.user_id == current_user.id) |
        (CompatibilitySession.partner_id == current_user.id)
    ).first()

    if not session:
        print(f"❌ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    print(f"🔴 Session found: {session.id}, status: {session.status}")

    # ✅ If the session is already complete, don't regenerate — questions and report are final
    if session.status == "complete":
        print(f"🔴 Session complete — returning report")
        return {
            "session_id": session.id,
            "status": "complete",
            "report": session.report,
            "score": session.score,
            "questions": [],
            "my_answers": {},
        }

    questions = db.query(CompatibilityQuestion).filter(
        CompatibilityQuestion.session_id == session_id
    ).order_by(CompatibilityQuestion.question_index).all()

    # ✅ Self-heal: if both agreed but no questions, generate them now
    if not questions and session.status in ("both_agreed", "answering"):
        print("🔴 No questions found — generating in English...")

        # ✅ FIX 1 + FIX 2: wipe old responses and reset session state
        db.query(CompatibilityResponse).filter(
            CompatibilityResponse.session_id == session.id
        ).delete(synchronize_session=False)
        session.status = "both_agreed"
        session.report = None
        session.score = None
        session.completed_at = None
        db.commit()

        user = db.query(User).filter(User.id == session.user_id).first()
        partner = db.query(User).filter(User.id == session.partner_id).first()

        user_profile = {
            "looking_for": user.looking_for if user else "Serious Relationship",
            "age": user.age if user else None,
        }
        partner_profile = {
            "looking_for": partner.looking_for if partner else "Serious Relationship",
            "age": partner.age if partner else None,
        }

        try:
            generated = AIService.generate_compatibility_questions(
                user_profile,
                partner_profile,
                language=language,
                session_id=session.id,
            )[:5]
            print(f"🔴 Generated {len(generated)} questions")
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            generated = []

        for idx, q in enumerate(generated):
            db.add(CompatibilityQuestion(
                id=str(uuid4()).replace("-", ""),
                session_id=session.id,
                question_text=q.get("question", ""),
                question_text_am=q.get("question_am", ""),
                options=json.dumps(q.get("options", [])) if q.get("options") else None,
                options_am=json.dumps(q.get("options_am", [])) if q.get("options_am") else None,
                category=q.get("method", "General"),
                question_index=idx,
            ))

        db.commit()

        questions = db.query(CompatibilityQuestion).filter(
            CompatibilityQuestion.session_id == session_id
        ).order_by(CompatibilityQuestion.question_index).all()
        print(f"🔴 Saved {len(questions)} questions")

    print(f"🔴 Found {len(questions)} questions")

    use_am = (language == "am")

    result = []
    for q in questions:
        text = (q.question_text_am or q.question_text) if use_am else q.question_text
        options_raw = q.options_am if use_am else q.options

        options = []
        if options_raw:
            try:
                options = json.loads(options_raw)
            except:
                options = []
        if not options and q.options:
            try:
                options = json.loads(q.options)
            except:
                options = []

        result.append({
            "id": q.id,
            "text": text,
            "options": options,
            "method": q.category or "General"
        })

    my_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session.id,
        CompatibilityResponse.user_id == current_user.id,
    ).all()
    my_answers = {r.question_id: r.response_text for r in my_responses}

    return {
        "session_id": session.id,
        "questions": result,
        "my_answers": my_answers,
    }

@router.post("/answers")
async def submit_compatibility_answers(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit answers to compatibility questions
    Body: { "session_id": "...", "answers": [{"question_id": "...", "response": "..."}] }
    """
    print("🔴🔴🔴 submit_compatibility_answers CALLED")
    
    session_id = request.get("session_id")
    answers = request.get("answers", [])
    language = request.get("language") or "en"
    
    print(f"🔴 session_id: {session_id}")
    print(f"🔴 answers count: {len(answers)}")
    
    if not session_id or not answers:
        raise HTTPException(status_code=400, detail="session_id and answers are required")
    
    session = db.query(CompatibilitySession).filter(
        CompatibilitySession.id == session_id,
        (CompatibilitySession.user_id == current_user.id) | 
        (CompatibilitySession.partner_id == current_user.id)
    ).first()
    
    if not session:
        print(f"❌ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"🔴 Session found: {session.id}, status: {session.status}")

    # ✅ FIX 3a: idempotent — if already complete, return existing report
    if session.status == "complete":
        print("🔴 Session already complete — returning existing report")
        return {
            "message": "Already analyzed",
            "status": "complete",
            "report": session.report,
        }

    # ✅ Charge 10 credits per submit — only if this user hasn't already submitted
    existing_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session_id,
        CompatibilityResponse.user_id == current_user.id,
    ).count()

    if existing_responses == 0:
        from app.services.credit_service import CreditService
        CreditService.spend_credits(
            db,
            user_id=current_user.id,
            amount=10,
            action="compatibility_answers",
        )
        print(f"🔴 Charged 10 credits to user {current_user.id} for compatibility answers")

    # Save answers
    for answer in answers:


        question_id = answer.get("question_id")
        response_text = answer.get("response")
        
        if not question_id or not response_text:
            continue
            
        existing = db.query(CompatibilityResponse).filter(
            CompatibilityResponse.session_id == session_id,
            CompatibilityResponse.question_id == question_id,
            CompatibilityResponse.user_id == current_user.id
        ).first()
        
        if existing:
            existing.response_text = response_text
            print(f"🔴 Updated answer for question: {question_id}")
        else:
            new_response = CompatibilityResponse(
                id=str(uuid4()).replace('-', ''),
                session_id=session_id,
                question_id=question_id,
                user_id=current_user.id,
                response_text=response_text
            )
            db.add(new_response)
            print(f"🔴 Created new answer for question: {question_id}")
    
    db.commit()
    print("🔴 All answers saved")

    # ✅ FIX 3b: only count current questions and only the two real partners
    all_questions = db.query(CompatibilityQuestion).filter(
        CompatibilityQuestion.session_id == session_id
    ).all()
    valid_qids = [q.id for q in all_questions]

    user_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session_id,
        CompatibilityResponse.user_id == session.user_id,
        CompatibilityResponse.question_id.in_(valid_qids),
    ).all()

    partner_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session_id,
        CompatibilityResponse.user_id == session.partner_id,
        CompatibilityResponse.question_id.in_(valid_qids),
    ).all()

    print(f"🔴 Total questions: {len(all_questions)}")
    print(f"🔴 User answers: {len(user_responses)}")
    print(f"🔴 Partner answers: {len(partner_responses)}")

    if len(user_responses) == len(all_questions) and len(partner_responses) == len(all_questions):








        print("🔴 Both users have answered all questions - analyzing!")
        session.status = "analyzing"
        db.commit()
        
        # Get responses for analysis
        all_responses = db.query(CompatibilityResponse).filter(
            CompatibilityResponse.session_id == session_id
        ).order_by(CompatibilityResponse.question_id).all()
        
        user_answers = [r.response_text for r in all_responses if r.user_id == session.user_id]
        partner_answers = [r.response_text for r in all_responses if r.user_id == session.partner_id]
        
        print(f"🔴 User answers: {len(user_answers)}")
        print(f"🔴 Partner answers: {len(partner_answers)}")
        
        # Analyze with AI
        user_obj = db.query(User).filter(User.id == session.user_id).first()
        partner_obj = db.query(User).filter(User.id == session.partner_id).first()
        person1_name = user_obj.first_name if user_obj else "You"
        person2_name = partner_obj.first_name if partner_obj else "Your partner"

        # Build the questions list in the shape analyze_compatibility expects
        questions_for_report = [
            {
                "question": q.question_text,
                "method": q.category or "General",
            }
            for q in all_questions
        ]

        print("🔴 Calling AI for analysis...")
        report = AIService.analyze_compatibility(
            questions_for_report,
            user_answers,
            partner_answers,
            person1_name=person1_name,
            person2_name=person2_name,
            language=language,
        )



        print(f"🔴 Analysis complete! Score: {report.get('score', 'N/A')}")
        
        session.status = "complete"
        session.report = report
        session.score = report.get("score", 0)
        session.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": "Answers submitted and analyzed!",
            "status": "complete",
            "report": report
        }
    
    return {
        "message": "Answers saved",
        "status": "answering",
        "progress": {
            "your_answers": len(user_responses),
            "partner_answers": len(partner_responses),
            "total": len(all_questions)
        }
    }

@router.get("/report/{session_id}")
async def get_compatibility_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the compatibility report for a session
    """
    print(f"🔴 get_compatibility_report CALLED for session: {session_id}")
    
    session = db.query(CompatibilitySession).filter(
        CompatibilitySession.id == session_id,
        (CompatibilitySession.user_id == current_user.id) | 
        (CompatibilitySession.partner_id == current_user.id)
    ).first()
    
    if not session:
        print(f"❌ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"🔴 Session found: {session.id}, status: {session.status}")
    
    if session.status != "complete":
        print(f"🔴 Report not ready, status: {session.status}")
        return {
            "status": session.status,
            "message": "Report is not ready yet"
        }
    
    print("🔴 Report ready, returning...")
    return {
        "session_id": session.id,
        "score": session.score,
        "report": session.report,
        "completed_at": session.completed_at,
        "status": session.status
    }

@router.get("/sessions")
async def get_compatibility_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all compatibility sessions for the current user
    """
    print(f"🔴 get_compatibility_sessions CALLED for user: {current_user.id}")
    
    sessions = db.query(CompatibilitySession).filter(
        (CompatibilitySession.user_id == current_user.id) | 
        (CompatibilitySession.partner_id == current_user.id)
    ).all()
    
    print(f"🔴 Found {len(sessions)} sessions")
    
    result = []
    for session in sessions:
        other_id = session.partner_id if session.user_id == current_user.id else session.user_id
        other_user = db.query(User).filter(User.id == other_id).first()
        
        result.append({
            "id": session.id,
            "partner_id": other_id,
            "partner_name": f"{other_user.first_name} {other_user.last_name or ''}".strip(),
            "status": session.status,
            "score": session.score,
            "request_sent_at": session.request_sent_at,
            "completed_at": session.completed_at
        })
    
    return result

@router.get("/test")
async def test_compatibility():
    return {"status": "Compatibility router is working!"}    