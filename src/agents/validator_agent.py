import json
from typing import List, Dict, Any
from .base import BaseAgent
from models import DailyMealPlan, ValidationReport

class ValidatorAgent(BaseAgent):
    def _get_system_prompt(self, language: str = "en") -> str:
        base_prompt = self._load_prompt("validator_prompt.md")
        return base_prompt.format(language=language)

    def validate_plan(self, plan: DailyMealPlan, context_str: str) -> ValidationReport:
        """
        Validates a proposed DailyMealPlan using the LLM.
        """
        settings = self.dm.get_settings()
        lang = settings.get("language", "en")
        
        system_prompt = self._get_system_prompt(lang)
        
        # Construct the user message containing the plan to validate
        # We perform a strict validation call
        user_content = f"""
        CONTEXT:
        {context_str}

        PROPOSED PLAN FOR {plan.date}:
        Breakfast: {plan.breakfast.dish_name} - {plan.breakfast.reasoning} (Ingredients: {plan.breakfast.ingredients_needed})
        Lunch: {plan.lunch.dish_name} - {plan.lunch.reasoning} (Ingredients: {plan.lunch.ingredients_needed})
        Dinner: {plan.dinner.dish_name} - {plan.dinner.reasoning} (Ingredients: {plan.dinner.ingredients_needed})
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            # key distinction: using beta.chat.completions.parse for structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=ValidationReport
            )
            return response.choices[0].message.parsed
        except Exception as e:
            print(f"Validator Error: {e}")
            # Fallback or error handling
            return ValidationReport(results=[])
