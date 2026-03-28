import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { api } from "@/api/client";
import type { UserMe } from "@/types";

interface AuthContextType {
  user: UserMe | null;
  isLoading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<UserMe>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // best effort
    }
    setUser(null);
    window.location.href = "https://auth.zurera.cloud/logout";
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
