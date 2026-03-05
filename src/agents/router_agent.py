import json
from typing import List, Dict, Optional, Tuple, Any
from .base import BaseAgent
from .menu_agent import MenuAgent
from .shopping_agent import ShoppingAgent

from context import ContextAssembler

class RouterAgent(BaseAgent):
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.menu_agent = MenuAgent(data_manager)
        self.shopping_agent = ShoppingAgent(data_manager)
        self.context_assembler = ContextAssembler(data_manager)
        self.chat_history: List[Dict] = []

    def _get_system_prompt(self, language: str = "en") -> str:
        base_prompt = self._load_prompt("router_prompt.md")
        return base_prompt.format(language=language)

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "handoff_to_menu_agent",
                    "description": "Delegate to the Menu Planning Agent for meal planning, recipes, or dish reviews.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for handoff"}
                        },
                        "required": ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "handoff_to_shopping_agent",
                    "description": "Delegate to the Shopping Agent for shopping lists, inventory updates, or shopping habits.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for handoff"}
                        },
                        "required": ["reason"]
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
                            "calories": {"type": "integer"},
                            "protein": {"type": "integer"},
                            "fats": {"type": "integer"},
                            "carbs": {"type": "integer"}
                        },
                        "required": ["item", "action", "date"]
                    }
                }
            }
        ]

    def _execute_tool_calls(self, tool_calls_list) -> List[Dict]:
        # Router only handles its own tools natively
        results = []
        for tool_call in tool_calls_list:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            output = ""

            if func_name == "update_person_info":
                if self.dm.update_entry('people.csv', 'name', args['name'], args):
                     output = "Updated person info."
                else:
                    self.dm.add_entry('people.csv', args)
                    output = "Added new person."
            
            elif func_name == "log_history":
                self.dm.add_entry('history.csv', args)
                output = "Logged history."
            
            results.append({
                "tool_call_id": tool_call.id,
                "output": output
            })
        return results

    def _encode_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def clear_history(self):
        self.chat_history = []

    def translate_database(self, target_language: str):
        # ... logic as before ...
        pass

    def process_message(self, user_text: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns {'response': str, 'logs': List[str]}
        """
        settings = self.dm.get_settings()
        lang = settings.get("language", "en")
        logs = []
        
        system_messages = [{"role": "system", "content": self._get_system_prompt(lang)}]
        
        # Inject Assembler Snapshot for Router as well
        context_str = self.context_assembler.get_context_snapshot()
        system_messages.append({"role": "system", "content": context_str})
        
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
        
        request_messages = system_messages + self.chat_history
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=self._get_tools(),
                tool_choice="auto" 
            )
        except Exception as e:
            return {"response": f"Error connecting to Router AI: {str(e)}", "logs": []}
        
        msg = response.choices[0].message
        
        tool_calls = msg.tool_calls
        handoff_occurred = False
        
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name == "handoff_to_menu_agent":
                    handoff_occurred = True
                    logs.append("Router: Handing off to Menu Agent...")
                    
                    # Result might be a dict (with logs) or message (legacy)
                    res = self.menu_agent.run(self.chat_history)
                    
                    # Handle return types
                    if isinstance(res, dict):
                        content = res.get("content", "")
                        agent_logs = res.get("logs", [])
                        logs.extend(agent_logs)
                        # We reconstruct a message object for history
                        res_msg = {"role": "assistant", "content": content}
                        self.chat_history.append(res_msg)
                        return {"response": content, "logs": logs}
                    else:
                        # Fallback for old style if any
                        self.chat_history.append(res)
                        return {"response": res.content, "logs": logs}
                
                elif tool_call.function.name == "handoff_to_shopping_agent":
                    handoff_occurred = True
                    logs.append("Router: Handing off to Shopping Agent...")
                    # Shopping agent run logic (assume similar update or just returns msg for now)
                    res_msg = self.shopping_agent.run(self.chat_history)
                    # Shopping Agent probably still returns simple Message object unless updated
                    content = res_msg.content
                    self.chat_history.append(res_msg)
                    return {"response": content, "logs": logs}

            if not handoff_occurred:
                tool_outputs = self._execute_tool_calls(tool_calls)
                logs.append("Router: Executing local tools...")
                
                self.chat_history.append(msg)
                request_messages.append(msg)
                
                for tool_out in tool_outputs:
                    t_msg = {
                        "role": "tool",
                        "tool_call_id": tool_out["tool_call_id"], 
                        "content": tool_out["output"]
                    }
                    self.chat_history.append(t_msg)
                    request_messages.append(t_msg)
                    logs.append(f"Router Tool: {tool_out['output']}")
                
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=request_messages
                )
                final_msg = final_response.choices[0].message
                self.chat_history.append(final_msg)
                return {"response": final_msg.content, "logs": logs}
        
        else:
            self.chat_history.append(msg)
            return {"response": msg.content, "logs": logs}
