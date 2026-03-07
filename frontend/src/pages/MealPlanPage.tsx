import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  RefreshCw,
  ShoppingCart,
} from "lucide-react";
import { api } from "@/api/client";
import type { Meal, MealPlanDetail, Profile } from "@/types";
import { DAY_NAMES } from "@/types";

export default function MealPlanPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<MealPlanDetail | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [regeneratingMeal, setRegeneratingMeal] = useState<string | null>(null);
  const [expandedMeal, setExpandedMeal] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get<MealPlanDetail>(`/meal-plans/${id}`),
      api.get<Profile[]>("/profiles"),
    ])
      .then(([p, pr]) => {
        setPlan(p);
        setProfiles(pr);
      })
      .catch(() => navigate("/dashboard"))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleRegenerate = async (mealId: string) => {
    if (!id) return;
    setRegeneratingMeal(mealId);
    try {
      const newMeal = await api.post<Meal>(
        `/meal-plans/${id}/regenerate-meal/${mealId}`,
      );
      setPlan((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          meals: prev.meals.map((m) =>
            m.id === mealId ? newMeal : m,
          ),
        };
      });
    } catch {
      // silently fail for now
    } finally {
      setRegeneratingMeal(null);
    }
  };

  const profileMap = Object.fromEntries(profiles.map((p) => [p.id, p]));

  if (loading || !plan) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const mealsByDay: Record<number, Meal[]> = {};
  for (const meal of plan.meals) {
    (mealsByDay[meal.day_of_week] ??= []).push(meal);
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("/dashboard")} className="p-1">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold">
            Week of {new Date(plan.week_start).toLocaleDateString()}
          </h1>
        </div>
        <button
          onClick={() => navigate(`/shopping/${plan.id}`)}
          className="flex items-center gap-1 bg-primary text-primary-foreground rounded-lg px-3 py-2 text-sm font-medium"
        >
          <ShoppingCart className="w-4 h-4" />
          Shopping List
        </button>
      </div>

      {[1, 2, 3, 4, 5, 6].map((day) => {
        const dayMeals = mealsByDay[day] ?? [];
        return (
          <div key={day} className="mb-6">
            <h2 className="text-lg font-semibold mb-3 text-primary">
              {DAY_NAMES[day]}
            </h2>
            <div className="space-y-3">
              {dayMeals
                .sort((a, b) => (a.meal_type === "lunch" ? -1 : 1))
                .map((meal) => (
                  <MealCard
                    key={meal.id}
                    meal={meal}
                    profileMap={profileMap}
                    expanded={expandedMeal === meal.id}
                    onToggle={() =>
                      setExpandedMeal(
                        expandedMeal === meal.id ? null : meal.id,
                      )
                    }
                    onRegenerate={() => handleRegenerate(meal.id)}
                    regenerating={regeneratingMeal === meal.id}
                  />
                ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MealCard({
  meal,
  profileMap,
  expanded,
  onToggle,
  onRegenerate,
  regenerating,
}: {
  meal: Meal;
  profileMap: Record<string, Profile>;
  expanded: boolean;
  onToggle: () => void;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div
        className="p-4 cursor-pointer flex items-start justify-between"
        onClick={onToggle}
      >
        <div className="flex-1">
          <span className="text-xs font-medium uppercase text-muted-foreground">
            {meal.meal_type}
          </span>
          <h3 className="font-semibold mt-0.5">{meal.name}</h3>
          {meal.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {meal.description}
            </p>
          )}
          <div className="flex flex-wrap gap-2 mt-2">
            {meal.portions.map((portion) => {
              const profile = profileMap[portion.profile_id];
              return (
                <span
                  key={portion.id}
                  className="inline-flex items-center gap-1 bg-muted rounded-full px-2.5 py-1 text-xs"
                >
                  <span className="font-medium">
                    {profile?.name ?? "Unknown"}
                  </span>
                  <span className="text-muted-foreground">
                    {portion.calories}kcal
                  </span>
                </span>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-1 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRegenerate();
            }}
            disabled={regenerating}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
            title="Regenerate this meal"
          >
            {regenerating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border p-4 space-y-4">
          {(meal.prep_time_min || meal.cook_time_min) && (
            <div className="flex gap-4 text-sm text-muted-foreground">
              {meal.prep_time_min && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Prep: {meal.prep_time_min}min
                </span>
              )}
              {meal.cook_time_min && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Cook: {meal.cook_time_min}min
                </span>
              )}
            </div>
          )}

          {/* Macros per profile */}
          <div>
            <h4 className="text-sm font-medium mb-2">Portions & Macros</h4>
            <div className="space-y-2">
              {meal.portions.map((portion) => {
                const profile = profileMap[portion.profile_id];
                return (
                  <div
                    key={portion.id}
                    className="bg-muted rounded-lg p-3 text-sm"
                  >
                    <div className="font-medium mb-1">
                      {profile?.name ?? "Unknown"} - {portion.serving_size}
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div>
                        <span className="text-muted-foreground">Cal</span>
                        <p className="font-semibold">{portion.calories}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Protein</span>
                        <p className="font-semibold">{portion.protein_g}g</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Carbs</span>
                        <p className="font-semibold">{portion.carbs_g}g</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Fat</span>
                        <p className="font-semibold">{portion.fat_g}g</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Ingredients */}
          {meal.ingredients.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Ingredients</h4>
              <ul className="text-sm space-y-1">
                {meal.ingredients.map((ing) => (
                  <li key={ing.id} className="flex justify-between">
                    <span>{ing.name}</span>
                    <span className="text-muted-foreground">
                      {ing.quantity}
                      {ing.unit ? ` ${ing.unit}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recipe steps */}
          {meal.recipe_steps.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Recipe</h4>
              <ol className="text-sm space-y-2 list-decimal list-inside">
                {meal.recipe_steps.map((step, i) => (
                  <li key={i} className="text-muted-foreground">
                    <span className="text-foreground">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
