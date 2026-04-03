import { NavLink } from "react-router-dom";

function bottomLinkClass({ isActive }) {
  const base =
    "flex-1 rounded-2xl px-1 py-2 text-center text-[10px] leading-tight font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-0";
  return isActive
    ? `${base} bg-gradient-to-r from-indigo-500 to-blue-600 text-white shadow-sm`
    : `${base} text-gray-700 hover:bg-gray-100`;
}

function gridColsClass(itemsLength) {
  if (itemsLength === 4) return "grid-cols-4";
  if (itemsLength === 5) return "grid-cols-5";
  return "grid-cols-5";
}

export default function BottomNavigation({ items, className = "" }) {
  const normalizedItems = Array.isArray(items) ? items : [];

  return (
    <nav
      className={[
        "fixed inset-x-0 bottom-0 z-30 bg-transparent px-3 pb-3 md:hidden",
        className,
      ]
        .join(" ")
        .trim()}
    >
      <div
        className={[
          "mx-auto w-full max-w-md gap-2 rounded-3xl border border-gray-100 bg-white px-2 py-2 shadow-xl",
          "grid",
          gridColsClass(normalizedItems.length),
        ].join(" ")}
      >
        {normalizedItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            aria-label={item.ariaLabel || item.label}
            className={bottomLinkClass}
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

