import { Routes, Route, Navigate } from "react-router-dom";
import { tokens } from "./api/tokens";
import AppLayout from "./components/AppLayout";
import RequireNoPairs from "./components/RequireNoPairs";

import WelcomePage from "./pages/WelcomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import OnboardingPage from "./pages/OnboardingPage";
import AddPairPage from "./pages/AddPairPage";
import DashboardPage from "./pages/DashboardPage";
import StudyPage from "./pages/StudyPage";
import StudyHomePage from "./pages/StudyHomePage";
import SourcesPage from "./pages/DecksPage";
import SourceDetailPage from "./pages/DeckDetailPage";
import LibraryPage from "./pages/library/LibraryPage";
import LibraryDeckDetailPage from "./pages/library/LibraryDeckDetailPage";
import ProfilePage from "./pages/ProfilePage";
import ProgressPage from "./pages/ProgressPage";

function RequireAuth({ children }) {
  const authed = !!tokens.getAccess();
  if (!authed) return <Navigate to="/login" replace />;
  return children;
}

function RequireGuest({ children }) {
  const authed = !!tokens.getAccess();
  if (authed) return <Navigate to="/app" replace />;
  return children;
}

function LegacyDeckRouteRedirect() {
  const path = window.location.pathname;
  if (path.startsWith("/app/decks/")) {
    return <Navigate to={path.replace("/app/decks/", "/app/sources/")} replace />;
  }
  return <Navigate to="/app/sources" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RequireGuest><WelcomePage /></RequireGuest>} />
      <Route path="/login" element={<RequireGuest><LoginPage /></RequireGuest>} />
      <Route path="/register" element={<RequireGuest><RegisterPage /></RequireGuest>} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route
          path="/onboarding"
          element={
            <RequireNoPairs>
              <OnboardingPage />
            </RequireNoPairs>
          }
        />
        <Route path="/app" element={<DashboardPage />} />
        <Route path="/app/pairs/new" element={<AddPairPage />} />
        <Route path="/app/sources" element={<SourcesPage />} />
        <Route path="/app/sources/:sourceId" element={<SourceDetailPage />} />
        <Route path="/app/decks" element={<Navigate to="/app/sources" replace />} />
        <Route path="/app/decks/:deckId" element={<LegacyDeckRouteRedirect />} />
        <Route path="/app/library" element={<LibraryPage />} />
        <Route path="/app/library/:deckId" element={<LibraryDeckDetailPage />} />
        <Route path="/app/profile" element={<ProfilePage />} />
        <Route path="/app/progress" element={<ProgressPage />} />
        <Route path="/app/study" element={<StudyHomePage />} />
        <Route path="/app/study/:deckId" element={<StudyPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
