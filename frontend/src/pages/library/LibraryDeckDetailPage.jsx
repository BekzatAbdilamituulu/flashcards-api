import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { LibraryApi } from "../../api/endpoints";
import Button from "../../components/Button";
import Card from "../../components/Card";

const PAGE_LIMIT = 50;

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function difficultyBadgeClass(difficulty) {
  const key = String(difficulty || "").toLowerCase();
  if (key === "easy") return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (key === "moderate" || key === "medium") return "bg-sky-100 text-sky-700 border-sky-200";
  if (key === "hard") return "bg-rose-100 text-rose-700 border-rose-200";
  return "bg-stone-100 text-stone-600 border-stone-200";
}

function toDeckItems(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

function extractImportCounts(data, fallbackImported = 0, fallbackSkipped = 0) {
  if (typeof data?.imported_count === "number" || typeof data?.skipped_count === "number") {
    return {
      imported: data?.imported_count ?? 0,
      skipped: data?.skipped_count ?? 0,
    };
  }

  if (Array.isArray(data?.results)) {
    const imported = data.results.filter((r) => r?.imported).length;
    const skipped = data.results.filter((r) => r?.skipped).length;
    return { imported, skipped };
  }

  if (data?.skipped === true) {
    return { imported: 0, skipped: 1 };
  }

  return { imported: fallbackImported, skipped: fallbackSkipped };
}

function buildImportToast(imported, skipped) {
  if (skipped > 0) {
    return `Added ${imported} ${imported === 1 ? "word" : "words"} • ${skipped} already existed`;
  }
  return "Added to your Main Deck";
}

export default function LibraryDeckDetailPage() {
  const { deckId } = useParams();
  const location = useLocation();
  const id = Number(deckId);

  const [deck, setDeck] = useState(location.state?.deck || null);
  const [cardsPage, setCardsPage] = useState(null);
  const [offset, setOffset] = useState(0);

  const [loadingDeck, setLoadingDeck] = useState(true);
  const [loadingCards, setLoadingCards] = useState(true);
  const [error, setError] = useState("");
  const [cardsError, setCardsError] = useState("");

  const [selectedIds, setSelectedIds] = useState([]);
  const [importingSelected, setImportingSelected] = useState(false);
  const [importingCardId, setImportingCardId] = useState(null);
  const [toast, setToast] = useState("");

  const cards = useMemo(() => cardsPage?.items ?? [], [cardsPage]);
  const meta = cardsPage?.meta;
  const visibleIds = useMemo(() => cards.map((c) => c.id), [cards]);
  const isImportingAny = importingSelected || importingCardId != null;

  useEffect(() => {
    setSelectedIds((prev) => prev.filter((idValue) => visibleIds.includes(idValue)));
  }, [visibleIds]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  async function loadDeck() {
    setLoadingDeck(true);
    setError("");

    try {
      if (!(id > 0)) {
        setError("Invalid reading pack id.");
        setDeck(null);
        return;
      }

      if (location.state?.deck?.id && Number(location.state.deck.id) === id) {
        setDeck(location.state.deck);
      }

      const res = await LibraryApi.listDecks();
      const found = toDeckItems(res.data).find((item) => Number(item.id) === id);
      if (found) {
        setDeck(found);
      } else if (!location.state?.deck) {
        setDeck({ id, name: `Reading pack #${id}` });
      }
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoadingDeck(false);
    }
  }

  async function loadCards(nextOffset = offset) {
    setLoadingCards(true);
    setCardsError("");

    try {
      const res = await LibraryApi.listDeckCards(id, PAGE_LIMIT, nextOffset);
      if (Array.isArray(res.data)) {
        setCardsPage({
          items: res.data,
          meta: {
            limit: PAGE_LIMIT,
            offset: nextOffset,
            total: res.data.length,
            has_more: false,
          },
        });
      } else {
        setCardsPage(res.data);
      }
      setOffset(nextOffset);
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setLoadingCards(false);
    }
  }

  useEffect(() => {
    async function loadAll() {
      await loadDeck();
      await loadCards(0);
    }

    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function toggleSelected(cardId) {
    setSelectedIds((prev) =>
      prev.includes(cardId) ? prev.filter((idValue) => idValue !== cardId) : [...prev, cardId]
    );
  }

  function selectAllVisible() {
    setSelectedIds(visibleIds);
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  async function importOneCard(cardId) {
    setCardsError("");
    setImportingCardId(cardId);

    try {
      const res = await LibraryApi.importCard(cardId);
      const { imported, skipped } = extractImportCounts(res.data, 1, 0);
      setToast(buildImportToast(imported, skipped));
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setImportingCardId(null);
    }
  }

  async function importSelectedCards() {
    if (selectedIds.length === 0) return;

    setCardsError("");
    setImportingSelected(true);

    try {
      const res = await LibraryApi.importSelected(id, selectedIds);
      const { imported, skipped } = extractImportCounts(res.data, selectedIds.length, 0);
      setToast(buildImportToast(imported, skipped));
      setSelectedIds([]);
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setImportingSelected(false);
    }
  }

  return (
    <div className="space-y-4">
      <Link to="/app/library" className="text-sm text-stone-600 underline">
        Back to library
      </Link>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
        <div className="relative aspect-[5/2] w-full bg-stone-100">
          {deck?.cover_image_url ? (
            <img src={deck.cover_image_url} alt={deck?.name || "Library deck"} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-r from-amber-100 via-stone-100 to-orange-100 text-stone-600">
              <span className="text-sm font-semibold">Curated library set</span>
            </div>
          )}

          {deck?.difficulty ? (
            <span
              className={`absolute right-3 top-3 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase ${difficultyBadgeClass(deck.difficulty)}`}
            >
              {deck.difficulty}
            </span>
          ) : null}
        </div>

        <div className="space-y-2 p-4">
          <h1 className="text-2xl font-bold text-stone-900">
            {loadingDeck ? "Loading reading pack..." : deck?.name || `Reading pack #${id}`}
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-stone-600">
            <span>{deck?.cards_count ?? "-"} words</span>
            {deck?.rating != null ? <span>{Number(deck.rating).toFixed(1)} rating</span> : null}
          </div>
        </div>
      </div>

      {error ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
      ) : null}

      <Card className="space-y-3 border-stone-200 bg-white/95 p-4">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={selectAllVisible}
            disabled={loadingCards || cards.length === 0 || isImportingAny}
          >
            Select all visible
          </Button>
          <Button
            variant="secondary"
            onClick={clearSelection}
            disabled={selectedIds.length === 0 || isImportingAny}
          >
            Clear selection
          </Button>
          <Button
            variant="primary"
            onClick={importSelectedCards}
            disabled={selectedIds.length === 0 || loadingCards || isImportingAny}
          >
            {importingSelected ? "Importing..." : `Import selected (${selectedIds.length})`}
          </Button>
        </div>
        <p className="text-xs text-stone-500">Select one or many entries, then import to your Main Deck.</p>
      </Card>

      {cardsError ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{cardsError}</pre>
      ) : null}

      {loadingCards ? <p className="text-sm text-stone-500">Loading entries...</p> : null}

      {!loadingCards && cards.length === 0 ? (
        <Card className="border-stone-200 bg-white/95">
          <p className="text-sm text-stone-600">No entries in this reading pack yet.</p>
        </Card>
      ) : null}

      {!loadingCards
        ? cards.map((card) => {
            const checked = selectedIds.includes(card.id);
            const isThisCardImporting = importingCardId === card.id;

            return (
              <Card
                key={card.id}
                className={`space-y-3 border-stone-200 bg-white/95 p-4 ${checked ? "ring-2 ring-amber-300" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <label className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSelected(card.id)}
                      disabled={isImportingAny}
                      className="mt-1 h-4 w-4 rounded border-stone-300"
                    />
                    <span className="text-sm text-stone-700">Select</span>
                  </label>

                  <Button
                    variant="secondary"
                    className="min-h-9 px-3 py-1.5 text-xs"
                    onClick={() => importOneCard(card.id)}
                    disabled={isImportingAny}
                  >
                    {isThisCardImporting ? "Importing..." : "Import"}
                  </Button>
                </div>

                <div>
                  <p className="text-xs text-stone-500">Word / entry</p>
                  <p className="text-stone-900">{card.front || "-"}</p>
                </div>

                <div>
                  <p className="text-xs text-stone-500">Translation / meaning</p>
                  <p className="text-stone-900">{card.back || "-"}</p>
                </div>

                {card.example_sentence ? (
                  <div>
                    <p className="text-xs text-stone-500">Source sentence</p>
                    <p className="text-stone-700">{card.example_sentence}</p>
                  </div>
                ) : null}
              </Card>
            );
          })
        : null}

      {meta ? (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <Button
            variant="secondary"
            onClick={() => loadCards(Math.max(0, offset - PAGE_LIMIT))}
            disabled={loadingCards || offset === 0 || isImportingAny}
          >
            Prev
          </Button>

          <p className="text-xs text-stone-500">
            {cards.length ? `${offset + 1}-${Math.min(offset + cards.length, meta.total)}` : "0"} of {meta.total}
          </p>

          <Button
            variant="secondary"
            onClick={() => loadCards(offset + PAGE_LIMIT)}
            disabled={loadingCards || !meta.has_more || isImportingAny}
          >
            Next
          </Button>
        </div>
      ) : null}

      {toast ? (
        <div className="fixed bottom-20 left-1/2 z-40 -translate-x-1/2 rounded-full bg-stone-900 px-4 py-2 text-xs font-medium text-white shadow-lg md:bottom-6">
          {toast}
        </div>
      ) : null}
    </div>
  );
}
