import os
import json
from data_manager import DataManager
from openai import OpenAI
from typing import List, Dict, Optional, Any

class BaseAgent:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        )
        self.model = "gpt-5-mini"

    def _load_prompt(self, filename: str) -> str:
        try:
            # Assuming prompts are in src/prompts relative to src/agents/base.py
            # base.py is in src/agents, so prompts is ../prompts
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_path, "prompts", filename)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt {filename}: {e}")
            return ""

    def _execute_tool_calls(self, tool_calls_list) -> List[Dict]:
        """
        To be overridden or used by subclasses if they share tools.
        For now, let's keep it abstract or generic.
        """
        return []
