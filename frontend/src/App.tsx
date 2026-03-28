import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import AuthGuard from "./components/AuthGuard";
import BottomNav from "./components/BottomNav";
import Dashboard from "./pages/Dashboard";
import MealPlanPage from "./pages/MealPlanPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import ProfilesPage from "./pages/ProfilesPage";
import InventoryPage from "./pages/InventoryPage";

function AppRoutes() {
  return (
    <AuthGuard>
      <div className="min-h-screen pb-20 bg-background">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/meal-plans/:id" element={<MealPlanPage />} />
          <Route path="/shopping/:id" element={<ShoppingListPage />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
        </Routes>
        <BottomNav />
      </div>
    </AuthGuard>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
