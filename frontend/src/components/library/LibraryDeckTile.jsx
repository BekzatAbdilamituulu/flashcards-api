function getDeckInitials(name) {
  if (!name) return "LP";
  const words = name.trim().split(/\s+/).slice(0, 2);
  return words.map((w) => w[0]?.toUpperCase() || "").join("") || "LP";
}

function difficultyBadgeClass(difficulty) {
  const key = String(difficulty || "").toLowerCase();
  if (key === "easy") return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (key === "moderate" || key === "medium") return "bg-sky-100 text-sky-700 border-sky-200";
  if (key === "hard") return "bg-rose-100 text-rose-700 border-rose-200";
  return "bg-stone-100 text-stone-600 border-stone-200";
}

export default function LibraryDeckTile({ deck, onClick }) {
  const cardsCount = deck?.cards_count ?? deck?.cardsCount ?? "-";

  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full overflow-hidden rounded-2xl border border-stone-200 bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-stone-100">
        {deck?.cover_image_url ? (
          <img
            src={deck.cover_image_url}
            alt={deck.name || "Library source"}
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-100 via-stone-100 to-orange-100">
            <span className="text-2xl font-semibold tracking-wide text-stone-600">
              {getDeckInitials(deck?.name)}
            </span>
          </div>
        )}

        {deck?.difficulty ? (
          <span
            className={`absolute right-2 top-2 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${difficultyBadgeClass(deck.difficulty)}`}
          >
            {deck.difficulty}
          </span>
        ) : null}
      </div>

      <div className="space-y-2 p-3">
        <h3 className="min-h-10 overflow-hidden text-sm font-semibold text-stone-900">
          {deck?.name || "Untitled collection"}
        </h3>

        <div className="flex items-center justify-between gap-2 text-xs text-stone-500">
          <span>{cardsCount} words</span>
          {deck?.rating != null ? <span>{Number(deck.rating).toFixed(1)} rating</span> : null}
        </div>
      </div>
    </button>
  );
}
