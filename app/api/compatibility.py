from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4
import json

from app.database import get_db
from app.dependencies import get_current_user
from app.services.ai_service import AIService
from app.models.user import User
from app.models.compatibility import (
    CompatibilitySession, 
    CompatibilityQuestion, 
    CompatibilityResponse
)

print("🔴🔴🔴 COMPATIBILITY ROUTER MODULE LOADED!")

router = APIRouter(tags=["Compatibility"])  # ✅ Remove prefix here

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
    
    # Check if session already exists
    existing = db.query(CompatibilitySession).filter(
        CompatibilitySession.user_id == current_user.id,
        CompatibilitySession.partner_id == partner_id,
        CompatibilitySession.status.in_(["pending", "both_agreed", "answering"])
    ).first()
    
    if existing:
        print(f"🔴 Session already exists: {existing.id}, status: {existing.status}")
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
    
    print(f"🔴 session_id: {session_id}")
    print(f"🔴 agree: {agree}")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    session = db.query(CompatibilitySession).filter(
        CompatibilitySession.id == session_id,
        CompatibilitySession.partner_id == current_user.id
    ).first()
    
    if not session:
        print(f"❌ Session not found: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"🔴 Session found: {session.id}, status: {session.status}")
    
    if not agree:
        session.status = "declined"
        db.commit()
        print("🔴 Request declined")
        return {"message": "Request declined"}
    
    session.status = "both_agreed"
    session.agreed_at = datetime.utcnow()
    db.commit()
    
    print("🔴 Session status updated to both_agreed")
    
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
        questions = AIService.generate_compatibility_questions(user_profile, partner_profile)
        print(f"🔴🔴🔴 QUESTIONS GENERATED SUCCESSFULLY: {len(questions)} questions")
        if questions:
            print(f"🔴 First question: {questions[0].get('question', 'None')[:50]}...")
    except Exception as e:
        print(f"❌❌❌ ERROR generating questions: {e}")
        import traceback
        traceback.print_exc()
        # Fallback questions with options
        questions = [
            {
                "question": "When your partner expresses a need that conflicts with your own, what do you typically do?",
                "options": [
                    "I prioritize my partner's need and sacrifice my own",
                    "I express my need and work toward a compromise",
                    "I withdraw and hope the conflict resolves itself",
                    "I assert my need and expect my partner to accommodate"
                ],
                "method": "Gottman Method"
            },
            {
                "question": "What does commitment mean to you in a relationship?",
                "options": [
                    "Staying together through all challenges, regardless of personal cost",
                    "Choosing each other daily, with the freedom to leave",
                    "Building a life together while maintaining individual independence",
                    "A sacred bond that requires sacrifice and compromise"
                ],
                "method": "Gottman Method"
            },
            {
                "question": "How do you typically respond when you feel emotionally hurt by your partner?",
                "options": [
                    "I withdraw to process my feelings alone",
                    "I confront them immediately and express my hurt",
                    "I reflect on whether my reaction is justified before responding",
                    "I become distant and wait for them to notice"
                ],
                "method": "Gottman Method"
            },
            {
                "question": "What makes you feel most emotionally secure in a relationship?",
                "options": [
                    "Consistent reassurance and validation from my partner",
                    "Knowing we can be independent without losing connection",
                    "Feeling understood even when we disagree",
                    "Physical presence and affection on a regular basis"
                ],
                "method": "Attachment Theory"
            },
            {
                "question": "When you're stressed or anxious, what do you need most from a partner?",
                "options": [
                    "Space to process my emotions on my own",
                    "Active listening and emotional support",
                    "Practical help to solve the problem",
                    "Physical comfort and closeness"
                ],
                "method": "Attachment Theory"
            },
            {
                "question": "How do you express love most naturally?",
                "options": [
                    "Through words of affirmation and encouragement",
                    "Through acts of service and practical help",
                    "Through quality time and undivided attention",
                    "Through physical touch and intimacy"
                ],
                "method": "Attachment Theory"
            },
            {
                "question": "When you face a major life decision, how do you approach it?",
                "options": [
                    "I analyze all options carefully before deciding",
                    "I trust my intuition and go with my gut feeling",
                    "I seek input from trusted people before deciding",
                    "I take time to reflect and decide when I feel ready"
                ],
                "method": "Big Five"
            },
            {
                "question": "How important is personal growth to you in a relationship?",
                "options": [
                    "Essential - we should grow together and support each other",
                    "Important, but not at the expense of the relationship",
                    "Secondary - stability and comfort matter more",
                    "I believe growth is an individual journey, not a shared one"
                ],
                "method": "Big Five"
            },
            {
                "question": "How do you typically handle disagreements about finances or lifestyle?",
                "options": [
                    "I advocate for my perspective and seek compromise",
                    "I defer to my partner's judgment to avoid conflict",
                    "I suggest we seek professional advice or external input",
                    "I maintain my position and hope we can agree over time"
                ],
                "method": "Big Five"
            },
            {
                "question": "What role does physical intimacy play in your ideal relationship?",
                "options": [
                    "A central pillar - essential for emotional connection",
                    "Important, but emotional intimacy matters more",
                    "Secondary - it comes and goes with life circumstances",
                    "Desirable, but not necessary for a deep connection"
                ],
                "method": "Big Five"
            }
        ]
        print(f"🔴 Using fallback questions: {len(questions)} questions")
    
    # Save questions to database
    print("🔴 Saving questions to database...")
    for idx, q in enumerate(questions):
        # Extract question text and options
        question_text = q.get('question', '') if isinstance(q, dict) else q
        options = q.get('options', []) if isinstance(q, dict) else []
        method = q.get('method', 'General') if isinstance(q, dict) else 'General'
        
        # Store options as JSON string
        options_json = json.dumps(options) if options else None
        
        question = CompatibilityQuestion(
            id=str(uuid4()).replace('-', ''),
            session_id=session.id,
            question_text=question_text,
            options=options_json,  # Store options as JSON
            category=method,
            question_index=idx
        )
        db.add(question)
        
        print(f"🔴 Saved question {idx+1}: {question_text[:50]}... ({len(options)} options, {method})")
    
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get compatibility questions for a session
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
    
    questions = db.query(CompatibilityQuestion).filter(
        CompatibilityQuestion.session_id == session_id
    ).order_by(CompatibilityQuestion.question_index).all()
    
    print(f"🔴 Found {len(questions)} questions")
    
    # Return questions with options
    result = []
    for q in questions:
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
        "session_id": session.id,
        "questions": result
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
    
    print(f"🔴 Session found: {session.id}")
    
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
    
    # Check if both users have answered all questions
    all_questions = db.query(CompatibilityQuestion).filter(
        CompatibilityQuestion.session_id == session_id
    ).all()
    
    user_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session_id,
        CompatibilityResponse.user_id == current_user.id
    ).all()
    
    partner_responses = db.query(CompatibilityResponse).filter(
        CompatibilityResponse.session_id == session_id,
        CompatibilityResponse.user_id != current_user.id
    ).all()
    
    print(f"🔴 Total questions: {len(all_questions)}")
    print(f"🔴 Your answers: {len(user_responses)}")
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
        print("🔴 Calling AI for analysis...")
        report = AIService.analyze_compatibility(user_answers, partner_answers)
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