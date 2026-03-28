import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ShoppingListPage from "@/pages/ShoppingListPage";
import { mockShoppingList } from "./mocks";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", email: "test@example.com", profile_id: "p1", profile_name: "Test" },
    isLoading: false,
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { api } from "@/api/client";
const mockedApi = vi.mocked(api);

function renderShoppingList() {
  return render(
    <MemoryRouter initialEntries={["/shopping/mp1"]}>
      <Routes>
        <Route path="/shopping/:id" element={<ShoppingListPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ShoppingListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows shopping list categories", async () => {
    mockedApi.get.mockResolvedValue(mockShoppingList);

    renderShoppingList();
    await waitFor(() => {
      expect(screen.getByText("Chicken Breast")).toBeTruthy();
      expect(screen.getByText("Salmon Fillet")).toBeTruthy();
      expect(screen.getByText("Mixed Greens")).toBeTruthy();
    });
  });

  it("shows category headers", async () => {
    mockedApi.get.mockResolvedValue(mockShoppingList);

    renderShoppingList();
    await waitFor(() => {
      expect(screen.getByText("Protein")).toBeTruthy();
      expect(screen.getByText("Produce")).toBeTruthy();
      expect(screen.getByText("Grains")).toBeTruthy();
    });
  });
});
