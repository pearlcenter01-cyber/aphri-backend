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
    def _score_answers(a1: str, a2: str) -> dict:
        """
        Deterministic comparison of one answer pair.
        Returns: { 'score': 0-100, 'verdict': 'match' | 'partial' | 'mismatch' }
        """
        s1 = (a1 or "").strip().lower()
        s2 = (a2 or "").strip().lower()
        if not s1 and not s2:
            return {"score": 50, "verdict": "partial"}
        if not s1 or not s2:
            return {"score": 15, "verdict": "mismatch"}
        if s1 == s2:
            return {"score": 100, "verdict": "match"}
        w1 = set(re.findall(r"\w+", s1))
        w2 = set(re.findall(r"\w+", s2))
        if not w1 or not w2:
            return {"score": 15, "verdict": "mismatch"}
        overlap = len(w1 & w2)
        union = len(w1 | w2)
        jaccard = overlap / union if union else 0
        score = int(20 + jaccard * 80)
        if score >= 70:
            verdict = "match"
        elif score >= 40:
            verdict = "partial"
        else:
            verdict = "mismatch"
        return {"score": score, "verdict": verdict}

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

        questions = []
        for q in chosen_set["questions"]:
            questions.append({
                "question": q.get("text_en", ""),
                "question_am": q.get("text_am", ""),
                "options": q.get("options_en", []),
                "options_am": q.get("options_am", []),
                "method": q.get("method", "General"),
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
        deterministic_score: int = 0,
    ) -> Dict[str, Any]:

        print(f"🔴 analyze_compatibility CALLED with deterministic_score={deterministic_score}")

        # Reports are always generated in English. Amharic is handled manually
        # via the translation request flow.
        lang_name = "English"

        # Build per-question summary for the AI
        pair_count = min(len(questions), len(user_responses), len(partner_responses))
        per_question = []
        for i in range(pair_count):
            ua = user_responses[i]
            pa = partner_responses[i]
            verdict = "match" if (ua and pa and ua == pa) else "mismatch"
            per_question.append({
                "question": questions[i]["question"],
                "method": questions[i].get("method", ""),
                "you_said_index": ua,
                "they_said_index": pa,
                "verdict": verdict,
            })

        prompt = f"""
        You are a warm, wise friend writing a relationship compatibility report.

        IMPORTANT: The score is already decided. You are NOT scoring. You must not change it.

        Overall score: {deterministic_score} / 100
        (Each of the 5 questions is worth 20 points. Same answer = 20, different = 0.)

        The two people: {person1_name} and {person2_name}.

        Questions and answers (option indices, both partners answered the same option set):

        {json.dumps(per_question, ensure_ascii=False, indent=2)}

        Write the entire report in {lang_name}.

        Use their real names — {person1_name} and {person2_name} — everywhere.
        Never say "Partner 1", "Partner 2", "person1", or "person2".

        Return JSON in exactly this structure:

        {{
            "score": {deterministic_score},
            "opening": "<2-3 sentences. Acknowledge what their answers show, matching the score.>",
            "what_works": ["<one sentence for each matched question. If none, say so honestly.>"],
            "what_to_watch": ["<one sentence for each mismatched question. If none, say so.>"],
            "for_you": {{
                "person1": {{"do": ["<concrete actions for {person1_name}>"], "dont": ["<things to avoid>"]}},
                "person2": {{"do": ["<concrete actions for {person2_name}>"], "dont": ["<things to avoid>"]}}
            }},
            "closing": "<2-3 sentences. Encouraging, grounded, matching the score.>"
        }}

        Rules:
        - The score is {deterministic_score}. Never change it.
        - If a question's verdict is 'mismatch', say so plainly.
        - If a question's verdict is 'match', treat it as a strength.
        - Do not mention "question 3" or any question number.
        - If all questions are mismatches, the report must reflect that honestly.
        """

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a warm, wise friend writing a relationship report in {lang_name}. "
                            "You are NOT scoring — the score is fixed. Follow the JSON structure. "
                            "Never change the score."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
            )

            report_text = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", report_text, re.DOTALL)
            report = json.loads(json_match.group()) if json_match else json.loads(report_text)

            report["score"] = deterministic_score
            return report

        except Exception as e:
            print(f"❌ Error analyzing compatibility: {e}")
            import traceback
            traceback.print_exc()
            return {
                "score": deterministic_score,
                "opening": f"{person1_name} and {person2_name}, you both showed up honestly for this.",
                "what_works": [],
                "what_to_watch": [],
                "for_you": {
                    "person1": {"do": [], "dont": []},
                    "person2": {"do": [], "dont": []},
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