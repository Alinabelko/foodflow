import os
import json
import datetime
from typing import List, Dict, Optional, Any
from openai import OpenAI
from data_manager import DataManager

class NutritionAgent:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-5-mini" # Using gpt-5-mini as requested, supports vision
        self.chat_history: List[Dict] = []

    def _load_prompt(self, filename: str) -> str:
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_path, "prompts", filename)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt {filename}: {e}")
            return ""

    def _get_system_prompt(self, language: str = "en") -> str:
        base_prompt = self._load_prompt("system_prompt.md")
        return base_prompt.format(language=language)

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "update_inventory",
                    "description": "Add or remove items from fridge, pantry, or freezer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "updates": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "storage_location": {"type": "string", "enum": ["fridge", "pantry", "freezer"]},
                                        "item_name": {"type": "string"},
                                        "action": {"type": "string", "enum": ["add", "remove"]},
                                        "quantity": {"type": "string", "description": "e.g. '2 liters', '1 box'"},
                                        # Specific to fridge
                                        "bought_date": {"type": "string", "description": "YYYY-MM-DD"},
                                        "expiry_date": {"type": "string", "description": "YYYY-MM-DD"},
                                        "expected_eat_date": {"type": "string", "description": "YYYY-MM-DD"}
                                    },
                                    "required": ["storage_location", "item_name", "action"]
                                }
                            }
                        },
                        "required": ["updates"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_person_info",
                    "description": "Update information about a family member/person.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "health_issues": {"type": "string"},
                            "diet_issues": {"type": "string"},
                            "goals": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "log_history",
                    "description": "Log what was eaten or bought to history.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "action": {"type": "string", "enum": ["eaten", "bought"]},
                            "date": {"type": "string", "description": "YYYY-MM-DD"},
                            "quantity": {"type": "string"},
                            "calories": {"type": "integer", "description": "Estimated calories (kcal)"},
                            "protein": {"type": "integer", "description": "Estimated protein (g)"},
                            "fats": {"type": "integer", "description": "Estimated fats (g)"},
                            "carbs": {"type": "integer", "description": "Estimated carbs (g)"}
                        },
                        "required": ["item", "action", "date"]
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
                            "comments": {"type": "string"},
                            "ingredients": {"type": "string", "description": "Comma separated list"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_ingredient_info",
                    "description": "Update information about an ingredient (allergies, preferences).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "allergy_info": {"type": "string"},
                            "preference_text": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_recipe",
                    "description": "Add or update a user's own recipe.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "ingredients": {"type": "string", "description": "List of ingredients"},
                            "process": {"type": "string", "description": "Cooking process description"}
                        },
                        "required": ["name", "process"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_shopping_habit",
                    "description": "Update shopping habits/routine information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "habit_text": {"type": "string", "description": "Description of shopping habit (e.g. 'Shop every Friday at Wallmart')"}
                        },
                        "required": ["habit_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_meal_plan",
                    "description": "Save a meal plan entry for a specific date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "YYYY-MM-DD"},
                            "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
                            "dish_name": {"type": "string"},
                            "notes": {"type": "string"}
                        },
                "required": ["date", "meal_type", "dish_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_daily_plan",
                    "description": "Clear all meal plan entries for a specific date (e.g., when re-planning).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "YYYY-MM-DD"}
                        },
                        "required": ["date"]
                    }
                }
            }
            # Add more tools for other tables as needed (Ingredients, ShoppingHabits, Recipes)
        ]

    def _execute_tool_calls(self, tool_calls_list):
        results = []
        for tool_call in tool_calls_list:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            output = ""
            
            if func_name == "update_inventory":
                for update in args['updates']:
                    loc = f"{update['storage_location']}.csv"
                    if update['action'] == 'add':
                        entry = {'item': update['item_name']}
                        if update['storage_location'] == 'fridge':
                            entry['bought_date'] = update.get('bought_date', datetime.date.today().isoformat())
                            entry['expiry_date'] = update.get('expiry_date', '')
                            entry['expected_eat_date'] = update.get('expected_eat_date', '')
                        self.dm.add_entry(loc, entry)
                        output += "Added item. "
                    elif update['action'] == 'remove':
                        self.dm.remove_entry(loc, 'item', update['item_name'])
                        output += "Removed item. "

            elif func_name == "update_person_info":
                if self.dm.update_entry('people.csv', 'name', args['name'], args):
                     output = "Updated person info."
                else:
                    self.dm.add_entry('people.csv', args)
                    output = "Added new person."

            elif func_name == "log_history":
                self.dm.add_entry('history.csv', args)
                output = "Logged history."
            
            elif func_name == "add_dish_review":
                self.dm.add_entry('dishes.csv', args)
                output = "Recorded review."

            elif func_name == "update_ingredient_info":
                if self.dm.update_entry('ingredients.csv', 'name', args['name'], args):
                    output = "Updated ingredient info."
                else:
                    self.dm.add_entry('ingredients.csv', args)
                    output = "Added ingredient info."

            elif func_name == "update_recipe":
                self.dm.add_entry('recipes.csv', args)
                output = "Added recipe."

            elif func_name == "update_shopping_habit":
                 self.dm.add_entry('shopping_habits.csv', args)
                 output = "Updated shopping habits"

            elif func_name == "save_meal_plan":
                # Default status to 'pending' if not provided by agent, but agent should use it
                if 'status' not in args:
                    args['status'] = 'pending'
                self.dm.add_entry('meal_plans.csv', args)
                # Silent output for save_meal_plan as requested
                output = "Saved meal plan."

            elif func_name == "clear_daily_plan":
                self.dm.remove_entry('meal_plans.csv', 'date', args['date'])
                output = "Cleared plan."
            
            results.append({
                "tool_call_id": tool_call.id,
                "output": output
            })

        return results

    def _encode_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def process_message(self, user_text: str, image_path: Optional[str] = None) -> str:
        settings = self.dm.get_settings()
        lang = settings.get("language", "en")
        
        # System messages (Prompt + Context) - always fresh
        system_messages = [{"role": "system", "content": self._get_system_prompt(lang)}]
        
        # Inject current context summaries
        inv = self.dm.get_inventory()
        context_str = f"Current Inventory: Fridge has {len(inv['fridge'])} items. "
        # Add more context logic if needed
        system_messages.append({"role": "system", "content": context_str})

        # Prepare User Message
        user_content = [{"type": "text", "text": user_text}]
        if image_path:
            base64_image = self._encode_image(image_path)
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        user_msg = {"role": "user", "content": user_content}
        self.chat_history.append(user_msg)

        # Build full request messages
        request_messages = system_messages + self.chat_history

        # 1. Analyze for DB updates
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=self._get_tools(),
                tool_choice="auto" 
            )
        except Exception as e:
            return f"Error connecting to AI: {str(e)}"

        msg = response.choices[0].message
        
        # Update history with assistant's response
        # We store the message object (or dict) to preserve tool calls
        self.chat_history.append(msg)
        request_messages.append(msg)

        tool_calls = msg.tool_calls

        if tool_calls:
            # Execute updates
            tool_outputs = self._execute_tool_calls(tool_calls)
            
            # Add tool outputs to history and request
            for tool_out in tool_outputs:
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tool_out["tool_call_id"], 
                    "content": tool_out["output"]
                }
                self.chat_history.append(tool_msg)
                request_messages.append(tool_msg)
            
            # Follow-up completion
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages
            )
            final_msg = final_response.choices[0].message
            self.chat_history.append(final_msg)
            
            return final_msg.content
            return final_msg.content
        else:
            return msg.content

    def clear_history(self):
        self.chat_history = []


    def translate_database(self, target_language: str):
        """
        Translates all content in the database to the target language.
        This is a heavy operation.
        """
        inventory = self.dm.get_inventory()
        # Also need other files
        all_files = list(self.dm.SCHEMAS.keys())
        
        for filename in all_files:
            data = self.dm.read_table(filename)
            if not data:
                continue
                
            # Convert entire table to JSON string for context
            json_str = json.dumps(data, ensure_ascii=False)
            
            prompt_template = self._load_prompt("translation_prompt.md")
            prompt = prompt_template.format(target_language=target_language, json_str=json_str)
            
            try:
                response = self.client.chat.completions.create(
                    model="gpt-5-mini", # Fast model for translation
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                translated_json = response.choices[0].message.content
                translated_data = json.loads(translated_json)
                
                # Depending on how the model returns it (list or wrapper), handle:
                if isinstance(translated_data, dict) and 'data' in translated_data:
                     translated_data = translated_data['data']
                elif isinstance(translated_data, dict):
                     # Try to find the list
                     for k, v in translated_data.items():
                         if isinstance(v, list):
                             translated_data = v
                             break
                
                if isinstance(translated_data, list):
                    self.dm.save_table(filename, translated_data)
            except Exception as e:
                print(f"Failed to translate {filename}: {e}")
