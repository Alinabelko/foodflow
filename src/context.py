import datetime
from data_manager import DataManager
from typing import List, Dict

EXPIRY_WARNING_DAYS = 2


class ContextAssembler:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager

    def get_context_snapshot(self) -> str:
        """
        Assembles a read-only text snapshot of the current state for the AI.
        """
        today = datetime.date.today()

        # 1. Inventory (Fridge - Critical)
        fridge = self.dm.read_table('fridge.csv')
        fridge.sort(key=lambda x: x.get('expiry_date', '9999-99-99'))

        # Split into expiring soon vs rest
        expiring_soon = []
        fridge_normal = []
        for item in fridge:
            exp = item.get('expiry_date', '')
            if exp:
                try:
                    exp_date = datetime.date.fromisoformat(exp)
                    days_left = (exp_date - today).days
                    if days_left <= EXPIRY_WARNING_DAYS:
                        expiring_soon.append((item, days_left))
                        continue
                except ValueError:
                    pass
            fridge_normal.append(item)

        fridge_str = "\n".join([
            f"- {i['item']} (Expires: {i.get('expiry_date', 'Unknown')})"
            for i in fridge_normal
        ]) or "(Empty)"

        if expiring_soon:
            expiring_str = "\n".join([
                f"- ⚠️ {item['item']} (Expires: {item.get('expiry_date', '?')}, in {days} day(s)) — MUST BE USED"
                for item, days in expiring_soon
            ])
        else:
            expiring_str = "None"

        # 2. Pantry (Summary)
        pantry = self.dm.read_table('pantry.csv')
        pantry_str = ", ".join([i['item'] for i in pantry]) if pantry else "(Empty)"

        # 3. Freezer
        freezer = self.dm.read_table('freezer.csv')
        freezer_str = ", ".join([i['item'] for i in freezer]) if freezer else "(Empty)"

        # 4. People & Goals
        people = self.dm.read_table('people.csv')
        people_str = ""
        for p in people:
            people_str += f"- {p['name']}: Goal='{p.get('goals', '')}', Diets='{p.get('diet_issues', '')}', Health='{p.get('health_issues', '')}'\n"

        # 5. Bad Ingredients (Strict Dislikes/Allergies)
        ingredients = self.dm.read_table('ingredients.csv')
        bad_stuff = []
        for ing in ingredients:
            level = ing.get('preference_level', 'neutral')
            if level in ['dislike', 'allergy']:
                bad_stuff.append(f"{ing['name']} ({level})")

        bad_stuff_str = ", ".join(bad_stuff) if bad_stuff else "None"

        # 6. Rotation dishes
        dishes = self.dm.read_table('dishes.csv')
        rotation_dishes = [
            d for d in dishes
            if str(d.get('is_rotation', '')).lower() in ('true', '1', 'yes')
        ]
        if rotation_dishes:
            rotation_str = "\n".join([
                f"- {d['name']} (freq: {d.get('rotation_frequency', 'regular')}, day: {d.get('rotation_day', 'any')})"
                for d in rotation_dishes
            ])
        else:
            rotation_str = "None"

        # 7. Recent history (last 7 entries) for variety check
        history = self.dm.read_table('history.csv')
        recent_eaten = [h for h in history if h.get('action') == 'eaten'][-7:]
        history_str = ", ".join([h['item'] for h in recent_eaten]) if recent_eaten else "None"

        # 8. Cold-start flag
        is_cold_start = not people and not fridge and not pantry
        cold_start_notice = (
            "\n⚠️ COLD START: No user profiles or inventory data found. "
            "Generate a basic plan and suggest the user add their profile and inventory for better recommendations.\n"
            if is_cold_start else ""
        )

        # Assemble Final String
        snapshot = f"""{cold_start_notice}
=== EXPIRING SOON (MUST USE — Hard Constraint) ===
{expiring_str}

=== INVENTORY ===
FRIDGE (Use these first!):
{fridge_str}

PANTRY:
{pantry_str}

FREEZER:
{freezer_str}

=== HOUSEHOLD ===
{people_str if people_str else "(No profiles set)"}

=== RESTRICTIONS ===
DO NOT USE (Dislikes/Allergies):
{bad_stuff_str}

=== ROTATION DISHES (Preferred when possible) ===
{rotation_str}

=== RECENT HISTORY (avoid repeats) ===
{history_str}
"""
        return snapshot
