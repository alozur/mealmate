import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarDays, ChefHat, Loader2, ShoppingCart, Plus, Users } from "lucide-react";
import { api } from "@/api/client";
import type { MealPlan, MealPlanDetail, Profile } from "@/types";
import { DAY_NAMES } from "@/types";

export default function Dashboard() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<MealPlan[]>("/meal-plans"),
      api.get<Profile[]>("/profiles"),
    ])
      .then(([p, pr]) => {
        setPlans(p);
        setProfiles(pr);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    if (profiles.length === 0) {
      setError("Please create at least one profile first.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const plan = await api.post<MealPlanDetail>("/meal-plans/generate", {});
      navigate(`/meal-plans/${plan.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate plan");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <ChefHat className="w-8 h-8 text-primary" />
        <h1 className="text-2xl font-bold">MealMate</h1>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive rounded-lg p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      <button
        onClick={handleGenerate}
        disabled={generating}
        className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-xl py-4 px-6 font-semibold text-lg hover:bg-primary/90 transition-colors disabled:opacity-50 mb-6"
      >
        {generating ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Generating meal plan...
          </>
        ) : (
          <>
            <Plus className="w-5 h-5" />
            Generate New Plan
          </>
        )}
      </button>

      {profiles.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="mb-2">No profiles yet</p>
          <button
            onClick={() => navigate("/profiles")}
            className="text-primary underline"
          >
            Create your first profile
          </button>
        </div>
      )}

      {plans.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Your Meal Plans</h2>
          <div className="space-y-3">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="bg-card border border-border rounded-xl p-4 cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => navigate(`/meal-plans/${plan.id}`)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CalendarDays className="w-5 h-5 text-primary" />
                    <div>
                      <p className="font-medium">
                        Week of {new Date(plan.week_start).toLocaleDateString()}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {plan.week_start} to {plan.week_end}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/shopping/${plan.id}`);
                    }}
                    className="p-2 rounded-lg hover:bg-muted transition-colors"
                  >
                    <ShoppingCart className="w-5 h-5 text-muted-foreground" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

