import type { Profile, MealPlan, MealPlanDetail, ShoppingList, InventoryItem } from "@/types";

export const mockProfiles: Profile[] = [
  {
    id: "p1",
    name: "Alonso",
    goal: "muscle_gain",
    restrictions: ["gluten-free"],
    calorie_target: 2800,
    protein_target: 200,
    carbs_target: 300,
    fat_target: 80,
    created_at: "2026-01-01T00:00:00",
  },
  {
    id: "p2",
    name: "Maria",
    goal: "fat_loss",
    restrictions: [],
    calorie_target: 1800,
    protein_target: 130,
    carbs_target: 200,
    fat_target: 60,
    created_at: "2026-01-01T00:00:00",
  },
];

export const mockMealPlan: MealPlan = {
  id: "mp1",
  week_start: "2026-03-09",
  week_end: "2026-03-14",
  status: "active",
  created_at: "2026-03-07T10:00:00",
};

export const mockMealPlanDetail: MealPlanDetail = {
  ...mockMealPlan,
  meals: [
    {
      id: "m1",
      day_of_week: 1,
      meal_type: "lunch",
      name: "Grilled Chicken Salad",
      description: "Fresh salad with grilled chicken",
      recipe_steps: ["Grill chicken", "Toss salad", "Serve"],
      prep_time_min: 10,
      cook_time_min: 15,
      portions: [
        { id: "po1", profile_id: "p1", serving_size: "1.5 portions", calories: 650, protein_g: 55, carbs_g: 30, fat_g: 20 },
        { id: "po2", profile_id: "p2", serving_size: "1 portion", calories: 450, protein_g: 40, carbs_g: 25, fat_g: 15 },
      ],
      ingredients: [
        { id: "i1", name: "Chicken breast", quantity: "400", unit: "g", category: "protein" },
        { id: "i2", name: "Mixed greens", quantity: "200", unit: "g", category: "produce" },
      ],
    },
    {
      id: "m2",
      day_of_week: 1,
      meal_type: "dinner",
      name: "Salmon with Rice",
      description: "Baked salmon with steamed rice",
      recipe_steps: ["Season salmon", "Bake at 200C", "Cook rice"],
      prep_time_min: 10,
      cook_time_min: 25,
      portions: [
        { id: "po3", profile_id: "p1", serving_size: "2 portions", calories: 800, protein_g: 60, carbs_g: 70, fat_g: 25 },
        { id: "po4", profile_id: "p2", serving_size: "1 portion", calories: 550, protein_g: 45, carbs_g: 50, fat_g: 18 },
      ],
      ingredients: [
        { id: "i3", name: "Salmon fillet", quantity: "500", unit: "g", category: "protein" },
        { id: "i4", name: "Rice", quantity: "300", unit: "g", category: "grains" },
      ],
    },
  ],
};

export const mockInventoryItems: InventoryItem[] = [
  {
    id: "inv1",
    name: "Pollo",
    quantity: "500",
    unit: "g",
    category: "protein",
    storage_location: "fridge",
    created_at: "2026-03-10T10:00:00",
  },
  {
    id: "inv2",
    name: "Brócoli",
    quantity: "300",
    unit: "g",
    category: "produce",
    storage_location: "fridge",
    created_at: "2026-03-10T11:00:00",
  },
  {
    id: "inv3",
    name: "Helado",
    quantity: "1",
    unit: "L",
    category: "dairy",
    storage_location: "freezer",
    created_at: "2026-03-10T12:00:00",
  },
];

export const mockShoppingList: ShoppingList = {
  categories: {
    protein: [
      { name: "Chicken Breast", total_quantity: "400", unit: "g", category: "protein" },
      { name: "Salmon Fillet", total_quantity: "500", unit: "g", category: "protein" },
    ],
    produce: [
      { name: "Mixed Greens", total_quantity: "200", unit: "g", category: "produce" },
    ],
    grains: [
      { name: "Rice", total_quantity: "300", unit: "g", category: "grains" },
    ],
  },
};
