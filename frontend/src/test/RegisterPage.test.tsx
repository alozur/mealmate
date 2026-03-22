import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.name = "ApiError";
    }
  },
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { useAuth } from "@/contexts/AuthContext";
import RegisterPage from "@/pages/RegisterPage";

const mockedUseAuth = vi.mocked(useAuth);

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <RegisterPage />
    </MemoryRouter>,
  );
}

describe("RegisterPage", () => {
  const mockRegister = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      login: vi.fn(),
      register: mockRegister,
      logout: vi.fn(),
    });
  });

  it("renders register form with invite code field", () => {
    renderRegister();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByLabelText("Invite Code")).toBeTruthy();
    expect(screen.getByText("Create account")).toBeTruthy();
  });

  it("calls register on form submit", async () => {
    mockRegister.mockResolvedValue(undefined);
    renderRegister();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "securepass123");
    await user.type(screen.getByLabelText("Invite Code"), "my-secret");
    await user.click(screen.getByText("Create account"));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        "new@example.com",
        "securepass123",
        "my-secret",
      );
    });
  });

  it("shows error on failed registration", async () => {
    const { ApiError } = await import("@/api/client");
    mockRegister.mockRejectedValue(new ApiError(403, "Invalid invite code"));
    renderRegister();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "securepass123");
    await user.type(screen.getByLabelText("Invite Code"), "wrong");
    await user.click(screen.getByText("Create account"));

    await waitFor(() => {
      expect(screen.getByText("Invalid invite code")).toBeTruthy();
    });
  });

  it("has link to login page", () => {
    renderRegister();
    expect(screen.getByText("Sign in")).toBeTruthy();
  });
});
