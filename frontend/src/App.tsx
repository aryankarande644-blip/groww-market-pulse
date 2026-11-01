import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import { RequireAuth, RequireOnboarding, RedirectIfAuthed } from "./components/RouteGuards";

import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { MarketPulsePage } from "./pages/MarketPulsePage";
import { WatchlistManagementPage } from "./pages/WatchlistManagementPage";
import { StockSearchPage } from "./pages/StockSearchPage";
import { PreferencesPage } from "./pages/PreferencesPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<RedirectIfAuthed><LoginPage /></RedirectIfAuthed>} />
          <Route path="/register" element={<RedirectIfAuthed><RegisterPage /></RedirectIfAuthed>} />
          <Route path="/onboarding" element={<RequireOnboarding><OnboardingPage /></RequireOnboarding>} />

          <Route path="/pulse" element={<RequireAuth><MarketPulsePage /></RequireAuth>} />
          <Route path="/watchlist" element={<RequireAuth><WatchlistManagementPage /></RequireAuth>} />
          <Route path="/search" element={<RequireAuth><StockSearchPage /></RequireAuth>} />
          <Route path="/preferences" element={<RequireAuth><PreferencesPage /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />

          <Route path="*" element={<LandingPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
