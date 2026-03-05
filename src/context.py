from data_manager import DataManager
from typing import List, Dict

class ContextAssembler:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager

    def get_context_snapshot(self) -> str:
        """
        Assembles a read-only text snapshot of the current state for the AI.
        """
        # 1. Inventory (Fridge - Critical)
        fridge = self.dm.read_table('fridge.csv')
        # Sort by expiry if possible (assuming ISO format YYYY-MM-DD works for string sort ok-ish, 
        # but empty strings rank first. Let's filter empty first or just sort.)
        fridge.sort(key=lambda x: x.get('expiry_date', '9999-99-99')) 
        
        fridge_str = "\n".join([f"- {i['item']} (Qty: {i.get('quantity','?')}, Expires: {i.get('expiry_date', 'Unknown')})" for i in fridge])
        if not fridge: fridge_str = "(Empty)"

        # 2. Pantry (Summary)
        pantry = self.dm.read_table('pantry.csv')
        pantry_str = ", ".join([i['item'] for i in pantry]) if pantry else "(Empty)"

        # 3. People & Goals
        people = self.dm.read_table('people.csv')
        people_str = ""
        for p in people:
            people_str += f"- {p['name']}: Goal='{p.get('goals','')}', Diets='{p.get('diet_issues','')}'\n"

        # 4. Bad Ingredients (Strict Dislikes/Allergies)
        ingredients = self.dm.read_table('ingredients.csv')
        bad_stuff = []
        for ing in ingredients:
            level = ing.get('preference_level', 'neutral')
            if level in ['dislike', 'allergy']:
                bad_stuff.append(f"{ing['name']} ({level})")
        
        bad_stuff_str = ", ".join(bad_stuff) if bad_stuff else "None"

        # Assemble Final String
        snapshot = f"""
=== INVENTORY ===
FRIDGE (Use these first!):
{fridge_str}

PANTRY:
{pantry_str}

=== HOUSEHOLD ===
{people_str}

=== RESTRICTIONS ===
DO NOT USE (Dislikes/Allergies):
{bad_stuff_str}
"""
        return snapshot
