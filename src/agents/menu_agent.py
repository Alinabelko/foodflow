import json
import datetime
from typing import List, Dict, Optional, Tuple, Any
from .base import BaseAgent
from .validator_agent import ValidatorAgent
from models import DailyMealPlan, MultiDayMealPlan
from context import ContextAssembler

class MenuAgent(BaseAgent):
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.validator = ValidatorAgent(data_manager)
        self.context_assembler = ContextAssembler(data_manager)

    def _get_system_prompt(self, language: str = "en") -> str:
        base_prompt = self._load_prompt("menu_prompt.md")
        return base_prompt.format(language=language)

    def _get_structured_prompt(self, context_str: str, feedback: str = "") -> str:
        base = self._load_prompt("menu_planner_structured.md")
        return base.format(context_str=context_str, feedback=feedback)

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "start_planning_cycle",
                    "description": "Start the rigorous meal planning process for one or more dates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dates": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "List of dates YYYY-MM-DD"
                            },
                            "focus": {"type": "string", "description": "Optional focus"}
                        },
                        "required": ["dates"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_dish_review",
                    "description": "Add or update a dish review/info.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "rating": {"type": "integer", "minimum": 1, "maximum": 10},
                            "comments": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            }
        ]

    def _generate_valid_plan(self, dates: List[str], focus: str = "") -> Tuple[str, List[str]]:
        """
        Executes the Plan -> Validate -> Refine loop for MULTIPLE days.
        """
        logs = []
        logs.append(f"Analyzing inventory and constraints for {len(dates)} days: {dates}")
        
        # 0. Assemble Context
        context_str = self.context_assembler.get_context_snapshot()
        logs.append("Context assembled successfully.")
        
        attempt = 1
        max_retries = 3
        feedback = ""
        
        if focus:
            feedback = f"User Request/Focus: {focus}"
            logs.append(f"Focusing on: {focus}")

        while attempt <= max_retries:
            logs.append(f"Generating meal plan proposal (Attempt {attempt}/{max_retries})...")
            
            # 1. Generate Proposal (MultiDay)
            prompt = self._get_structured_prompt(context_str, feedback)
            prompt += f"\n\n**TASK**: Generate a MultiDayMealPlan for these dates: {', '.join(dates)}."
            messages = [{"role": "system", "content": prompt}]
            
            try:
                response = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=messages,
                    response_format=MultiDayMealPlan
                )
                multi_plan: MultiDayMealPlan = response.choices[0].message.parsed
                logs.append(f"Proposed plans for {len(multi_plan.days)} days.")
            except Exception as e:
                logs.append(f"Error generating plan: {e}")
                return (f"Error generating plan: {e}", logs)

            # 2. Validate All Days
            logs.append("Validating all plans against constraints...")
            all_valid = True
            all_issues = []
            
            # We validate each day individually and aggregate issues
            for plan in multi_plan.days:
                # Ensure date matches what we asked (or strict override)
                # plan.date might need alignment if LLM messed up, but usually it's fine
                report = self.validator.validate_plan(plan, context_str)
                invalid_items = [r for r in report.results if not r.is_valid]
                
                if invalid_items:
                    all_valid = False
                    day_issues = "; ".join([f"{r.meal_type} ({r.dish_name}): {', '.join(r.issues)}" for r in invalid_items])
                    all_issues.append(f"Date {plan.date}: {day_issues}")

            if all_valid:
                logs.append("All days validated successfully!")
                
                # SUCCESS - Save All
                response_str = f"Plan successfully created for {len(dates)} days!\n\n"
                
                for plan in multi_plan.days:
                    date_header = f"### {plan.date}"
                    response_str += f"{date_header}\n"
                    
                    # Process meals + snack
                    candidates = [('breakfast', plan.breakfast), ('lunch', plan.lunch), ('dinner', plan.dinner)]
                    if plan.snack:
                        candidates.append(('snack', plan.snack))
                        
                    for meal_type, candidate in candidates:
                        # Save to DB
                        self.dm.add_entry('meal_plans.csv', {
                            'date': plan.date,
                            'meal_type': meal_type,
                            'dish_name': candidate.dish_name,
                            'notes': candidate.reasoning,
                            'status': 'pending'
                        })
                        
                        needs_str = ""
                        if candidate.missing_ingredients:
                             needs_str = f" (Needs: {', '.join(candidate.missing_ingredients)})"
                        else:
                             needs_str = " (All in stock)"
                             
                        # Servings Flag
                        servings_info = ""
                        if candidate.servings_estimate:
                            servings_info = f" [~{candidate.servings_estimate}srv]"
                            if candidate.is_quantity_assumed:
                                servings_info += "⚠️"
                        
                        response_str += f"**{meal_type.title()}**: {candidate.dish_name}{needs_str}{servings_info}\n"

                        # AUTO-SHOPPING
                        if candidate.missing_ingredients:
                            for item in candidate.missing_ingredients:
                                self.dm.add_entry('shopping_list.csv', {
                                    'item': item,
                                    'quantity': '1', 
                                    'status': 'pending',
                                    'added_date': datetime.date.today().isoformat()
                                })
                    response_str += "\n"
                    
                logs.append("Final plans saved to database.")
                return (response_str, logs)
            
            # FAILURE
            issues_str = "\n".join(all_issues)
            logs.append(f"Validation FAILED. Issues found:\n{issues_str}")
            feedback = f"Previous attempt was rejected. Issues:\n{issues_str}\nPlease fix these constraints."
            attempt += 1 # Only increment if failed
        
        logs.append("Max retries reached. Planning failed.")
        return (f"Failed to generate valid plans after {max_retries} attempts. Last issues:\n{issues_str}", logs)

    def run(self, chat_history: List[Dict]) -> Dict:
        """
        Returns a dict that MAY contain 'logs' key if steps were taken.
        """
        logs = []
        settings = self.dm.get_settings()
        lang = settings.get("language", "en")
        
        system_messages = [{"role": "system", "content": self._get_system_prompt(lang)}]
        
        context_str = self.context_assembler.get_context_snapshot()
        system_messages.append({"role": "system", "content": context_str})

        request_messages = system_messages + chat_history
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=self._get_tools(),
                tool_choice="auto" 
            )
        except Exception as e:
            return {"role": "assistant", "content": f"Error: {e}", "logs": logs}

        msg = response.choices[0].message
        
        if msg.tool_calls:
            results = []
            for tc in msg.tool_calls:
                if tc.function.name == "start_planning_cycle":
                    args = json.loads(tc.function.arguments)
                    
                    # Handle legacy single date or new generic args
                    dates = args.get('dates')
                    if not dates and 'date' in args:
                        dates = [args['date']]
                    
                    if dates:
                        logs.append(f"Starting planning cycle for {dates}...")
                        output, plan_logs = self._generate_valid_plan(dates, args.get('focus', ''))
                        logs.extend(plan_logs)
                    else:
                        output = "Error: No dates specified."
                        
                elif tc.function.name == "add_dish_review":
                    args = json.loads(tc.function.arguments)
                    self.dm.add_entry('dishes.csv', args)
                    output = "Review added."
                    logs.append(f"Added review for {args.get('name')}")
                else:
                    output = "Unknown tool."
                
                results.append({
                    "tool_call_id": tc.id,
                    "output": output
                })
            
            final_content = results[0]['output'] if results else "Done."
            
            return {
                "role": "assistant", 
                "content": final_content,
                "logs": logs
            }
        else:
            return {"role": "assistant", "content": msg.content, "logs": logs}
