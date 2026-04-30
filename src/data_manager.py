import csv
import os
import pandas as pd
from typing import List, Dict, Optional, Union

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

class DataManager:
    SCHEMAS = {
        'ingredients.csv': ['name', 'allergy_info', 'preference_text', 'preference_level'],
        'people.csv': ['name', 'health_issues', 'diet_issues', 'goals'],
        'dishes.csv': ['name', 'user_relation', 'rating', 'comments', 'utility', 'protein', 'calories', 'difficulty', 'ingredients', 'is_rotation', 'rotation_frequency', 'rotation_day'],
        'shopping_habits.csv': ['habit_text'],
        'fridge.csv': ['item', 'bought_date', 'expiry_date', 'expected_eat_date'],
        'pantry.csv': ['item'],
        'freezer.csv': ['item'],
        'recipes.csv': ['name', 'ingredients', 'process'],
        'history.csv': ['item', 'action', 'date', 'quantity', 'calories', 'protein', 'fats', 'carbs'],
        'nutrition_log.csv': ['date', 'meal_type', 'dish', 'calories', 'protein', 'fats', 'carbs'],
        'meal_plans.csv': ['date', 'meal_type', 'dish_name', 'notes', 'status'],
        'shopping_list.csv': ['item', 'quantity', 'status', 'added_date']
    }

    def __init__(self):
        self._ensure_data_dir()
        self._init_files()

    def _ensure_data_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _init_files(self):
        for filename, headers in self.SCHEMAS.items():
            filepath = os.path.join(DATA_DIR, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def _get_filepath(self, filename: str) -> str:
        return os.path.join(DATA_DIR, filename)

    def read_table(self, filename: str) -> List[Dict]:
        filepath = self._get_filepath(filename)
        try:
            df = pd.read_csv(filepath)
            df = df.fillna("") # Replace NaNs with empty string
            return df.to_dict('records')
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return []

    def add_entry(self, filename: str, entry: Dict):
        """
        Adds a single entry to the specified CSV file.
        df.to_csv is used to ensure proper escaping and format.
        """
        filepath = self._get_filepath(filename)
        # Validate schema
        expected_keys = set(self.SCHEMAS[filename])
        # Allow extra keys? For now, let's filter to be safe or just append. 
        # Better to ensure all expected keys are present (even if empty).
        row = {k: entry.get(k, '') for k in self.SCHEMAS[filename]}
        
        df = pd.DataFrame([row])
        # Append to file
        df.to_csv(filepath, mode='a', header=False, index=False)

    def update_entry(self, filename: str, key_field: str, key_value: str, updates: Dict):
        """
        Updates an entry where key_field matches key_value.
        Note: This is a simple implementation that rewrites the file.
        """
        filepath = self._get_filepath(filename)
        df = pd.read_csv(filepath)
        
        mask = df[key_field] == key_value
        if mask.any():
            for k, v in updates.items():
                if k in df.columns:
                    df.loc[mask, k] = v
            df.to_csv(filepath, index=False)
            return True
        return False

    def remove_entry(self, filename: str, key_field: str, key_value: str):
        filepath = self._get_filepath(filename)
        df = pd.read_csv(filepath)
        df = df[df[key_field] != key_value]
        df.to_csv(filepath, index=False)

    def get_inventory(self) -> Dict[str, List[Dict]]:
        return {
            'fridge': self.read_table('fridge.csv'),
            'pantry': self.read_table('pantry.csv'),
            'freezer': self.read_table('freezer.csv')
        }

    def save_table(self, filename: str, data: List[Dict]):
        """
        Overwrites the CSV with new list of dicts.
        Useful for bulk edits from UI.
        """
        filepath = self._get_filepath(filename)
        if not data:
            # If empty, just write headers
            headers = self.SCHEMAS.get(filename, [])
            df = pd.DataFrame(columns=headers)
        else:
            df = pd.DataFrame(data)
            # Ensure only schema columns are saved (and all are present)
            headers = self.SCHEMAS.get(filename, [])
            for col in headers:
                if col not in df.columns:
                    df[col] = "" # Fill missing cols
            df = df[headers] # reorder and filter
        
        df.to_csv(filepath, index=False)

    def get_settings(self) -> Dict:
        filepath = self._get_filepath('settings.json')
        if os.path.exists(filepath):
            import json
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"language": "en"} # Default

    def save_settings(self, settings: Dict):
        filepath = self._get_filepath('settings.json')
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
