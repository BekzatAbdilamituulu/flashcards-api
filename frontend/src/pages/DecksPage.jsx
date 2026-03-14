import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LanguagesApi, ReadingSourcesApi } from "../api/endpoints";
import Button from "../components/Button";
import Card from "../components/Card";
import Input from "../components/Input";
import { useActivePair } from "../context/ActivePairContext";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function langLabel(l) {
  if (!l) return "?";
  return `${l.name}${l.code ? ` (${l.code})` : ""}`;
}

function normalizeSourceStats(source) {
  return {
    ...source,
    total_cards: Number(source?.total_cards ?? source?.cards_count ?? source?.word_count ?? 0),
    due_cards: Number(source?.due_cards ?? source?.due_count ?? 0),
  };
}

export default function SourcesPage() {
  const nav = useNavigate();
  const { activePair, loading: activePairLoading } = useActivePair();

  const [sourcesPage, setSourcesPage] = useState(null);
  const [languages, setLanguages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [kind, setKind] = useState("");
  const [reference, setReference] = useState("");
  const [creating, setCreating] = useState(false);

  const langById = useMemo(() => {
    const m = new Map();
    for (const l of languages) m.set(l.id, l);
    return m;
  }, [languages]);

  const activeLearning = activePair ? langById.get(activePair.source_language_id) : null;
  const activeTranslation = activePair ? langById.get(activePair.target_language_id) : null;

  async function load() {
    if (!activePair?.id) {
      setSourcesPage({ items: [], meta: { total: 0, has_more: false, offset: 0, limit: 50 } });
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [sourcesRes, langsRes] = await Promise.all([
        ReadingSourcesApi.list({ pair_id: activePair.id, include_stats: true, limit: 200, offset: 0 }),
        LanguagesApi.list(),
      ]);
      const payload = sourcesRes.data ?? { items: [] };
      const items = Array.isArray(payload?.items) ? payload.items.map(normalizeSourceStats) : [];
      setSourcesPage({
        ...payload,
        items,
      });
      setLanguages(langsRes.data ?? []);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  async function createSource(e) {
    e.preventDefault();
    if (!activePair?.id) {
      setError("Select an active learning pair before creating a source.");
      return;
    }
    if (!title.trim()) return;

    setCreating(true);
    setError("");
    try {
      await ReadingSourcesApi.create({
        pair_id: activePair.id,
        title: title.trim(),
        author: author.trim() ? author.trim() : null,
        kind: kind.trim() ? kind.trim() : null,
        reference: reference.trim() ? reference.trim() : null,
      });
      setTitle("");
      setAuthor("");
      setKind("");
      setReference("");
      await load();
    } catch (e) {
      setError(extractError(e));
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    if (activePairLoading) {
      setLoading(true);
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePair?.id, activePairLoading]);

  const sources = sourcesPage?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Books & Sources</h1>
        <p className="mt-1 text-sm text-gray-500">Organize saved words by the text where you found them.</p>
        {activePair ? (
          <p className="mt-2 text-sm text-gray-700">
            Active pair: <span className="font-semibold">{langLabel(activeLearning)}</span> to{" "}
            <span className="font-semibold">{langLabel(activeTranslation)}</span>
          </p>
        ) : null}
      </div>

      <Card>
        <h2 className="text-lg font-semibold">Add source</h2>
        {!activePair ? (
          <p className="mt-2 text-sm text-gray-600">Choose an active pair first.</p>
        ) : (
          <p className="mt-2 text-sm text-gray-600">This source will be linked to the active pair.</p>
        )}

        <form onSubmit={createSource} className="mt-4 grid gap-3">
          <label className="grid gap-2">
            <span className="text-sm text-gray-700">Title</span>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm text-gray-700">Author (optional)</span>
              <Input value={author} onChange={(e) => setAuthor(e.target.value)} />
            </label>
            <label className="grid gap-2">
              <span className="text-sm text-gray-700">Kind (optional)</span>
              <Input value={kind} onChange={(e) => setKind(e.target.value)} placeholder="book, article..." />
            </label>
          </div>

          <label className="grid gap-2">
            <span className="text-sm text-gray-700">Reference (optional)</span>
            <Input
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="chapter, location, URL"
            />
          </label>

          <div>
            <Button variant="primary" type="submit" disabled={creating || !activePair}>
              {creating ? "Creating..." : "Create source"}
            </Button>
          </div>
        </form>
      </Card>

      {error ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
      ) : null}

      {loading || activePairLoading ? (
        <p className="text-sm text-gray-500">Loading sources...</p>
      ) : !activePair ? (
        <Card>
          <p className="text-sm text-gray-600">Select an active pair to view sources.</p>
        </Card>
      ) : sources.length === 0 ? (
        <Card>
          <p className="text-sm text-gray-600">No sources yet. Add your first book or text source.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {sources.map((source) => (
            <Card key={source.id} className="transition-shadow hover:shadow-md">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">{source.title}</h3>
                {(source.author || source.kind) && (
                  <p className="text-sm text-gray-600">
                    {source.author || "Unknown"}
                    {source.kind ? ` · ${source.kind}` : ""}
                  </p>
                )}
                {source.reference ? <p className="text-xs text-gray-500">{source.reference}</p> : null}
                <p className="text-sm text-gray-700">
                  Words: <span className="font-semibold">{source.total_cards ?? 0}</span>
                  {" · "}
                  Due: <span className="font-semibold">{source.due_cards ?? 0}</span>
                </p>
                {source.last_added_at ? (
                  <p className="text-xs text-gray-500">Last added: {new Date(source.last_added_at).toLocaleString()}</p>
                ) : null}
              </div>

              <div className="mt-4 flex gap-2">
                <Button variant="primary" onClick={() => nav(`/app/sources/${source.id}`)}>
                  Open source
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
