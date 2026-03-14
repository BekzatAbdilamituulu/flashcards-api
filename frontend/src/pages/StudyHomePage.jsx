import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DecksApi, ReadingSourcesApi } from "../api/endpoints";
import Card from "../components/Card";
import Button from "../components/Button";
import { useActivePair } from "../context/ActivePairContext";

function isMainDeck(deck) {
  return (
    deck?.deck_type === "main" ||
    deck?.deck_type === "MAIN" ||
    deck?.is_main === true ||
    (typeof deck?.name === "string" && deck.name.toLowerCase().includes("main"))
  );
}

export default function StudyHomePage() {
  const { activePair } = useActivePair();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [decks, setDecks] = useState([]);
  const [sources, setSources] = useState([]);

  const mainDeck = useMemo(() => {
    if (!decks.length) return null;
    return decks.find(isMainDeck) ?? decks[0];
  }, [decks]);

  useEffect(() => {
    async function load() {
      if (!activePair?.id) {
        setDecks([]);
        setSources([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const [decksRes, sourcesRes] = await Promise.all([
          DecksApi.list(200, 0, { pair_id: activePair.id }),
          ReadingSourcesApi.list({ pair_id: activePair.id, include_stats: true, limit: 200, offset: 0 }),
        ]);
        setDecks(decksRes.data?.items ?? []);
        setSources(sourcesRes.data?.items ?? []);
      } catch (e) {
        setError(e?.message ?? "Failed to load study options.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [activePair?.id]);

  return (
    <div className="mx-auto w-full max-w-md">
      <Card className="text-center">
        <h1 className="text-2xl font-bold">Reading review</h1>
        <p className="mt-2 text-gray-700">Start a reading review with your active learning pair.</p>

        {loading ? <p className="mt-4 text-sm text-gray-500">Loading study options...</p> : null}
        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}

        {!loading && !error && !mainDeck ? (
          <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
            No reviewable words found for the active pair yet.
          </div>
        ) : null}

        {!loading && !error && mainDeck ? (
          <Link to={`/app/study/${mainDeck.id}`} className="mt-4 inline-block w-full">
            <Button variant="primary" className="w-full">Start reading review</Button>
          </Link>
        ) : null}

        {!loading && !error && mainDeck && sources.length > 0 ? (
          <div className="mt-4 space-y-2 text-left">
            <p className="text-sm font-medium text-gray-800">Review a specific source</p>
            <div className="grid gap-2">
              {sources
                .filter((source) => Number(source?.total_cards ?? 0) > 0)
                .slice(0, 5)
                .map((source) => (
                  <Link
                    key={source.id}
                    to={`/app/study/${mainDeck.id}?sourceId=${source.id}`}
                    className="block"
                  >
                    <Button variant="secondary" className="w-full justify-between">
                      <span>{source.title}</span>
                      <span>{Number(source?.due_cards ?? 0)} due</span>
                    </Button>
                  </Link>
                ))}
            </div>
          </div>
        ) : null}

        <Link to="/app/sources" className="mt-3 inline-block w-full">
          <Button variant="secondary" className="w-full">Open sources</Button>
        </Link>
      </Card>
    </div>
  );
}
