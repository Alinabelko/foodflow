from pydantic import BaseModel, Field
from typing import List, Optional

class MealCandidate(BaseModel):
    dish_name: str = Field(..., description="Name of the dish")
    reasoning: str = Field(..., description="Why this dish was chosen (e.g. utilizes expiring ingredients)")
    ingredients_needed: List[str] = Field(..., description="List of main ingredients needed")
    missing_ingredients: List[str] = Field(default_factory=list, description="Ingredients that are NOT in the current inventory and need to be bought")
    servings_estimate: Optional[int] = Field(None, description="Estimated number of servings based on inventory usage")
    is_quantity_assumed: bool = Field(False, description="True if inventory quantity was unknown/guessed")

class DailyMealPlan(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    breakfast: MealCandidate
    lunch: MealCandidate
    dinner: MealCandidate
    snack: Optional[MealCandidate] = Field(None, description="Optional snack")

class MultiDayMealPlan(BaseModel):
    days: List[DailyMealPlan] = Field(..., description="List of daily plans")

class ValidationResult(BaseModel):
    meal_type: str = Field(..., description="breakfast, lunch, or dinner")
    dish_name: str
    is_valid: bool
    issues: List[str] = Field(default_factory=list, description="List of specific issues if invalid")
    score: int = Field(..., description="0-100 suitability score")

class ValidationReport(BaseModel):
    results: List[ValidationResult]
