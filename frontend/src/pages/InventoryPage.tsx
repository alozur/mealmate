import { useEffect, useRef, useState } from "react";
import { Edit, Loader2, Plus, Trash2 } from "lucide-react";
import { api } from "@/api/client";
import type { InventoryItem } from "@/types";
import { INVENTORY_CATEGORY_LABELS, STORAGE_LABELS } from "@/types";

const CATEGORY_OPTIONS = Object.entries(INVENTORY_CATEGORY_LABELS).map(
  ([value, label]) => ({ value, label }),
);

const UNIT_OPTIONS = [
  "",
  "g",
  "kg",
  "ml",
  "L",
  "uds",
  "latas",
  "paquetes",
  "bolsas",
];

interface ItemForm {
  name: string;
  quantity: string;
  unit: string;
  category: string;
  storage_location: string;
}

const emptyForm: ItemForm = {
  name: "",
  quantity: "",
  unit: "",
  category: "other",
  storage_location: "fridge",
};

function SwipeableItem({
  children,
  onEdit,
  onDelete,
}: {
  children: React.ReactNode;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const startX = useRef(0);
  const currentX = useRef(0);
  const [offset, setOffset] = useState(0);
  const [swiped, setSwiped] = useState(false);
  const ACTION_WIDTH = 120;

  const handleTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
    currentX.current = offset;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const diff = e.touches[0].clientX - startX.current;
    const newOffset = Math.max(
      -ACTION_WIDTH,
      Math.min(0, currentX.current + diff),
    );
    setOffset(newOffset);
  };

  const handleTouchEnd = () => {
    if (offset < -ACTION_WIDTH / 2) {
      setOffset(-ACTION_WIDTH);
      setSwiped(true);
    } else {
      setOffset(0);
      setSwiped(false);
    }
  };

  const close = () => {
    setOffset(0);
    setSwiped(false);
  };

  return (
    <div className="relative overflow-hidden rounded-xl">
      <div className="absolute right-0 top-0 bottom-0 flex">
        <button
          onClick={() => {
            close();
            onEdit();
          }}
          className="w-[60px] flex items-center justify-center bg-blue-500 text-white"
        >
          <Edit className="w-5 h-5" />
        </button>
        <button
          onClick={() => {
            close();
            onDelete();
          }}
          className="w-[60px] flex items-center justify-center bg-red-500 text-white"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>
      <div
        ref={containerRef}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onClick={() => swiped && close()}
        style={{
          transform: `translateX(${offset}px)`,
          transition: offset === 0 || offset === -ACTION_WIDTH ? "transform 0.2s ease" : "none",
        }}
        className="relative bg-card border border-border rounded-xl"
      >
        {children}
      </div>
    </div>
  );
}

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"fridge" | "freezer">("fridge");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ItemForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchItems = () => {
    api
      .get<InventoryItem[]>("/inventory")
      .then(setItems)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const filteredItems = items.filter(
    (item) => item.storage_location === activeTab,
  );

  const groupedByCategory = filteredItems.reduce<
    Record<string, InventoryItem[]>
  >((acc, item) => {
    const cat = item.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  const openCreate = () => {
    setForm({ ...emptyForm, storage_location: activeTab });
    setEditingId(null);
    setShowForm(true);
  };

  const openEdit = (item: InventoryItem) => {
    setForm({
      name: item.name,
      quantity: item.quantity ?? "",
      unit: item.unit ?? "",
      category: item.category,
      storage_location: item.storage_location,
    });
    setEditingId(item.id);
    setShowForm(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        quantity: form.quantity || null,
        unit: form.unit || null,
        category: form.category,
        storage_location: form.storage_location,
      };
      if (editingId) {
        await api.put(`/inventory/${editingId}`, payload);
      } else {
        await api.post("/inventory", payload);
      }
      setShowForm(false);
      fetchItems();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/inventory/${id}`);
    fetchItems();
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
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Inventario</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-1 bg-primary text-primary-foreground rounded-lg px-3 py-2 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Storage location tabs */}
      <div className="flex gap-1 bg-muted rounded-xl p-1 mb-5">
        {(["fridge", "freezer"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground"
            }`}
          >
            {STORAGE_LABELS[tab]}
            <span className="ml-1.5 text-xs opacity-60">
              ({items.filter((i) => i.storage_location === tab).length})
            </span>
          </button>
        ))}
      </div>

      {filteredItems.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p className="mb-2">
            No hay productos en {STORAGE_LABELS[activeTab].toLowerCase()}
          </p>
          <p className="text-sm">
            Pulsa + para añadir productos
          </p>
        </div>
      )}

      {/* Items grouped by category */}
      <div className="space-y-5">
        {Object.entries(groupedByCategory).map(([category, catItems]) => (
          <div key={category}>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {INVENTORY_CATEGORY_LABELS[category] ?? category}
            </h3>
            <div className="space-y-2">
              {catItems.map((item) => (
                <SwipeableItem
                  key={item.id}
                  onEdit={() => openEdit(item)}
                  onDelete={() => handleDelete(item.id)}
                >
                  <div className="p-3 flex items-center justify-between">
                    <span className="font-medium">{item.name}</span>
                    {(item.quantity || item.unit) && (
                      <span className="text-sm text-muted-foreground">
                        {item.quantity}
                        {item.unit ? ` ${item.unit}` : ""}
                      </span>
                    )}
                  </div>
                </SwipeableItem>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Add/Edit Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center">
          <div className="bg-card w-full max-w-lg rounded-t-2xl sm:rounded-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">
              {editingId ? "Editar producto" : "Nuevo producto"}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Nombre</label>
                <input
                  value={form.name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, name: e.target.value }))
                  }
                  className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  placeholder="ej. Pollo, Leche, Brócoli..."
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">Cantidad</label>
                  <input
                    value={form.quantity}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, quantity: e.target.value }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                    placeholder="ej. 500"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Unidad</label>
                  <select
                    value={form.unit}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, unit: e.target.value }))
                    }
                    className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                  >
                    {UNIT_OPTIONS.map((u) => (
                      <option key={u} value={u}>
                        {u || "—"}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">Categoría</label>
                <select
                  value={form.category}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, category: e.target.value }))
                  }
                  className="w-full mt-1 px-3 py-2 border border-input rounded-lg bg-background"
                >
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Ubicación</label>
                <div className="flex gap-2 mt-1">
                  {(["fridge", "freezer"] as const).map((loc) => (
                    <button
                      key={loc}
                      onClick={() =>
                        setForm((f) => ({ ...f, storage_location: loc }))
                      }
                      className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                        form.storage_location === loc
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-background border-border hover:border-primary/50"
                      }`}
                    >
                      {STORAGE_LABELS[loc]}
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
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name}
                className="flex-1 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium disabled:opacity-50"
              >
                {saving ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
