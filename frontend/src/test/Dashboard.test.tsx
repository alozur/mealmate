import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Dashboard from "@/pages/Dashboard";
import { mockProfiles, mockMealPlan } from "./mocks";

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

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner initially", () => {
    mockedApi.get.mockImplementation(() => new Promise(() => {}));
    renderDashboard();
    expect(document.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows generate button after loading", async () => {
    mockedApi.get.mockImplementation((endpoint: string) => {
      if (endpoint === "/meal-plans") return Promise.resolve([]);
      if (endpoint === "/profiles") return Promise.resolve(mockProfiles);
      return Promise.resolve([]);
    });

    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Generate New Plan")).toBeTruthy();
    });
  });

  it("shows existing meal plans", async () => {
    mockedApi.get.mockImplementation((endpoint: string) => {
      if (endpoint === "/meal-plans") return Promise.resolve([mockMealPlan]);
      if (endpoint === "/profiles") return Promise.resolve(mockProfiles);
      return Promise.resolve([]);
    });

    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Your Meal Plans")).toBeTruthy();
    });
  });

  it("shows prompt when no profiles exist", async () => {
    mockedApi.get.mockImplementation((endpoint: string) => {
      if (endpoint === "/meal-plans") return Promise.resolve([]);
      if (endpoint === "/profiles") return Promise.resolve([]);
      return Promise.resolve([]);
    });

    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("No profiles yet")).toBeTruthy();
    });
  });

  it("shows error when generation fails without profiles", async () => {
    mockedApi.get.mockImplementation((endpoint: string) => {
      if (endpoint === "/meal-plans") return Promise.resolve([]);
      if (endpoint === "/profiles") return Promise.resolve([]);
      return Promise.resolve([]);
    });

    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Generate New Plan")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Generate New Plan"));

    await waitFor(() => {
      expect(screen.getByText(/Please create at least one profile/)).toBeTruthy();
    });
  });
});
