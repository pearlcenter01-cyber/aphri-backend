import json
import re
from typing import List, Dict, Any

from app.data.compatibility_questions import (
    COMPATIBILITY_QUESTION_SETS,
    get_compatibility_question_set,
)

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
    def generate_compatibility_questions(
        user_profile: Dict,
        partner_profile: Dict,
        language: str = "en",
        session_id: str = "",
    ) -> List[Dict]:
        """
        Load 5 compatibility questions from the local bank.
        Deterministic per session_id, so both partners get the same set.
        Returns the same shape as before: [{question, options, method}, ...]
        """
        print("🔴🔴🔴 generate_compatibility_questions CALLED (local bank)!")

        # Fall back to a stable seed if no session_id is passed
        seed = session_id or f"{user_profile.get('id')}-{partner_profile.get('id')}"
        chosen_set = get_compatibility_question_set(seed)

        use_am = (language == "am")

        questions = []
        for q in chosen_set["questions"]:
            questions.append({
                "question": q["text_am"] if use_am else q["text_en"],
                "options":  q["options_am"] if use_am else q["options_en"],
                "method":   q["method"],
            })

        print(f"🔴 Loaded {len(questions)} questions from set '{chosen_set['id']}' (seed={seed})")
        return questions

    @staticmethod
    def analyze_compatibility(
        questions: List[Dict],
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

        The 5 questions they were both asked, and how each answered:

        {json.dumps([
            {
                "question": questions[i]["question"] if i < len(questions) else "",
                "method":   questions[i].get("method", "") if i < len(questions) else "",
                person1_name: user_responses[i] if i < len(user_responses) else "",
                person2_name: partner_responses[i] if i < len(partner_responses) else "",
            }
            for i in range(max(len(questions), len(user_responses), len(partner_responses)))
        ], ensure_ascii=False, indent=2)}

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