from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
import json

from app.models.user import User
from app.models.match_question_game import MatchQuestionGame
from app.models.real_match import RealMatch
from app.models.chat_question import ChatQuestion
from app.models.match import Match
from app.services.swipe_service import SwipeService


class QuestionGameService:
    """Service for the 3-question game algorithm"""
    
    @staticmethod
    def start_or_get_game(user_id: str, db: Session) -> Dict[str, Any]:
        """Start the game or get current state"""
        
        # Check if user already has 20 real matches
        real_matches_count = db.query(RealMatch).filter(
            RealMatch.user_id == user_id
        ).count()
        
        if real_matches_count >= 20:
            return {
                'status': 'complete',
                'message': '🎉 You have 20 real matches!',
                'real_matches_count': real_matches_count
            }
        
        # Get current game in progress
        current_game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == user_id,
            MatchQuestionGame.is_complete == False
        ).first()
        
        if current_game:
            # Game in progress - return current state
            return QuestionGameService._get_game_state(current_game, db)
        
        # No game in progress - start new one
        return QuestionGameService._start_new_game(user_id, db)
    
    @staticmethod
    def _start_new_game(user_id: str, db: Session) -> Dict[str, Any]:
        """Start a new game with next candidate"""
        
        # Get top 20 candidates (50%+ compatibility from 8 questions)
        candidates = SwipeService.get_matches(db, user_id, 20)
        
        if not candidates:
            return {
                'status': 'no_candidates',
                'message': 'No more candidates available'
            }
        
        # ✅ Get users who already played (completed games) - CANNOT play again
        completed_games = db.query(MatchQuestionGame.candidate_id).filter(
            MatchQuestionGame.user_id == user_id,
            MatchQuestionGame.is_complete == True
        ).all()
        completed_ids = [c[0] for c in completed_games]
        
        # ✅ Get real matches - CANNOT play again
        real_matches = db.query(RealMatch.matched_user_id).filter(
            RealMatch.user_id == user_id
        ).all()
        matched_ids = [r[0] for r in real_matches]
        
        # Find next candidate
        for candidate in candidates:
            candidate_id = candidate['id']
            
            # ✅ Skip if already played OR already a real match
            if candidate_id in completed_ids or candidate_id in matched_ids:
                continue
                
            # Get their custom questions
            other_user = db.query(User).filter(User.id == candidate_id).first()
            if not other_user:
                continue
            
            if not other_user.custom_questions:
                continue
            
            try:
                questions = json.loads(other_user.custom_questions)
                if len(questions) < 3:
                    continue
            except:
                continue
            
            # Create game entry
            game = MatchQuestionGame(
                id=str(uuid4()).replace('-', ''),
                user_id=user_id,
                candidate_id=candidate_id,
                question_index=0,
                custom_question=questions[0],
                is_complete=False
            )
            db.add(game)
            db.commit()
            
            
            # Create chat question record — the CANDIDATE is the asker
            chat_question = ChatQuestion(
                id=str(uuid4()).replace('-', ''),
                match_id=None,
                user_id=candidate_id,       # ← the other person asks
                candidate_id=user_id,       # ← I receive
                question_index=0,
                question_text=questions[0],
                is_answered=False
            )
            db.add(chat_question)
            db.commit()
            
            # Get real matches count for response
            real_matches_count = db.query(RealMatch).filter(
                RealMatch.user_id == user_id
            ).count()
            
            return {
                'status': 'in_progress',
                'game_id': game.id,
                'candidate_id': candidate_id,
                'candidate_name': other_user.full_name,
                'compatibility_score': candidate.get('compatibility_score', 0),
                'question_index': 0,
                'question_text': questions[0],
                'total_questions': 3,
                'progress': 'Question 1 of 3',
                'real_matches_so_far': real_matches_count
            }
        
        return {
            'status': 'no_candidates',
            'message': 'No more candidates available'
        }
    
    @staticmethod
    def _get_game_state(game: MatchQuestionGame, db: Session) -> Dict[str, Any]:
        """Get current state of an in-progress game"""
        
        other_user = db.query(User).filter(User.id == game.candidate_id).first()
        if not other_user:
            return {'status': 'error', 'message': 'Candidate not found'}
        
        # Get all chat questions for this game
        chat_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == game.user_id,
            ChatQuestion.candidate_id == game.candidate_id
        ).order_by(ChatQuestion.question_index).all()
        
        answered = [q for q in chat_questions if q.is_answered]
        rated = [q for q in chat_questions if q.is_answered and q.rating]
        
        current_index = len(answered)
        rated_count = len(rated)
        
        real_matches_count = db.query(RealMatch).filter(
            RealMatch.user_id == game.user_id
        ).count()
        
        # Check if all 3 are answered AND rated
        if current_index >= 3 and rated_count >= 3:
            if game.is_complete:
                return {
                    'status': 'complete',
                    'final_score': game.final_score,
                    'is_match': game.final_score >= 65 if game.final_score else False,
                    'real_matches_count': real_matches_count
                }
            else:
                return QuestionGameService._calculate_final_score(game, db)
        
        # Get next question
        try:
            questions = json.loads(other_user.custom_questions)
            next_question = questions[current_index] if current_index < len(questions) else None
        except:
            next_question = None
        
        return {
            'status': 'in_progress',
            'game_id': game.id,
            'candidate_id': game.candidate_id,
            'candidate_name': other_user.full_name,
            'compatibility_score': 0,
            'question_index': current_index,
            'question_text': next_question,
            'total_questions': 3,
            'progress': f'Question {current_index + 1} of 3',
            'real_matches_so_far': real_matches_count,
            'waiting_for_rating': True  # ✅ Always true if answer is submitted
        }
    
    @staticmethod
    def submit_question_answer(
        user_id: str,
        candidate_id: str,
        answer_text: str,
        db: Session
    ) -> Dict[str, Any]:
        """Submit an answer to the current question"""
        
        # Get game
        game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == user_id,
            MatchQuestionGame.candidate_id == candidate_id,
            MatchQuestionGame.is_complete == False
        ).first()
        
        if not game:
            return {'error': 'No active game found'}
        
        # Get the current unanswered question
        chat_question = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_id,
            ChatQuestion.candidate_id == candidate_id,
            ChatQuestion.is_answered == False
        ).order_by(ChatQuestion.question_index).first()
        
        if not chat_question:
            return {'error': 'No active question to answer'}
        
        # Save the answer
        chat_question.answer_text = answer_text
        chat_question.is_answered = True
        chat_question.answered_at = datetime.utcnow()
        db.commit()
        
        # ✅ Always return need_rating immediately after each answer
        return {
            'status': 'need_rating',
            'message': 'Answer submitted! Rate it now.',
            'question_id': chat_question.id,
            'candidate_id': candidate_id,
            'question_index': chat_question.question_index,
            'total_questions': 3
        }
    
    @staticmethod
    def rate_single_answer(
        user_id: str,
        question_id: str,
        rating: int,
        db: Session
    ) -> Dict[str, Any]:
        """Rate a single answer and return next question"""
        
        chat_question = db.query(ChatQuestion).filter(
            ChatQuestion.id == question_id
        ).first()
        
        if not chat_question:
            return {'error': 'Question not found'}
        
        # Save rating
        chat_question.rating = rating
        chat_question.rated_at = datetime.utcnow()
        db.commit()
        
        # Get the game
        game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == user_id,
            MatchQuestionGame.candidate_id == chat_question.candidate_id,
            MatchQuestionGame.is_complete == False
        ).first()
        
        if not game:
            return {'error': 'No active game found'}
        
        # Check if all 3 questions are answered AND rated
        all_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_id,
            ChatQuestion.candidate_id == chat_question.candidate_id
        ).all()
        
        answered = [q for q in all_questions if q.is_answered]
        rated = [q for q in all_questions if q.is_answered and q.rating]
        
        # If all 3 are answered and rated, calculate final score
        if len(answered) >= 3 and len(rated) >= 3:
            return QuestionGameService._calculate_final_score(game, db)
        
        # Get next unanswered question
        next_question = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_id,
            ChatQuestion.candidate_id == chat_question.candidate_id,
            ChatQuestion.is_answered == False
        ).order_by(ChatQuestion.question_index).first()
        
        if next_question:
            return {
                'status': 'next_question',
                'question_id': next_question.id,
                'question_text': next_question.question_text,
                'question_index': next_question.question_index,
                'progress': f'Question {next_question.question_index + 1} of 3',
                'total_questions': 3
            }
        
        # If no next question, wait for answer
        return {
            'status': 'waiting_for_answer',
            'message': 'Waiting for other user to answer'
        }
    
    @staticmethod
    def rate_answers(
        user_id: str,
        candidate_id: str,
        ratings: List[int],
        db: Session
    ) -> Dict[str, Any]:
        """Rate all 3 answers and calculate final score (legacy)"""
        
        if len(ratings) != 3:
            return {'error': 'Must provide exactly 3 ratings (1-5)'}
        
        # Get game
        game = db.query(MatchQuestionGame).filter(
            MatchQuestionGame.user_id == user_id,
            MatchQuestionGame.candidate_id == candidate_id,
            MatchQuestionGame.is_complete == False
        ).first()
        
        if not game:
            return {'error': 'No active game found'}
        
        # Get all chat questions
        chat_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == user_id,
            ChatQuestion.candidate_id == candidate_id
        ).order_by(ChatQuestion.question_index).all()
        
        if len(chat_questions) < 3:
            return {'error': 'Not all questions answered yet'}
        
        # Save ratings
        for i, q in enumerate(chat_questions):
            q.rating = ratings[i]
            q.rated_at = datetime.utcnow()
        
        db.commit()
        
        # Calculate final score
        return QuestionGameService._calculate_final_score(game, db)
    
    @staticmethod
    def _calculate_final_score(game: MatchQuestionGame, db: Session) -> Dict[str, Any]:
        """Calculate final score and determine if real match"""
        
        user = db.query(User).filter(User.id == game.user_id).first()
        candidate = db.query(User).filter(User.id == game.candidate_id).first()
        
        if not user or not candidate:
            return {'error': 'User not found'}
        
        # Get 8-question score
        compatibility = SwipeService.calculate_compatibility(user, candidate)
        eight_q_score = compatibility['score']
        
        # Get all chat questions with ratings
        chat_questions = db.query(ChatQuestion).filter(
            ChatQuestion.user_id == game.user_id,
            ChatQuestion.candidate_id == game.candidate_id
        ).order_by(ChatQuestion.question_index).all()
        
        ratings = [q.rating for q in chat_questions if q.rating]
        
        if len(ratings) < 3:
            return {'error': 'Not all questions rated yet'}
        
        # Calculate custom score (1-5 -> 0-100)
        avg_rating = sum(ratings) / len(ratings)
        custom_score = (avg_rating / 5) * 100
        
        # Final score
        final_score = (eight_q_score + custom_score) / 2
        
        # Save
        game.is_complete = True
        game.final_score = final_score
        db.commit()
        
        real_matches_count = db.query(RealMatch).filter(
            RealMatch.user_id == game.user_id
        ).count()
        
        # Check if real match
        if final_score >= 65:
            # Create real match
            real_match = RealMatch(
                id=str(uuid4()).replace('-', ''),
                user_id=game.user_id,
                matched_user_id=game.candidate_id,
                final_score=final_score
            )
            db.add(real_match)
            
            # ✅ UNLOCK THE CHAT
            match = db.query(Match).filter(
                (Match.user_1_id == game.user_id) & (Match.user_2_id == game.candidate_id)
            ).first()
            if not match:
                match = db.query(Match).filter(
                    (Match.user_1_id == game.candidate_id) & (Match.user_2_id == game.user_id)
                ).first()
            if match:
                match.chat_unlocked_at = datetime.utcnow()
                print(f"🔓 Chat unlocked for match: {match.id}")
            
            db.commit()
            
            real_matches_count += 1
            
            return {
                'status': 'real_match',
                'final_score': final_score,
                'is_match': True,
                'real_matches_count': real_matches_count,
                'message': f'🎉 Match! You and {candidate.full_name} are now a real match!',
                'candidate_name': candidate.full_name
            }
        else:
            return {
                'status': 'not_match',
                'final_score': final_score,
                'is_match': False,
                'real_matches_count': real_matches_count,
                'message': f'Score: {int(final_score)}%. Not quite a match. Keep going!'
            }
    
    @staticmethod
    def get_real_matches(user_id: str, db: Session) -> Dict[str, Any]:
        """Get all real matches for a user"""
        
        real_matches = db.query(RealMatch).filter(
            RealMatch.user_id == user_id
        ).all()
        
        result = []
        for match in real_matches:
            other_user = db.query(User).filter(User.id == match.matched_user_id).first()
            if other_user:
                result.append({
                    'id': match.id,
                    'user_id': match.matched_user_id,
                    'name': other_user.full_name,
                    'email': other_user.email,
                    'score': match.final_score,
                    'created_at': match.created_at.isoformat()
                })
        
        return {
            'count': len(result),
            'matches': result,
            'is_complete': len(result) >= 20
        }