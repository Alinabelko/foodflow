"""
Shared seed helpers and date utilities for FoodFlow e2e tests.
Imported directly by test modules (unlike conftest.py which is pytest-magic).
"""
import datetime
from data_manager import DataManager


def seed_fridge(dm: DataManager, items: list):
    """
    Add items to fridge.csv.
    Each dict may contain: item, bought_date, expiry_date, expected_eat_date
    """
    today = datetime.date.today().isoformat()
    for item in items:
        entry = {
            "item": item["item"],
            "bought_date": item.get("bought_date", today),
            "expiry_date": item.get("expiry_date", ""),
            "expected_eat_date": item.get("expected_eat_date", ""),
        }
        dm.add_entry("fridge.csv", entry)


def seed_pantry(dm: DataManager, items: list):
    """Add simple items to pantry.csv."""
    for item in items:
        dm.add_entry("pantry.csv", {"item": item})


def seed_people(dm: DataManager, people: list):
    """
    Add people to people.csv.
    Each dict may contain: name, health_issues, diet_issues, goals
    """
    for person in people:
        dm.add_entry("people.csv", {
            "name": person["name"],
            "health_issues": person.get("health_issues", ""),
            "diet_issues": person.get("diet_issues", ""),
            "goals": person.get("goals", ""),
        })


def seed_ingredients(dm: DataManager, ingredients: list):
    """
    Add ingredients to ingredients.csv.
    Each dict may contain: name, allergy_info, preference_text, preference_level
    """
    for ing in ingredients:
        dm.add_entry("ingredients.csv", {
            "name": ing["name"],
            "allergy_info": ing.get("allergy_info", ""),
            "preference_text": ing.get("preference_text", ""),
            "preference_level": ing.get("preference_level", "neutral"),
        })


def today_str() -> str:
    return datetime.date.today().isoformat()


def tomorrow_str() -> str:
    return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


def days_from_now(n: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=n)).isoformat()
