import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InventoryPage from "@/pages/InventoryPage";
import { mockInventoryItems } from "./mocks";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/api/client";
const mockedApi = vi.mocked(api);

function renderInventory() {
  return render(
    <MemoryRouter initialEntries={["/inventory"]}>
      <InventoryPage />
    </MemoryRouter>,
  );
}

describe("InventoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner initially", () => {
    mockedApi.get.mockImplementation(() => new Promise(() => {}));
    renderInventory();
    expect(document.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows empty state when no items", async () => {
    mockedApi.get.mockResolvedValue([]);
    renderInventory();
    await waitFor(() => {
      expect(screen.getByText(/No hay productos en nevera/)).toBeTruthy();
    });
  });

  it("shows inventory items grouped by category", async () => {
    mockedApi.get.mockResolvedValue(mockInventoryItems);
    renderInventory();
    await waitFor(() => {
      expect(screen.getByText("Pollo")).toBeTruthy();
      expect(screen.getByText("Brócoli")).toBeTruthy();
    });
  });

  it("switches between fridge and freezer tabs", async () => {
    mockedApi.get.mockResolvedValue(mockInventoryItems);
    renderInventory();

    await waitFor(() => {
      expect(screen.getByText("Pollo")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByText(/Congelador/));

    await waitFor(() => {
      expect(screen.getByText("Helado")).toBeTruthy();
      expect(screen.queryByText("Pollo")).toBeFalsy();
    });
  });

  it("opens create form when clicking plus button", async () => {
    mockedApi.get.mockResolvedValue([]);
    renderInventory();

    await waitFor(() => {
      expect(screen.getByText("Inventario")).toBeTruthy();
    });

    const user = userEvent.setup();
    const addButton = document.querySelector("button svg.lucide-plus")?.closest("button");
    expect(addButton).toBeTruthy();
    await user.click(addButton!);

    await waitFor(() => {
      expect(screen.getByText("Nuevo producto")).toBeTruthy();
    });
  });

  it("creates a new item via form", async () => {
    mockedApi.get.mockResolvedValue([]);
    mockedApi.post.mockResolvedValue({
      id: "new1",
      name: "Leche",
      quantity: null,
      unit: null,
      category: "other",
      storage_location: "fridge",
      created_at: "2026-03-10T10:00:00",
    });
    renderInventory();

    await waitFor(() => {
      expect(screen.getByText("Inventario")).toBeTruthy();
    });

    const user = userEvent.setup();
    const addButton = document.querySelector("button svg.lucide-plus")?.closest("button");
    await user.click(addButton!);

    await waitFor(() => {
      expect(screen.getByText("Nuevo producto")).toBeTruthy();
    });

    const nameInput = screen.getByPlaceholderText(/Pollo, Leche/);
    await user.type(nameInput, "Leche");
    await user.click(screen.getByText("Guardar"));

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith("/inventory", expect.objectContaining({ name: "Leche" }));
    });
  });
});
