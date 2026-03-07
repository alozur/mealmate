import { useEffect, useState } from "react";
import { ArrowLeft, Edit, Loader2, Plus, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api/client";
import type { Profile } from "@/types";
import { GOAL_LABELS } from "@/types";

const GOAL_OPTIONS = [
  { value: "muscle_gain", label: "Muscle Gain" },
  { value: "fat_loss", label: "Fat Loss" },
  { value: "maintenance", label: "Maintenance" },
  { value: "general_health", label: "General Health" },
];

const RESTRICTION_OPTIONS = [
  "vegetarian",
  "vegan",
  "gluten_free",
  "dairy_free",
  "no_pork",
  "no_shellfish",
  "nut_free",
  "low_sodium",
];

interface ProfileForm {
  name: string;
  goal: string;
  restrictions: string[];
  calorie_target: number;
  protein_target: number;
  carbs_target: number;
  fat_target: number;
}

const emptyForm: ProfileForm = {
  name: "",
  goal: "maintenance",
  restrictions: [],
  calorie_target: 2000,
  protein_target: 150,
  carbs_target: 200,
  fat_target: 70,
};

export default function ProfilesPage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchProfiles = () => {
    api
      .get<Profile[]>("/profiles")
      .then(setProfiles)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  const openCreate = () => {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(true);
  };

  const openEdit = (profile: Profile) => {
    setForm({
      name: profile.name,
      goal: profile.goal,
      restrictions: profile.restrictions,
      calorie_target: profile.calorie_target,
      protein_target: profile.protein_target,
      carbs_target: profile.carbs_target,
      fat_target: profile.fat_target,
    });
    setEditingId(profile.id);
    setShowForm(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editingId) {
        await api.put(`/profiles/${editingId}`, form);
      } else {
        await api.post("/profiles", form);
      }
      setShowForm(false);
      fetchProfiles();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/profiles/${id}`);
    fetchProfiles();
  };

  const toggleRestriction = (r: string) => {
    setForm((prev) => ({
      ...prev,
      restrictions: prev.restrictions.includes(r)
        ? prev.restrictions.filter((x) => x !== r)
        : [...prev.restrictions, r],
    }));
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">Profiles</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-1 bg-primary text-primary-foreground rounded-lg px-3 py-2 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>

      {profiles.length === 0 && !showForm && (
        <div className="text-center py-12 text-muted-foreground">
          <p className="mb-2">No profiles yet</p>
          <p className="text-sm">Add profiles to set fitness goals and dietary preferences</p>
        </div>
      )}

      <div className="space-y-3">
        {profiles.map((profile) => (
          <div
            key={profile.id}
            className="bg-card border border-border rounded-xl p-4"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{profile.name}</h3>
                <span className="text-sm text-primary">
                  {GOAL_LABELS[profile.goal] ?? profile.goal}
                </span>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => openEdit(profile)}
                  className="p-1.5 rounded-lg hover:bg-muted"
                >
                  <Edit className="w-4 h-4 text-muted-foreground" />
                </button>
                <button
                  onClick={() => handleDelete(profile.id)}
                  className="p-1.5 rounded-lg hover:bg-destructive/10"
                >
                  <Trash2 className="w-4 h-4 text-destructive" />
                </button>
              </div>
            </div>
            <div className="grid grid-cols-4 gap-2 mt-3 text-xs">
              <div className="bg-muted rounded-lg p-2 text-center">
                <span className="text-muted-foreground">Cal</span>
                <p className="font-semibold">{profile.calorie_target}</p>
              </div>
              <div className="bg-muted rounded-lg p-2 text-center">
                <span className="text-muted-foreground">Protein</span>
                <p className="font-semibold">{profile.protein_target}g</p>
              </div>
              <div className="bg-muted rounded-lg p-2 text-center">
                <span className="text-muted-foreground">Carbs</span>
                <p className="font-semibold">{profile.carbs_target}g</p>
              </div>
              <div className="bg-muted rounded-lg p-2 text-center">
                <span className="text-muted-foreground">Fat</span>
                <p className="font-semibold">{profile.fat_target}g</p>
              </div>
            </div>
            {profile.restrictions.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {profile.restrictions.map((r) => (
                  <span
                    key={r}
                    className="text-xs bg-secondary rounded-full px-2 py-0.5"
                  >
                    {r.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Profile Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center">
          <div className="bg-card w-full max-w-lg rounded-t-2xl sm:rounded-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">
              {editingId ? "Edit Profile" : "New Profile"}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name</label>
                <input
                  value={form.name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, name: e.target.value }))
                  }
                  className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  placeholder="e.g. Alonso"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Goal</label>
                <select
                  value={form.goal}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, goal: e.target.value }))
                  }
                  className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                >
                  {GOAL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">Calories</label>
                  <input
                    type="number"
                    value={form.calorie_target}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        calorie_target: Number(e.target.value),
                      }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Protein (g)</label>
                  <input
                    type="number"
                    value={form.protein_target}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        protein_target: Number(e.target.value),
                      }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Carbs (g)</label>
                  <input
                    type="number"
                    value={form.carbs_target}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        carbs_target: Number(e.target.value),
                      }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Fat (g)</label>
                  <input
                    type="number"
                    value={form.fat_target}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        fat_target: Number(e.target.value),
                      }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">
                  Dietary Restrictions
                </label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {RESTRICTION_OPTIONS.map((r) => (
                    <button
                      key={r}
                      onClick={() => toggleRestriction(r)}
                      className={`text-xs rounded-full px-3 py-1.5 border transition-colors ${
                        form.restrictions.includes(r)
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background border-border hover:border-primary/50"
                      }`}
                    >
                      {r.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 py-2.5 border border-border rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name}
                className="flex-1 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
