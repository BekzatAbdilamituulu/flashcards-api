import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { AuthApi } from "../api/endpoints";
import { tokens } from "../api/tokens";
import PairSwitcher from "./PairSwitcher";

function sideLinkClass({ isActive }) {
  const base = "rounded-xl px-3 py-2 text-sm font-medium transition-colors";
  return isActive
    ? `${base} bg-black text-white`
    : `${base} text-gray-700 hover:bg-gray-100`;
}

function bottomLinkClass({ isActive }) {
  const base = "flex-1 rounded-xl px-2 py-2 text-center text-xs font-medium";
  return isActive ? `${base} bg-black text-white` : `${base} text-gray-700`;
}

export default function AppLayout() {
  const nav = useNavigate();

  async function onLogout() {
    const refresh = tokens.getRefresh();
    try {
      if (refresh) await AuthApi.logout(refresh);
    } catch {
      // best-effort server logout
    } finally {
      tokens.clear();
      nav("/login", { replace: true });
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 text-black">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col md:max-w-7xl md:flex-row">
        <aside className="hidden w-60 border-r border-stone-200 bg-white p-6 md:flex md:flex-col">
          <div className="text-2xl font-bold">Cortex Reader</div>

          <nav className="mt-8 flex flex-col gap-2">
            <NavLink to="/app" end className={sideLinkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/app/decks" className={sideLinkClass}>
              My Sources
            </NavLink>
            <NavLink to="/app/library" className={sideLinkClass}>
              Library
            </NavLink>
            <NavLink to="/app/study" className={sideLinkClass}>
              Reading Review
            </NavLink>
            <NavLink to="/app/progress" className={sideLinkClass}>
              Progress
            </NavLink>
            <NavLink to="/app/profile" className={sideLinkClass}>
              Profile
            </NavLink>
          </nav>

          <button
            onClick={onLogout}
            className="mt-auto min-h-11 w-full rounded-xl border border-gray-300 px-4 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Logout
          </button>
        </aside>

        <main className="flex-1 p-4 pb-24 md:p-6 md:pb-6">
          <div className="mx-auto w-full max-w-md space-y-4 md:max-w-5xl">
            <PairSwitcher />
            <Outlet />
          </div>
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 border-t border-stone-200 bg-white/95 p-3 backdrop-blur md:hidden">
        <div className="mx-auto flex w-full max-w-md gap-2">
          <NavLink to="/app" end className={bottomLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/app/decks" className={bottomLinkClass}>
            Sources
          </NavLink>
          <NavLink to="/app/library" className={bottomLinkClass}>
            Library
          </NavLink>
          <NavLink to="/app/profile" className={bottomLinkClass}>
            Profile
          </NavLink>
          <button
            onClick={onLogout}
            className="flex-1 rounded-xl px-2 py-2 text-center text-xs font-medium text-gray-700"
          >
            Logout
          </button>
        </div>
      </nav>
    </div>
  );
}
