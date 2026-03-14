import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LibraryApi } from "../../api/endpoints";
import LibraryDeckTile from "../../components/library/LibraryDeckTile";
import Input from "../../components/Input";
import Card from "../../components/Card";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function normalizeDecksPayload(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  return [];
}

export default function LibraryPage() {
  const nav = useNavigate();
  const [decks, setDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await LibraryApi.listDecks();
        setDecks(normalizeDecksPayload(res.data));
      } catch (e) {
        setError(extractError(e));
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const filteredDecks = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return decks;
    return decks.filter((deck) => String(deck?.name || "").toLowerCase().includes(q));
  }, [decks, search]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-stone-200 bg-gradient-to-b from-amber-50 to-stone-100 p-4 shadow-sm">
        <h1 className="text-2xl font-bold text-stone-900">Library sources</h1>
        <p className="mt-1 text-sm text-stone-600">Browse curated sources and import words into your own books.</p>

        <div className="mt-3">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search reading packs by title"
            className="border-stone-300 bg-white/95"
          />
        </div>
      </div>

      {error ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
      ) : null}

      {loading ? <p className="text-sm text-stone-500">Loading library sources...</p> : null}

      {!loading && filteredDecks.length === 0 ? (
        <Card className="border-stone-200 bg-white/90">
          <p className="text-sm text-stone-600">
            {search.trim() ? "No reading packs found for your search." : "No reading packs available right now."}
          </p>
        </Card>
      ) : null}

      {!loading && filteredDecks.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {filteredDecks.map((deck) => (
            <LibraryDeckTile
              key={deck.id}
              deck={deck}
              onClick={() => nav(`/app/library/${deck.id}`, { state: { deck } })}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
