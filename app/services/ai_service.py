import json
import re
from typing import List, Dict, Any

# ✅ New SDK (openai>=1.0.0)
from openai import OpenAI

from app.config import settings

# ✅ Create a single reusable client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# ✅ Debug
print("🔴🔴🔴 AI_SERVICE MODULE LOADED!")
print(f"🔴 OpenAI API Key: {settings.OPENAI_API_KEY[:10]}...")
print(f"🔴 OpenAI Model: {settings.OPENAI_MODEL}")


class AIService:

    @staticmethod
    def generate_compatibility_questions(user_profile: Dict, partner_profile: Dict, language: str = "en") -> List[Dict]:
        lang_name = "Amharic" if language == "am" else "English"
        print("🔴🔴🔴 generate_compatibility_questions CALLED!")

        prompt = f"""
        You are a relationship compatibility expert using the combined Gottman Method, 
        Attachment Theory, and Big Five personality framework.
        
        User 1 Profile:
        - Looking for: {user_profile.get('looking_for', 'Serious Relationship')}
        - Age: {user_profile.get('age', 'Unknown')}
        
        User 2 Profile:
        - Looking for: {partner_profile.get('looking_for', 'Serious Relationship')}
        - Age: {partner_profile.get('age', 'Unknown')}
        
        Generate 5 deep, psychological questions to assess their compatibility.
        Write ALL question text and ALL multiple-choice options in {lang_name}.
        Include questions from all 3 frameworks:
        
        1. GOTTMAN METHOD (2 questions): Conflict resolution, communication, trust
        2. ATTACHMENT THEORY (2 questions): Emotional needs, security, intimacy
        3. BIG FIVE (1 questions): Personality alignment, values, lifestyle
        
        For EACH question:
        1. Make the question deep and thought-provoking
        2. Provide EXACTLY 4 multiple choice options (A, B, C, D)
        3. Make the options challenging - NO obvious right answers. All options should be valid perspectives that real people hold.
        4. The options should reveal different personality traits, attachment styles, or communication patterns
        5. Avoid options that are clearly "good" or "bad" - make all options equally valid but different
        
        The framework/method it belongs to.
        
        Return ONLY a JSON array with this format:
        [
            {{
                "question": "When your partner expresses a need that conflicts with your own, what do you typically do?",
                "options": [
                    "I prioritize my partner's need and sacrifice my own",
                    "I express my need and work toward a compromise",
                    "I withdraw and hope the conflict resolves itself",
                    "I assert my need and expect my partner to accommodate"
                ],
                "method": "Gottman Method"
            }},
            ...
        ]
        """

        try:
            print("🔴 About to call OpenAI API...")
            print(f"🔴 Prompt (first 200 chars): {prompt[:200]}...")

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a relationship compatibility expert. Generate questions with 4 challenging, equal-validity multiple choice options. No obvious right answers. Make all options equally valid but different."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=1500
            )

            print("🔴 OpenAI response received!")

            questions_text = response.choices[0].message.content.strip()
            print(f"🔴 Response text (first 200 chars): {questions_text[:200]}...")

            json_match = re.search(r'\[.*\]', questions_text, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                print(f"🔴 Extracted {len(questions)} questions from JSON")
                return questions
            else:
                questions = json.loads(questions_text)
                print(f"🔴 Extracted {len(questions)} questions from response")
                return questions

        except Exception as e:
            print(f"❌ Error generating questions: {e}")
            import traceback
            traceback.print_exc()
            print("🔴 Using fallback questions...")
            return [
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
            ]

    @staticmethod
    def analyze_compatibility(user_responses: List[str], partner_responses: List[str], language: str = "en") -> Dict[str, Any]:
        print("🔴🔴🔴 analyze_compatibility CALLED!")

        lang_name = "Amharic" if language == "am" else "English"

        prompt = f"""
        You are a relationship compatibility expert using the combined Gottman Method,
        Attachment Theory, and Big Five personality framework.

        Partner 1's answers to 5 compatibility questions:
        {json.dumps(user_responses, indent=2)}

        Partner 2's answers to the same 5 compatibility questions:
        {json.dumps(partner_responses, indent=2)}

        Analyze the compatibility between these two people.
        Write the entire report in {lang_name}.
        Provide a comprehensive analysis with the following:

        1. OVERALL COMPATIBILITY SCORE (0-100%): Calculate based on alignment of values, communication style, emotional needs, and goals.

        2. STRENGTHS (3-4 key areas where they are highly compatible): Highlight specific areas of alignment with examples from their answers.

        3. CHALLENGES (3-4 key areas where they differ): Identify potential conflict areas with specific examples from their answers.

        4. KEY INSIGHTS: Personality insights about each person based on their answers.

        5. RECOMMENDATIONS: Practical advice for building a strong relationship based on their compatibility profile.

        Return ONLY a JSON object with the following structure:
        {{
            "score": 75,
            "strengths": ["text1", "text2", "text3"],
            "challenges": ["text1", "text2", "text3"],
            "insights": {{
                "person1": "text",
                "person2": "text"
            }},
            "recommendations": "text"
        }}
        """

        try:
            print("🔴 About to call OpenAI for analysis...")

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": f"You are a relationship compatibility expert. Analyze answers and provide a detailed compatibility report in {lang_name}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            print("🔴 OpenAI analysis response received!")

            report_text = response.choices[0].message.content.strip()

            json_match = re.search(r'\{.*\}', report_text, re.DOTALL)
            if json_match:
                report = json.loads(json_match.group())
                print(f"🔴 Report extracted successfully: score={report.get('score', 'N/A')}")
                return report
            else:
                report = json.loads(report_text)
                print(f"🔴 Report extracted successfully: score={report.get('score', 'N/A')}")
                return report

        except Exception as e:
            print(f"❌ Error analyzing compatibility: {e}")
            import traceback
            traceback.print_exc()
            return {
                "score": 50,
                "strengths": ["Both are willing to explore their compatibility!"],
                "challenges": ["Need more data for a complete analysis."],
                "insights": {
                    "person1": "Open to exploring relationships.",
                    "person2": "Open to exploring relationships."
                },
                "recommendations": "Communicate openly and honestly with each other. Take time to understand each other's perspectives."
            }

    @staticmethod
    def extract_personality_traits(responses: List[str]) -> Dict[str, Any]:
        prompt = f"""
        Based on these responses, extract the user's personality traits:
        {json.dumps(responses, indent=2)}
        
        Return a JSON object with:
        - attachment_style: "secure", "anxious", "avoidant", or "disorganized"
        - communication_style: "assertive", "passive", "aggressive", or "passive-aggressive"
        - conflict_resolution: "collaborative", "competitive", "avoidant", or "accommodating"
        - emotional_intelligence: "high", "medium", or "low"
        - core_values: array of 3-5 values
        """

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Analyze the responses and extract personality traits."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )

            traits_text = response.choices[0].message.content.strip()

            json_match = re.search(r'\{.*\}', traits_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(traits_text)
        except:
            return {
                "attachment_style": "secure",
                "communication_style": "assertive",
                "conflict_resolution": "collaborative",
                "emotional_intelligence": "medium",
                "core_values": ["Honesty", "Trust", "Communication"]
            }