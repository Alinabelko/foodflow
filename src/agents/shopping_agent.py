import json
import datetime
from typing import List, Dict, Optional
from .base import BaseAgent

class ShoppingAgent(BaseAgent):
    def _get_system_prompt(self, language: str = "en") -> str:
        base_prompt = self._load_prompt("shopping_prompt.md")
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
                                        # In Shopping Agent, often "add" means "Bought".
                                        "storage_location": {"type": "string", "enum": ["fridge", "pantry", "freezer"]},
                                        "item_name": {"type": "string"},
                                        "action": {"type": "string", "enum": ["add", "remove"]},
                                        "quantity": {"type": "string", "description": "e.g. '2 liters', '1 box'"},
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
                    "name": "update_shopping_habit",
                    "description": "Update shopping habits/routine information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "habit_text": {"type": "string", "description": "Description of shopping habit"}
                        },
                        "required": ["habit_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_shopping_list",
                    "description": "Add, remove, or check items in the shopping list.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["add", "remove", "check"]},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "item": {"type": "string"},
                                        "quantity": {"type": "string"}
                                    },
                                    "required": ["item"]
                                }
                            }
                        },
                        "required": ["action", "items"]
                    }
                }
            }
        ]

    def _execute_tool_calls(self, tool_calls_list) -> List[Dict]:
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
                        output += "Added to inventory. "
                    elif update['action'] == 'remove':
                        self.dm.remove_entry(loc, 'item', update['item_name'])
                        output += "Removed from inventory. "

            elif func_name == "update_shopping_habit":
                 self.dm.add_entry('shopping_habits.csv', args)
                 output = "Updated shopping habits"

            elif func_name == "manage_shopping_list":
                action = args['action']
                for item_obj in args['items']:
                    if action == 'add':
                        item_obj['status'] = 'pending'
                        item_obj['added_date'] = datetime.date.today().isoformat()
                        # If quantity missing
                        if 'quantity' not in item_obj: item_obj['quantity'] = '1'
                        self.dm.add_entry('shopping_list.csv', item_obj)
                        output += f"Added {item_obj['item']}. "
                    
                    elif action == 'remove':
                        self.dm.remove_entry('shopping_list.csv', 'item', item_obj['item'])
                        output += f"Removed {item_obj['item']}. "
                    
                    # 'check' is implicitly handled by the agent's context usually, or we can return list here
                    # But for now, let's assume 'check' is just reading, but this tool is for modification mainly.
                    # If Agent wants to read, they should rely on system context. If the system prompt includes the list.
            
            results.append({
                "tool_call_id": tool_call.id,
                "output": output
            })
        return results

    def run(self, chat_history: List[Dict]) -> Dict:
        """
        Executes the agent logic.
        """
        settings = self.dm.get_settings()
        lang = settings.get("language", "en")
        
        system_messages = [{"role": "system", "content": self._get_system_prompt(lang)}]
        
        # Context extraction - Shopping needs inventory and Shopping List
        inv = self.dm.get_inventory()
        shopping_list = self.dm.read_table('shopping_list.csv')
        
        context_str = f"Current Inventory: Fridge has {len(inv['fridge'])} items. "
        context_str += f"Current Shopping List has {len(shopping_list)} items: " + \
                       ", ".join([i['item'] for i in shopping_list[:10]]) # Limit for context
        
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
             return {"role": "assistant", "content": f"Error in ShoppingAgent: {str(e)}"}

        msg = response.choices[0].message
        
        tool_calls = msg.tool_calls
        if tool_calls:
            tool_outputs = self._execute_tool_calls(tool_calls)
            
            turn_history = request_messages.copy()
            turn_history.append(msg)
            
            for tool_out in tool_outputs:
                turn_history.append({
                    "role": "tool",
                    "tool_call_id": tool_out["tool_call_id"], 
                    "content": tool_out["output"]
                })
            
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=turn_history
            )
            return final_response.choices[0].message
        else:
            return msg
