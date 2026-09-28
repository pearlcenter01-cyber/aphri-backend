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
        
        Return ONLY a JSON array with 5 objects. Each object must have this shape:
[
    {{
        "question": "<unique psychological question>",
        "options": ["<option A>", "<option B>", "<option C>", "<option D>"],
        "method": "<Gottman Method | Attachment Theory | Big Five>"
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
    def analyze_compatibility(
        user_responses: List[str],
        partner_responses: List[str],
        person1_name: str = "You",
        person2_name: str = "Your partner",
        language: str = "en",
    ) -> Dict[str, Any]:
        print("🔴🔴🔴 analyze_compatibility CALLED!")

        lang_name = "Amharic" if language == "am" else "English"

        prompt = f"""
        You are a warm, wise friend giving relationship advice — not a therapist, not a clinical psychologist.
        You speak plainly, kindly, and specifically. You never use jargon. You never say "communication is key."
        You sound like someone who knows them both and wants them to succeed.

        The two people are {person1_name} and {person2_name}.

        {person1_name}'s answers to 5 compatibility questions:
        {json.dumps(user_responses, indent=2)}

        {person2_name}'s answers to the same 5 questions:
        {json.dumps(partner_responses, indent=2)}

        Write the entire report in {lang_name}.

        Use their real names — {person1_name} and {person2_name} — everywhere.
        Never say "Partner 1", "Partner 2", "person1", or "person2" in the prose.
        Speak directly to them.

        Write a personalized report in the exact JSON structure below. Every sentence should sound
        like it came from a real person who read their answers carefully, not from a formula.

        Structure:
        {{
            "score": <integer 0-100, your honest overall compatibility estimate>,
            "opening": "<2-3 sentences. Acknowledge what the two of them seem to be building. Warm, specific, no fluff.>",
            "what_works": [
                "<1 sentence each. Concrete things you noticed in their answers that are already strengths between them.>",
                "<1 sentence each.>",
                "<1 sentence each.>"
            ],
            "what_to_watch": [
                "<1 sentence each. Friction points, said gently. Not 'you're wrong' — more like 'this is where you two might rub.'>",
                "<1 sentence each.>",
                "<1 sentence each.>"
            ],
            "for_you": {{
                "person1": {{
                    "do": [
                        "<specific action, 1 sentence, written directly to {person1_name}>",
                        "<specific action>",
                        "<specific action>"
                    ],
                    "dont": [
                        "<specific thing to avoid, 1 sentence, written directly to {person1_name}>",
                        "<specific thing to avoid>",
                        "<specific thing to avoid>"
                    ]
                }},
                "person2": {{
                    "do": [
                        "<specific action, 1 sentence, written directly to {person2_name}>",
                        "<specific action>",
                        "<specific action>"
                    ],
                    "dont": [
                        "<specific thing to avoid, 1 sentence, written directly to {person2_name}>",
                        "<specific thing to avoid>",
                        "<specific thing to avoid>"
                    ]
                }}
            }},
            "closing": "<2-3 sentences. Encouraging, grounded, personal. End with warmth, not a summary.>"
        }}

        Rules:
        - Write the 'for_you' sections directly to each person, using 'you' and their name.
        - In opening, what_works, what_to_watch, and closing, write to the couple by name ("{person1_name} and {person2_name}", "the two of you").
        - Be specific. 'Take time to listen' is bad. 'Next time you disagree about plans, try saying "tell me more" before you explain your side' is good.
        - Do not repeat the same idea in different sections.
        - Do not mention "question 3" or "their answers to question 5". Refer to behavior, not to the test.
        - Roughly 400-500 words total.
        - If the score is below 50, be honest but kind. Don't pretend it's a great match if it isn't.
        - If the score is above 80, don't oversell it — real relationships still take work.
        """

        try:
            print("🔴 About to call OpenAI for analysis...")

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": f"You are a warm, wise friend giving relationship advice in {lang_name}. Speak plainly. Use the two people's real names — never 'Partner 1' or 'Partner 2'. Follow the JSON structure exactly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )

            print("🔴 OpenAI analysis response received!")

            report_text = response.choices[0].message.content.strip()

            json_match = re.search(r'\{.*\}', report_text, re.DOTALL)
            if json_match:
                report = json.loads(json_match.group())
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
                "opening": f"{person1_name} and {person2_name}, you both showed up honestly for this. That alone says something.",
                "what_works": ["You're both willing to look at this together."],
                "what_to_watch": ["There's not enough here yet for a full picture."],
                "for_you": {
                    "person1": {"do": ["Keep showing up like this."], "dont": ["Don't rush the process."]},
                    "person2": {"do": ["Keep showing up like this."], "dont": ["Don't rush the process."]},
                },
                "closing": "Talk to each other. That's where it starts.",
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