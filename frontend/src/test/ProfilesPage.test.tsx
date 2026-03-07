import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProfilesPage from "@/pages/ProfilesPage";
import { mockProfiles } from "./mocks";

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

function renderProfiles() {
  return render(
    <MemoryRouter>
      <ProfilesPage />
    </MemoryRouter>,
  );
}

describe("ProfilesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading then profiles", async () => {
    mockedApi.get.mockResolvedValue(mockProfiles);

    renderProfiles();
    await waitFor(() => {
      expect(screen.getByText("Alonso")).toBeTruthy();
      expect(screen.getByText("Maria")).toBeTruthy();
    });
  });

  it("shows empty state when no profiles", async () => {
    mockedApi.get.mockResolvedValue([]);

    renderProfiles();
    await waitFor(() => {
      expect(screen.getByText(/No profiles yet/)).toBeTruthy();
    });
  });

  it("opens create profile modal", async () => {
    mockedApi.get.mockResolvedValue([]);

    renderProfiles();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /add/i })).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(screen.getByText("New Profile")).toBeTruthy();
    });
  });

  it("displays profile macro targets", async () => {
    mockedApi.get.mockResolvedValue(mockProfiles);

    renderProfiles();
    await waitFor(() => {
      expect(screen.getByText("2800")).toBeTruthy(); // Alonso calorie target
      expect(screen.getByText("1800")).toBeTruthy(); // Maria calorie target
    });
  });
});
