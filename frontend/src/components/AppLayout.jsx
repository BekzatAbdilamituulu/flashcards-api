import { NavLink, Outlet } from "react-router-dom";
import PairSwitcher from "./PairSwitcher";
import BottomNavigation from "./BottomNavigation";

function sideLinkClass({ isActive }) {
  const base =
    "rounded-xl px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-0";
  return isActive
    ? `${base} bg-black text-white`
    : `${base} text-gray-700 hover:bg-gray-100`;
}

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500/15 via-blue-600/10 to-purple-600/15 text-black">
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

        </aside>

        <main className="flex-1 p-4 pb-24 md:p-6 md:pb-6">
          <div className="mx-auto w-full max-w-md space-y-4 md:max-w-5xl">
            <PairSwitcher />
            <Outlet />
          </div>
        </main>
      </div>

      <BottomNavigation
        items={[
          { to: "/app", end: true, label: "Dashboard", ariaLabel: "Dashboard" },
          { to: "/app/decks", label: "Sources", ariaLabel: "Sources" },
          { to: "/app/progress", label: "Progress", ariaLabel: "Progress" },
          { to: "/app/library", label: "Library", ariaLabel: "Library" },
          { to: "/app/profile", label: "Profile", ariaLabel: "Profile" },
        ]}
      />
    </div>
  );
}
