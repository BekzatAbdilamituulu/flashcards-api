import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CardsApi, DecksApi, ReadingSourcesApi } from "../api/endpoints";
import Button from "../components/Button";
import Card from "../components/Card";
import Input from "../components/Input";
import { useActivePair } from "../context/ActivePairContext";
import {
  collectSelectedCandidates,
  parseHighlightsWithCandidates,
} from "../utils/highlightImport";
import { setCurrentSourceForPair } from "../utils/currentSourceStorage";
import { memoryStrengthFromCard } from "../utils/memoryStrength";

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

const PAGE_LIMIT = 20;
const CONTENT_KIND_OPTIONS = ["word", "phrase", "quote", "idea"];

function isMainDeck(deck) {
  return (
    deck?.deck_type === "main" ||
    deck?.deck_type === "MAIN" ||
    deck?.is_main === true ||
    (typeof deck?.name === "string" && deck.name.toLowerCase().includes("main"))
  );
}

export default function SourceDetailPage() {
  const nav = useNavigate();
  const { sourceId: sourceIdParam } = useParams();
  const sourceId = Number(sourceIdParam);
  const editCardId = Number(new URLSearchParams(window.location.search).get("editCardId") || 0);
  const { activePair } = useActivePair();

  const [source, setSource] = useState(null);
  const [sourceStats, setSourceStats] = useState(null);
  const [mainDeck, setMainDeck] = useState(null);

  const [cardsPage, setCardsPage] = useState(null);
  const [offset, setOffset] = useState(0);

  const [loadingSource, setLoadingSource] = useState(true);
  const [loadingCards, setLoadingCards] = useState(true);
  const [error, setError] = useState("");
  const [cardsError, setCardsError] = useState("");

  const [creating, setCreating] = useState(false);
  const [editingSource, setEditingSource] = useState(false);
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceAuthor, setSourceAuthor] = useState("");
  const [sourceKind, setSourceKind] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [savingSource, setSavingSource] = useState(false);
  const [deletingSource, setDeletingSource] = useState(false);
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [contentKind, setContentKind] = useState("word");
  const [sourceSentence, setSourceSentence] = useState("");
  const [sourcePage, setSourcePage] = useState("");
  const [contextNote, setContextNote] = useState("");

  const [editingId, setEditingId] = useState(null);
  const [editFront, setEditFront] = useState("");
  const [editBack, setEditBack] = useState("");
  const [editContentKind, setEditContentKind] = useState("word");
  const [editSourceSentence, setEditSourceSentence] = useState("");
  const [editSourcePage, setEditSourcePage] = useState("");
  const [editContextNote, setEditContextNote] = useState("");
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const [importText, setImportText] = useState("");
  const [importPreview, setImportPreview] = useState([]);
  const [importMsg, setImportMsg] = useState("");
  const [importing, setImporting] = useState(false);

  const cards = useMemo(() => cardsPage?.items ?? [], [cardsPage]);

  const meta = cardsPage?.meta;
  const selectedCandidateCount = useMemo(
    () => collectSelectedCandidates(importPreview).length,
    [importPreview]
  );
  const difficultWordsCount = useMemo(() => {
    return cards.filter((card) => {
      const status = String(card?.status || "").toLowerCase();
      return status === "difficult" || status === "hard";
    }).length;
  }, [cards]);

  const totalWords = sourceStats?.total_cards ?? meta?.total ?? cards.length;
  const dueWords = sourceStats?.due_cards ?? 0;

  async function loadSourceAndDeck(nextOffset = offset) {
    setLoadingSource(true);
    setLoadingCards(true);
    setError("");
    setCardsError("");
    try {
      if (!activePair?.id) {
        setSource(null);
        setMainDeck(null);
        setCardsPage({ items: [], meta: { total: 0, offset: 0, limit: PAGE_LIMIT, has_more: false } });
        setError("Select an active learning pair first.");
        return false;
      }

      const [detailRes, decksRes] = await Promise.all([
        ReadingSourcesApi.getDetail(sourceId, PAGE_LIMIT, nextOffset),
        DecksApi.list(200, 0, { pair_id: activePair.id }),
      ]);

      const detail = detailRes.data;
      const loadedSource = detail?.source;
      if (String(loadedSource?.pair_id) !== String(activePair.id)) {
        setSource(null);
        setMainDeck(null);
        setCardsPage({ items: [], meta: { total: 0, offset: 0, limit: PAGE_LIMIT, has_more: false } });
        setError("This source does not belong to the active pair.");
        return false;
      }

      const pairDecks = decksRes.data?.items ?? [];
      const resolvedMainDeck = pairDecks.find((deck) => isMainDeck(deck)) ?? pairDecks[0] ?? null;
      if (!resolvedMainDeck) {
        setSource(loadedSource);
        setSourceStats(loadedSource);
        setMainDeck(null);
        setCardsPage({ items: detail?.cards ?? [], meta: detail?.meta ?? { total: 0, offset: 0, limit: PAGE_LIMIT, has_more: false } });
        setError("Reading review is not ready for this pair.");
        return false;
      }

      setSource(loadedSource);
      setSourceStats(loadedSource);
      setMainDeck(resolvedMainDeck);
      setCardsPage({ items: detail?.cards ?? [], meta: detail?.meta ?? { total: 0, offset: 0, limit: PAGE_LIMIT, has_more: false } });
      setOffset(nextOffset);
      setCurrentSourceForPair(activePair.id, loadedSource.id);
      return true;
    } catch (e) {
      setError(extractError(e));
      return false;
    } finally {
      setLoadingSource(false);
      setLoadingCards(false);
    }
  }

  async function loadCards(nextOffset = offset) {
    return loadSourceAndDeck(nextOffset);
  }

  function startSourceEdit() {
    setSourceTitle(source?.title ?? "");
    setSourceAuthor(source?.author ?? "");
    setSourceKind(source?.kind ?? "");
    setSourceReference(source?.reference ?? "");
    setEditingSource(true);
    setError("");
  }

  function cancelSourceEdit() {
    setEditingSource(false);
    setSourceTitle("");
    setSourceAuthor("");
    setSourceKind("");
    setSourceReference("");
  }

  async function saveSource() {
    if (!source?.id || !sourceTitle.trim()) return;

    setSavingSource(true);
    setError("");
    try {
      await ReadingSourcesApi.update(source.id, {
        title: sourceTitle.trim(),
        author: sourceAuthor.trim() ? sourceAuthor.trim() : null,
        kind: sourceKind.trim() ? sourceKind.trim() : null,
        reference: sourceReference.trim() ? sourceReference.trim() : null,
      });
      cancelSourceEdit();
      await loadSourceAndDeck(offset);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setSavingSource(false);
    }
  }

  async function deleteSource() {
    if (!source?.id) return;

    const ok = window.confirm(`Delete "${source.title}"?`);
    if (!ok) return;

    setDeletingSource(true);
    setError("");
    try {
      await ReadingSourcesApi.delete(source.id);
      nav("/app/sources");
    } catch (e) {
      setError(extractDeleteError(e));
    } finally {
      setDeletingSource(false);
    }
  }

  async function createCard(e) {
    e.preventDefault();
    if (!mainDeck?.id || !front.trim() || !back.trim()) return;

    const sentence = sourceSentence.trim();

    setCreating(true);
    setCardsError("");
    try {
      await CardsApi.create(mainDeck.id, {
        front: front.trim(),
        back: back.trim(),
        example_sentence: sentence || null,
        content_kind: contentKind || null,
        reading_source_id: sourceId,
        source_sentence: sentence || null,
        source_page: sourcePage.trim() ? sourcePage.trim() : null,
        context_note: contextNote.trim() ? contextNote.trim() : null,
      });
      setFront("");
      setBack("");
      setContentKind("word");
      setSourceSentence("");
      setSourcePage("");
      setContextNote("");
      await Promise.all([loadCards(offset), loadSourceAndDeck()]);
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setCreating(false);
    }
  }

  function startEdit(card) {
    setEditingId(card.id);
    setEditFront(card.front ?? "");
    setEditBack(card.back ?? "");
    setEditContentKind(card.content_kind ?? "word");
    setEditSourceSentence(card.source_sentence ?? card.example_sentence ?? "");
    setEditSourcePage(card.source_page ?? "");
    setEditContextNote(card.context_note ?? "");
  }

  useEffect(() => {
    if (!editCardId || !cards.length) return;
    const targetCard = cards.find((card) => Number(card.id) === Number(editCardId));
    if (targetCard) {
      startEdit(targetCard);
    }
  }, [editCardId, cards]);

  function cancelEdit() {
    setEditingId(null);
    setEditFront("");
    setEditBack("");
    setEditContentKind("word");
    setEditSourceSentence("");
    setEditSourcePage("");
    setEditContextNote("");
  }

  async function saveEdit(card) {
    if (!editFront.trim() || !editBack.trim()) return;

    const sentence = editSourceSentence.trim();

    setSavingId(card.id);
    setCardsError("");
    try {
      await CardsApi.update(card.deck_id, card.id, {
        front: editFront.trim(),
        back: editBack.trim(),
        example_sentence: sentence || null,
        content_kind: editContentKind || null,
        reading_source_id: sourceId,
        source_sentence: sentence || null,
        source_page: editSourcePage.trim() ? editSourcePage.trim() : null,
        context_note: editContextNote.trim() ? editContextNote.trim() : null,
      });
      cancelEdit();
      await loadCards(offset);
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setSavingId(null);
    }
  }

  async function deleteCard(card) {
    const ok = window.confirm("Delete this entry?");
    if (!ok) return;

    setDeletingId(card.id);
    setCardsError("");
    try {
      await CardsApi.delete(card.deck_id, card.id);

      const currentCount = cards.length;
      if (currentCount === 1 && offset > 0) {
        const prevOffset = Math.max(0, offset - PAGE_LIMIT);
        await loadCards(prevOffset);
      } else {
        await loadCards(offset);
      }
      await loadSourceAndDeck();
    } catch (e) {
      setCardsError(extractError(e));
    } finally {
      setDeletingId(null);
    }
  }

  function previewHighlights() {
    const parsed = parseHighlightsWithCandidates(importText);
    setImportPreview(parsed);
    if (!parsed.length) {
      setImportMsg("No highlights found. Paste exported highlights or reading notes text.");
      return;
    }
    const totalCandidates = collectSelectedCandidates(parsed).length;
    setImportMsg(`Preview ready: ${parsed.length} highlight(s), ${totalCandidates} selected candidate(s).`);
  }

  function onImportFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImportText(String(reader.result || ""));
      setImportMsg("");
    };
    reader.readAsText(file);
  }

  function toggleImportItem(itemId) {
    setImportPreview((current) =>
      current.map((item) => {
        if (item.id !== itemId) return item;
        const allSelected = (item.candidates || []).every((candidate) => candidate.selected);
        return {
          ...item,
          candidates: (item.candidates || []).map((candidate) => ({
            ...candidate,
            selected: !allSelected,
          })),
        };
      })
    );
  }

  function updateImportItem(itemId, patch) {
    setImportPreview((current) =>
      current.map((item) => (item.id === itemId ? { ...item, ...patch } : item))
    );
  }

  function toggleImportCandidate(itemId, candidateId) {
    setImportPreview((current) =>
      current.map((item) => {
        if (item.id !== itemId) return item;
        return {
          ...item,
          candidates: (item.candidates || []).map((candidate) =>
            candidate.id === candidateId ? { ...candidate, selected: !candidate.selected } : candidate
          ),
        };
      })
    );
  }

  function updateImportCandidate(itemId, candidateId, patch) {
    setImportPreview((current) =>
      current.map((item) => {
        if (item.id !== itemId) return item;
        return {
          ...item,
          candidates: (item.candidates || []).map((candidate) =>
            candidate.id === candidateId ? { ...candidate, ...patch } : candidate
          ),
        };
      })
    );
  }

  async function importSelectedHighlights() {
    if (!mainDeck?.id) return;
    const selectedItems = collectSelectedCandidates(importPreview);
    if (!selectedItems.length) {
      setImportMsg("Select at least one parsed highlight.");
      return;
    }

    setImporting(true);
    setImportMsg("");
    let created = 0;
    let failed = 0;

    for (const item of selectedItems) {
      try {
        await CardsApi.create(mainDeck.id, {
          front: item.text.trim(),
          back: "",
          content_kind: item.kind || "quote",
          reading_source_id: sourceId,
          source_sentence: item.sourceSentence ? item.sourceSentence.trim() : null,
          example_sentence: item.sourceSentence ? item.sourceSentence.trim() : null,
          source_page: item.sourcePage ? item.sourcePage.trim() : null,
          context_note: source?.title ? `Source title: ${source.title}` : null,
        });
        created += 1;
      } catch {
        failed += 1;
      }
    }

    await Promise.all([loadCards(offset), loadSourceAndDeck()]);
    setImportMsg(`Imported ${created} item(s)${failed ? `, failed ${failed}` : ""}.`);
    setImportPreview((current) =>
      current.map((item) => ({
        ...item,
        candidates: (item.candidates || []).map((candidate) => ({ ...candidate, selected: false })),
      }))
    );
    setImporting(false);
  }

  useEffect(() => {
    async function loadAll() {
      if (!(sourceId > 0)) {
        setError("Invalid source id.");
        setLoadingSource(false);
        setLoadingCards(false);
        return;
      }

      const ok = await loadSourceAndDeck();
      if (ok) {
        await loadCards(0);
      } else {
        setLoadingCards(false);
      }
    }

    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceId, activePair?.id]);

  return (
    <div className="space-y-4">
      <Link to="/app/sources" className="text-sm text-gray-500 underline">
        Back to sources
      </Link>

      <div className="flex items-start justify-between gap-3">
        <div>
          {editingSource ? (
            <div className="grid max-w-2xl gap-3">
              <Input value={sourceTitle} onChange={(e) => setSourceTitle(e.target.value)} placeholder="Title" />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input
                  value={sourceAuthor}
                  onChange={(e) => setSourceAuthor(e.target.value)}
                  placeholder="Author"
                />
                <Input value={sourceKind} onChange={(e) => setSourceKind(e.target.value)} placeholder="Kind" />
              </div>
              <Input
                value={sourceReference}
                onChange={(e) => setSourceReference(e.target.value)}
                placeholder="Reference"
              />
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" onClick={saveSource} disabled={savingSource || !sourceTitle.trim()}>
                  {savingSource ? "Saving..." : "Save source"}
                </Button>
                <Button variant="secondary" onClick={cancelSourceEdit} disabled={savingSource}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold">
                {loadingSource ? "Loading source..." : source?.title || `Source #${sourceId}`}
              </h1>
              {source ? (
                <p className="mt-1 text-sm text-gray-500">
                  {source.author ? `${source.author} · ` : ""}
                  {source.kind ? `${source.kind} · ` : ""}
                  {source.reference || ""}
                </p>
              ) : null}
            </>
          )}
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600 sm:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white px-2 py-2">
              Total words: <span className="font-semibold text-gray-900">{totalWords}</span>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-2 py-2">
              Due: <span className="font-semibold text-gray-900">{dueWords}</span>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-2 py-2">
              Added today: <span className="font-semibold text-gray-900">{sourceStats?.added_today ?? 0}</span>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white px-2 py-2">
              Difficult: <span className="font-semibold text-gray-900">{difficultWordsCount}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="primary"
            onClick={() => (mainDeck?.id ? nav(`/app/study/${mainDeck.id}?sourceId=${sourceId}`) : null)}
            disabled={!mainDeck?.id || editingSource}
          >
            Review from this source
          </Button>
        </div>
      </div>

      {error ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
      ) : null}

      <Card>
        <h2 className="text-lg font-semibold">Import highlights</h2>
        <p className="mt-1 text-sm text-gray-600">
          Paste Kindle highlights or reading notes. You can also paste text from PDF highlights/notes.
        </p>
        <div className="mt-3 grid gap-3">
          <textarea
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder="Paste highlights here..."
            className="min-h-36 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-black"
          />
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => onImportFile(e.target.files?.[0])}
              className="text-sm"
            />
            <Button variant="secondary" type="button" onClick={previewHighlights}>
              Preview parsed items
            </Button>
            <Button
              variant="primary"
              type="button"
              onClick={importSelectedHighlights}
              disabled={importing || selectedCandidateCount === 0 || !mainDeck?.id}
            >
              {importing ? "Importing..." : "Import selected"}
            </Button>
          </div>
          {importMsg ? <p className="text-xs text-gray-600">{importMsg}</p> : null}
        </div>

        {importPreview.length ? (
          <div className="mt-4 space-y-3">
            {importPreview.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="checkbox"
                    checked={(item.candidates || []).some((candidate) => candidate.selected)}
                    onChange={() => toggleImportItem(item.id)}
                  />
                  <span className="text-xs text-gray-500">Select all candidates in this highlight</span>
                </div>
                {item.sourceTitle ? <p className="mt-2 text-xs text-gray-500">Title: {item.sourceTitle}</p> : null}
                <textarea
                  value={item.text}
                  onChange={(e) => updateImportItem(item.id, { text: e.target.value })}
                  className="mt-2 min-h-20 w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm"
                />
                <Input
                  className="mt-2"
                  value={item.sourcePage}
                  onChange={(e) => updateImportItem(item.id, { sourcePage: e.target.value })}
                  placeholder="Page/location (optional)"
                />
                {item.candidates?.length ? (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-medium text-gray-600">Candidate words/phrases</p>
                    {item.candidates.map((candidate) => (
                      <div
                        key={candidate.id}
                        className="flex flex-wrap items-center gap-2 rounded border border-gray-200 bg-white px-2 py-2"
                      >
                        <input
                          type="checkbox"
                          checked={candidate.selected}
                          onChange={() => toggleImportCandidate(item.id, candidate.id)}
                        />
                        <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-gray-600">
                          {candidate.kind}
                        </span>
                        <Input
                          className="min-w-[14rem] flex-1"
                          value={candidate.text}
                          onChange={(e) =>
                            updateImportCandidate(item.id, candidate.id, { text: e.target.value })
                          }
                        />
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </Card>

      <Card>
        <h2 className="text-lg font-semibold">Save word</h2>
        <p className="mt-1 text-sm text-gray-600">Capture the word first. Add extra source details only when you need them.</p>
        <form onSubmit={createCard} className="mt-4 grid gap-3">
          <Input placeholder="Word" value={front} onChange={(e) => setFront(e.target.value)} />
          <Input placeholder="Translation / meaning" value={back} onChange={(e) => setBack(e.target.value)} />
          <Input
            placeholder="Sentence (optional)"
            value={sourceSentence}
            onChange={(e) => setSourceSentence(e.target.value)}
          />
          <details>
            <summary className="cursor-pointer text-sm font-medium text-gray-700">Advanced details</summary>
            <div className="mt-3 grid gap-3">
              <label className="grid gap-2">
                <span className="text-sm text-gray-700">Entry kind</span>
                <select
                  value={contentKind}
                  onChange={(e) => setContentKind(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-black"
                >
                  {CONTENT_KIND_OPTIONS.map((kind) => (
                    <option key={kind} value={kind}>
                      {kind}
                    </option>
                  ))}
                </select>
              </label>
              <Input
                placeholder="Source page (optional)"
                value={sourcePage}
                onChange={(e) => setSourcePage(e.target.value)}
              />
              <Input
                placeholder="Context note (optional)"
                value={contextNote}
                onChange={(e) => setContextNote(e.target.value)}
              />
            </div>
          </details>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" type="submit" disabled={creating || !front.trim() || !back.trim() || !mainDeck?.id}>
              {creating ? "Saving..." : "Save word"}
            </Button>
            <Button variant="secondary" type="button" onClick={() => loadCards(offset)} disabled={loadingCards}>
              {loadingCards ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </form>
      </Card>

      {cardsError ? (
        <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{cardsError}</pre>
      ) : null}

      <div className="space-y-3">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Vocabulary from this source</h2>
            <p className="text-sm text-gray-500">Words, meanings, and sentences tied to this text.</p>
          </div>
        </Card>

        {loadingCards ? <p className="text-sm text-gray-500">Loading entries...</p> : null}

        {!loadingCards && cards.length === 0 ? (
          <Card>
            <p className="text-gray-700">No words in this source yet.</p>
          </Card>
        ) : null}

        {!loadingCards
          ? cards.map((card) => {
              const isEditing = editingId === card.id;
              const isSaving = savingId === card.id;
              const isDeleting = deletingId === card.id;

              return (
                <Card key={card.id}>
                  {isEditing ? (
                    <div className="grid gap-3">
                      <Input value={editFront} onChange={(e) => setEditFront(e.target.value)} placeholder="Word" />
                      <Input value={editBack} onChange={(e) => setEditBack(e.target.value)} placeholder="Translation / meaning" />
                      <Input
                        value={editSourceSentence}
                        onChange={(e) => setEditSourceSentence(e.target.value)}
                        placeholder="Sentence (optional)"
                      />
                      <details>
                        <summary className="cursor-pointer text-sm font-medium text-gray-700">Advanced details</summary>
                        <div className="mt-3 grid gap-3">
                          <label className="grid gap-2">
                            <span className="text-sm text-gray-700">Entry kind</span>
                            <select
                              value={editContentKind}
                              onChange={(e) => setEditContentKind(e.target.value)}
                              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-black"
                            >
                              {CONTENT_KIND_OPTIONS.map((kind) => (
                                <option key={kind} value={kind}>
                                  {kind}
                                </option>
                              ))}
                            </select>
                          </label>
                          <Input
                            value={editSourcePage}
                            onChange={(e) => setEditSourcePage(e.target.value)}
                            placeholder="Source page"
                          />
                          <Input
                            value={editContextNote}
                            onChange={(e) => setEditContextNote(e.target.value)}
                            placeholder="Context note"
                          />
                        </div>
                      </details>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="primary"
                          onClick={() => saveEdit(card)}
                          disabled={isSaving || !editFront.trim() || !editBack.trim()}
                        >
                          {isSaving ? "Saving..." : "Save"}
                        </Button>
                        <Button variant="secondary" onClick={cancelEdit} disabled={isSaving}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-gray-500">Word / entry</p>
                        <p className="text-gray-700">{card.front}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Translation / meaning</p>
                        <p className="text-gray-700">{card.back}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Source sentence</p>
                        <p className="text-gray-700">{card.source_sentence || card.example_sentence || "-"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Memory strength</p>
                        <p className="text-gray-700">{card.memory_strength || memoryStrengthFromCard(card)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Word type</p>
                        <p className="text-gray-700">{card.content_kind || "-"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Source page</p>
                        <p className="text-gray-700">{card.source_page || "-"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Context note</p>
                        <p className="text-gray-700">{card.context_note || "-"}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button
                          variant="secondary"
                          onClick={() => startEdit(card)}
                          disabled={deletingId != null || savingId != null}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="danger"
                          onClick={() => deleteCard(card)}
                          disabled={isDeleting || editingId != null || savingId != null}
                        >
                          {isDeleting ? "Deleting..." : "Delete"}
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>
              );
            })
          : null}
      </div>

      {meta ? (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <Button
            variant="secondary"
            onClick={() => loadCards(Math.max(0, offset - PAGE_LIMIT))}
            disabled={loadingCards || offset === 0}
          >
            Prev
          </Button>

          <p className="text-xs text-gray-500">
            {cards.length ? `${offset + 1}-${Math.min(offset + cards.length, meta.total)}` : "0"} of {meta.total}
          </p>

          <Button
            variant="secondary"
            onClick={() => loadCards(offset + PAGE_LIMIT)}
            disabled={loadingCards || !meta.has_more}
          >
            Next
          </Button>
        </div>
      ) : null}
    </div>
  );
}
