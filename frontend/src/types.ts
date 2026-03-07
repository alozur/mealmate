export interface Profile {
  id: string;
  name: string;
  goal: string;
  restrictions: string[];
  calorie_target: number;
  protein_target: number;
  carbs_target: number;
  fat_target: number;
  created_at: string;
}

export interface MealPortion {
  id: string;
  profile_id: string;
  serving_size: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface Ingredient {
  id: string;
  name: string;
  quantity: string;
  unit: string | null;
  category: string;
}

export interface Meal {
  id: string;
  day_of_week: number;
  meal_type: "lunch" | "dinner";
  name: string;
  description: string | null;
  recipe_steps: string[];
  prep_time_min: number | null;
  cook_time_min: number | null;
  portions: MealPortion[];
  ingredients: Ingredient[];
}

export interface MealPlan {
  id: string;
  week_start: string;
  week_end: string;
  status: string;
  created_at: string;
}

export interface MealPlanDetail extends MealPlan {
  meals: Meal[];
}

export interface ShoppingListItem {
  name: string;
  total_quantity: string;
  unit: string | null;
  category: string;
}

export interface ShoppingList {
  categories: Record<string, ShoppingListItem[]>;
}

export const DAY_NAMES: Record<number, string> = {
  1: "Monday",
  2: "Tuesday",
  3: "Wednesday",
  4: "Thursday",
  5: "Friday",
  6: "Saturday",
};

export const GOAL_LABELS: Record<string, string> = {
  muscle_gain: "Muscle Gain",
  fat_loss: "Fat Loss",
  maintenance: "Maintenance",
  general_health: "General Health",
};
