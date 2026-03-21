import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LanguagesApi, ReadingSourcesApi } from "../api/endpoints";
import Button from "../components/Button";
import Card from "../components/Card";
import Input from "../components/Input";
import { useActivePair } from "../context/ActivePairContext";

function extractError(e) {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function extractDeleteError(e) {
  const detail = String(e?.response?.data?.detail || e?.message || "").toLowerCase();
  if (detail.includes("cards still reference it")) {
    return "This source can't be deleted because saved words still reference it. Delete or move those words first.";
  }
  return extractError(e);
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
  const [editingSourceId, setEditingSourceId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAuthor, setEditAuthor] = useState("");
  const [editKind, setEditKind] = useState("");
  const [editReference, setEditReference] = useState("");
  const [savingSourceId, setSavingSourceId] = useState(null);
  const [deletingSourceId, setDeletingSourceId] = useState(null);

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

  function startEditSource(source) {
    setEditingSourceId(source.id);
    setEditTitle(source.title ?? "");
    setEditAuthor(source.author ?? "");
    setEditKind(source.kind ?? "");
    setEditReference(source.reference ?? "");
    setError("");
  }

  function cancelEditSource() {
    setEditingSourceId(null);
    setEditTitle("");
    setEditAuthor("");
    setEditKind("");
    setEditReference("");
  }

  async function saveSource(sourceId) {
    if (!editTitle.trim()) return;

    setSavingSourceId(sourceId);
    setError("");
    try {
      await ReadingSourcesApi.update(sourceId, {
        title: editTitle.trim(),
        author: editAuthor.trim() ? editAuthor.trim() : null,
        kind: editKind.trim() ? editKind.trim() : null,
        reference: editReference.trim() ? editReference.trim() : null,
      });
      cancelEditSource();
      await load();
    } catch (e) {
      setError(extractError(e));
    } finally {
      setSavingSourceId(null);
    }
  }

  async function deleteSource(source) {
    const ok = window.confirm(`Delete "${source.title}"?`);
    if (!ok) return;

    setDeletingSourceId(source.id);
    setError("");
    try {
      await ReadingSourcesApi.delete(source.id);
      if (editingSourceId === source.id) cancelEditSource();
      await load();
    } catch (e) {
      setError(extractDeleteError(e));
    } finally {
      setDeletingSourceId(null);
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
              {editingSourceId === source.id ? (
                <div className="grid gap-3">
                  <label className="grid gap-2">
                    <span className="text-sm text-gray-700">Title</span>
                    <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="grid gap-2">
                      <span className="text-sm text-gray-700">Author</span>
                      <Input value={editAuthor} onChange={(e) => setEditAuthor(e.target.value)} />
                    </label>
                    <label className="grid gap-2">
                      <span className="text-sm text-gray-700">Kind</span>
                      <Input value={editKind} onChange={(e) => setEditKind(e.target.value)} />
                    </label>
                  </div>
                  <label className="grid gap-2">
                    <span className="text-sm text-gray-700">Reference</span>
                    <Input value={editReference} onChange={(e) => setEditReference(e.target.value)} />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      onClick={() => saveSource(source.id)}
                      disabled={savingSourceId === source.id || !editTitle.trim()}
                    >
                      {savingSourceId === source.id ? "Saving..." : "Save"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={cancelEditSource}
                      disabled={savingSourceId === source.id}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <>
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
                      <p className="text-xs text-gray-500">
                        Last added: {new Date(source.last_added_at).toLocaleString()}
                      </p>
                    ) : null}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button variant="primary" onClick={() => nav(`/app/sources/${source.id}`)}>
                      Open source
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => startEditSource(source)}
                      disabled={deletingSourceId != null || savingSourceId != null}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => deleteSource(source)}
                      disabled={deletingSourceId === source.id || editingSourceId != null || savingSourceId != null}
                    >
                      {deletingSourceId === source.id ? "Deleting..." : "Delete"}
                    </Button>
                  </div>
                </>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
