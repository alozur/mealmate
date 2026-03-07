import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { api } from "@/api/client";
import type { ShoppingList } from "@/types";

const CATEGORY_LABELS: Record<string, string> = {
  produce: "Produce",
  protein: "Protein",
  dairy: "Dairy",
  grains: "Grains",
  pantry: "Pantry",
  spices: "Spices",
  frozen: "Frozen",
  beverages: "Beverages",
  condiments: "Condiments",
};

export default function ShoppingListPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [shoppingList, setShoppingList] = useState<ShoppingList | null>(null);
  const [loading, setLoading] = useState(true);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    if (!id) return;
    api
      .get<ShoppingList>(`/meal-plans/${id}/shopping-list`)
      .then(setShoppingList)
      .catch(() => navigate("/dashboard"))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const toggleCheck = (itemKey: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(itemKey)) next.delete(itemKey);
      else next.add(itemKey);
      return next;
    });
  };

  const toggleCategory = (category: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  if (loading || !shoppingList) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const categories = Object.entries(shoppingList.categories);

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(-1)} className="p-1">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-bold">Shopping List</h1>
      </div>

      {categories.length === 0 ? (
        <p className="text-center text-muted-foreground py-8">
          No ingredients found
        </p>
      ) : (
        <div className="space-y-4">
          {categories.map(([category, items]) => {
            const isCollapsed = collapsedCategories.has(category);
            const checkedCount = items.filter((item) =>
              checked.has(`${category}-${item.name}`),
            ).length;

            return (
              <div
                key={category}
                className="bg-card border border-border rounded-xl overflow-hidden"
              >
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center justify-between p-4"
                >
                  <div className="flex items-center gap-2">
                    <h2 className="font-semibold capitalize">
                      {CATEGORY_LABELS[category] ?? category}
                    </h2>
                    <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">
                      {checkedCount}/{items.length}
                    </span>
                  </div>
                  {isCollapsed ? (
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>

                {!isCollapsed && (
                  <div className="border-t border-border">
                    {items.map((item) => {
                      const key = `${category}-${item.name}`;
                      const isChecked = checked.has(key);
                      return (
                        <div
                          key={key}
                          onClick={() => toggleCheck(key)}
                          className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-b-0 cursor-pointer hover:bg-muted/50 transition-colors"
                        >
                          <div
                            className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                              isChecked
                                ? "bg-primary border-primary"
                                : "border-border"
                            }`}
                          >
                            {isChecked && (
                              <Check className="w-3 h-3 text-primary-foreground" />
                            )}
                          </div>
                          <span
                            className={`flex-1 ${isChecked ? "line-through text-muted-foreground" : ""}`}
                          >
                            {item.name}
                          </span>
                          <span className="text-sm text-muted-foreground">
                            {item.total_quantity}
                            {item.unit ? ` ${item.unit}` : ""}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
