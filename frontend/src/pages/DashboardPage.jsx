import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AutoApi,
  CardsApi,
  DecksApi,
  LanguagesApi,
  ProgressApi,
  ReadingSourcesApi,
} from "../api/endpoints";
import { useActivePair } from "../context/ActivePairContext";
import {
  clearCurrentSourceForPair,
  getCurrentSourceForPair,
  setCurrentSourceForPair,
} from "../utils/currentSourceStorage";
import { memoryStrengthFromCard } from "../utils/memoryStrength";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function isMainDeck(deck) {
  return (
    deck?.deck_type === "main" ||
    deck?.deck_type === "MAIN" ||
    deck?.is_main === true ||
    (typeof deck?.name === "string" && deck.name.toLowerCase().includes("main"))
  );
}

function Modal({ open, title, children, onClose }) {
  if (!open) return null;

  return (
    <div
      onMouseDown={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.2)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <div
        onMouseDown={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 520,
          background: "white",
          border: "1px solid #ddd",
          borderRadius: 12,
          padding: 16,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            marginBottom: 10,
          }}
        >
          <strong>{title}</strong>
          <button onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const nav = useNavigate();
  const {
    activePair,
    loading: activePairLoading,
  } = useActivePair();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [langs, setLangs] = useState([]);
  const [mainDeckCards, setMainDeckCards] = useState([]);
  const [editingDeckId, setEditingDeckId] = useState(null);
  const [editingCardId, setEditingCardId] = useState(null);
  const [editFront, setEditFront] = useState("");
  const [editBack, setEditBack] = useState("");
  const [editExample, setEditExample] = useState("");
  const [editReadingSourceId, setEditReadingSourceId] = useState("");
  const [editSourceTitle, setEditSourceTitle] = useState("");
  const [editSourceAuthor, setEditSourceAuthor] = useState("");
  const [editSourceKind, setEditSourceKind] = useState("");
  const [editSourceReference, setEditSourceReference] = useState("");
  const [editSourcePage, setEditSourcePage] = useState("");
  const [editContextNote, setEditContextNote] = useState("");
  const [busyCardAction, setBusyCardAction] = useState(false);
  const [wordsOpen, setWordsOpen] = useState(false);
  const [incompleteOpen, setIncompleteOpen] = useState(false);

  // Add word modal state
// NOTE: User is learning English:
//   front = English (learning language)
//   back  = Russian (translation/native)
//   example_sentence = English
const [addOpen, setAddOpen] = useState(false);
const [learningText, setLearningText] = useState(""); // front (en)
const [nativeText, setNativeText] = useState(""); // translation (ru)
const [sourceSentence, setSourceSentence] = useState("");
const [sourcePage, setSourcePage] = useState("");
const [contextNote, setContextNote] = useState("");
const [readingSources, setReadingSources] = useState([]);
const [sourceWidgetError, setSourceWidgetError] = useState("");
const [currentSourceId, setCurrentSourceId] = useState(null);
const [selectedReadingSourceId, setSelectedReadingSourceId] = useState("");
const [newSourceTitle, setNewSourceTitle] = useState("");
const [newSourceAuthor, setNewSourceAuthor] = useState("");
const [newSourceKind, setNewSourceKind] = useState("");
const [newSourceReference, setNewSourceReference] = useState("");
const [sourcePickerOpen, setSourcePickerOpen] = useState(false);
const [switchingSource, setSwitchingSource] = useState(false);
const [adding, setAdding] = useState(false);
const [addMsg, setAddMsg] = useState("");

// Auto preview (read-only; does NOT save to DB)
const [previewLoading, setPreviewLoading] = useState(false);
const [previewMsg, setPreviewMsg] = useState("");
const [dirtyNative, setDirtyNative] = useState(false);

  const nativeLang = useMemo(() => {
    if (!activePair) return null;
    return langs.find((l) => l.id === activePair.target_language_id) ?? null;
  }, [langs, activePair]);

  const learningLang = useMemo(() => {
    if (!activePair) return null;
    return langs.find((l) => l.id === activePair.source_language_id) ?? null;
  }, [langs, activePair]);

// When user types a word, suggest translation.
useEffect(() => {
  if (!addOpen) return;
  if (!activePair) return;

  const front = learningText.trim();
  if (!front) {
    setPreviewMsg("");
    setPreviewLoading(false);
    if (!dirtyNative) setNativeText("");
    return;
  }

  let cancelled = false;
  const t = setTimeout(async () => {
    try {
      setPreviewLoading(true);
      setPreviewMsg("");

      const res = await AutoApi.preview({
        front,
        deck_id: null,
        source_language_id: activePair.source_language_id, // learning (en)
        target_language_id: activePair.target_language_id, // native (ru)
      });

      if (cancelled) return;

      const data = res.data;
      if (!dirtyNative && data?.suggested_back != null) {
        setNativeText(data.suggested_back);
      }
    } catch (e) {
      if (cancelled) return;
      setPreviewMsg(extractError(e));
    } finally {
      if (!cancelled) setPreviewLoading(false);
    }
  }, 450);

  return () => {
    cancelled = true;
    clearTimeout(t);
  };
}, [addOpen, learningText, activePair, dirtyNative]);

  async function load() {
    if (!activePair?.id) {
      setMainDeckCards([]);
      setReadingSources([]);
      setCurrentSourceId(null);
      setSourceWidgetError("");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [langsRes, decksRes] = await Promise.all([
        LanguagesApi.list(),
        DecksApi.list(200, 0, { pair_id: activePair.id }),
      ]);
      setLangs(langsRes.data ?? []);
      let resolvedCurrentSourceId = null;
      try {
        const sourcesRes = await ReadingSourcesApi.list({
          pair_id: activePair.id,
          include_stats: true,
          limit: 200,
          offset: 0,
        });
        const sources = sourcesRes.data?.items ?? [];
        setReadingSources(sources);
        const rememberedSourceId = getCurrentSourceForPair(activePair.id);
        if (
          rememberedSourceId &&
          sources.some((source) => Number(source.id) === Number(rememberedSourceId))
        ) {
          resolvedCurrentSourceId = Number(rememberedSourceId);
          setCurrentSourceId(resolvedCurrentSourceId);
        } else {
          if (rememberedSourceId) clearCurrentSourceForPair(activePair.id);
          setCurrentSourceId(null);
        }
        setSourceWidgetError("");
      } catch (sourceError) {
        setReadingSources([]);
        setCurrentSourceId(null);
        setSourceWidgetError(extractError(sourceError));
      }
      const decks = decksRes.data?.items ?? [];
      const mainDecks = decks.filter((deck) => isMainDeck(deck));
      const deckSummaries = await Promise.all(
        mainDecks.map(async (deck) => {
          try {
            const [summaryRes, cardsRes] = await Promise.all([
              ProgressApi.summary({
                pair_id: activePair.id,
                deck_id: deck.id,
              }),
              CardsApi.list(
                deck.id,
                200,
                0
              ),
            ]);
            return {
              deck,
              summary: summaryRes.data,
              cards: cardsRes.data?.items ?? [],
            };
          } catch {
            return { deck, summary: null, cards: [] };
          }
        })
      );

      setMainDeckCards(deckSummaries);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  function startEdit(deckId, card) {
    const fallbackSourceId =
      card?.reading_source_id != null
        ? String(card.reading_source_id)
        : currentSourceId != null
          ? String(currentSourceId)
          : "";
    setEditingDeckId(deckId);
    setEditingCardId(card.id);
    setEditFront(card.front || "");
    setEditBack(card.back || "");
    setEditExample(card.source_sentence || card.example_sentence || "");
    setEditReadingSourceId(fallbackSourceId);
    setEditSourceTitle(card.source_title || "");
    setEditSourceAuthor(card.source_author || "");
    setEditSourceKind(card.source_kind || "");
    setEditSourceReference(card.source_reference || "");
    setEditSourcePage(card.source_page || "");
    setEditContextNote(card.context_note || "");
  }

  function cancelEdit() {
    setEditingDeckId(null);
    setEditingCardId(null);
    setEditFront("");
    setEditBack("");
    setEditExample("");
    setEditReadingSourceId("");
    setEditSourceTitle("");
    setEditSourceAuthor("");
    setEditSourceKind("");
    setEditSourceReference("");
    setEditSourcePage("");
    setEditContextNote("");
  }

  async function updateCard(deckId, card) {
    if (!editFront.trim() || !editBack.trim()) return;
    setBusyCardAction(true);
    const selectedSource = readingSources.find(
      (source) => String(source.id) === String(editReadingSourceId)
    );
    try {
      await CardsApi.update(deckId, card.id, {
        front: editFront.trim(),
        back: editBack.trim(),
        example_sentence: editExample.trim() ? editExample.trim() : null,
        source_sentence: editExample.trim() ? editExample.trim() : null,
        source_page: editSourcePage.trim() ? editSourcePage.trim() : null,
        context_note: editContextNote.trim() ? editContextNote.trim() : null,
        ...(editReadingSourceId
          ? { reading_source_id: Number(editReadingSourceId) }
          : {
              source_title: editSourceTitle.trim() ? editSourceTitle.trim() : null,
              source_author: editSourceAuthor.trim() ? editSourceAuthor.trim() : null,
              source_kind: editSourceKind.trim() ? editSourceKind.trim() : null,
              source_reference: editSourceReference.trim() ? editSourceReference.trim() : null,
            }),
      });
      if (activePair?.id && selectedSource) {
        setCurrentSourceForPair(activePair.id, selectedSource.id);
        setCurrentSourceId(selectedSource.id);
      }
      cancelEdit();
      await load();
    } catch (e) {
      setError(extractError(e));
    } finally {
      setBusyCardAction(false);
    }
  }

  async function deleteCard(deckId, cardId) {
    const ok = window.confirm("Delete this word?");
    if (!ok) return;

    setBusyCardAction(true);
    try {
      await CardsApi.delete(deckId, cardId);
      await load();
    } catch (e) {
      setError(extractError(e));
    } finally {
      setBusyCardAction(false);
    }
  }

  async function refreshDeckCards(deckId) {
    try {
      const cardsRes = await CardsApi.list(
        deckId,
        200,
        0
      );
      const nextCards = cardsRes.data?.items ?? [];
      setMainDeckCards((current) =>
        current.map((entry) =>
          entry.deck.id === deckId ? { ...entry, cards: nextCards } : entry
        )
      );
    } catch (e) {
      setError(extractError(e));
    }
  }

  async function resetProgress(deckId, cardId) {
    const ok = window.confirm("Reset progress for this word?");
    if (!ok) return;

    setBusyCardAction(true);
    try {
      await CardsApi.reset(deckId, cardId);
      await refreshDeckCards(deckId);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setBusyCardAction(false);
    }
  }

  function openAdd() {
    if (!activePair) {
      setError("Select an active learning pair before adding words.");
      return;
    }
    setAddMsg("");
    setPreviewMsg("");
    setPreviewLoading(false);
    setDirtyNative(false);
    setLearningText("");
    setNativeText("");
    setSourceSentence("");
    setSourcePage("");
    setContextNote("");
    setSelectedReadingSourceId(currentSourceId ? String(currentSourceId) : "");
    setNewSourceTitle("");
    setNewSourceAuthor("");
    setNewSourceKind("");
    setNewSourceReference("");
    setAddOpen(true);
  }

  function handleSourceSelectionChange(value) {
    setSelectedReadingSourceId(value);
    if (!activePair?.id || !value) return;
    const nextId = Number(value);
    if (Number.isFinite(nextId) && nextId > 0) {
      setCurrentSourceForPair(activePair.id, nextId);
      setCurrentSourceId(nextId);
    }
  }

  function renderSourceSummary(source) {
    if (!source) return null;
    return (
      <div
        style={{
          fontSize: 12,
          opacity: 0.8,
          border: "1px solid #e5e7eb",
          borderRadius: 10,
          padding: "8px 10px",
          background: "#f8fafc",
        }}
      >
        <div style={{ fontWeight: 600 }}>{source.title}</div>
        <div>
          {source.author || "Unknown author"}
          {source.kind ? ` · ${source.kind}` : ""}
        </div>
        {source.reference ? <div>{source.reference}</div> : null}
      </div>
    );
  }

  async function submitAdd(e) {
    e.preventDefault();
    if (!activePair) {
      setAddMsg("Select an active learning pair before saving.");
      return;
    }

    const learning = learningText.trim();
    const native = nativeText.trim();
    if (!learning) return;

    const targetDeck = mainDeckCards.find((entry) => isMainDeck(entry.deck)) ?? mainDeckCards[0] ?? null;
    if (!targetDeck?.deck?.id) {
      setAddMsg("Reading review is not ready for the active pair yet.");
      return;
    }

    setAdding(true);
    setAddMsg("");

    try {
      const createRes = await CardsApi.create(targetDeck.deck.id, {
        front: learning,
        back: native || null,
        content_kind: "word",
        example_sentence: sourceSentence.trim() ? sourceSentence.trim() : null,
        source_sentence: sourceSentence.trim() ? sourceSentence.trim() : null,
        source_page: sourcePage.trim() ? sourcePage.trim() : null,
        context_note: contextNote.trim() ? contextNote.trim() : null,
        reading_source_id: selectedReadingSourceId ? Number(selectedReadingSourceId) : null,
        source_title: !selectedReadingSourceId && newSourceTitle.trim() ? newSourceTitle.trim() : null,
        source_author: !selectedReadingSourceId && newSourceAuthor.trim() ? newSourceAuthor.trim() : null,
        source_kind: !selectedReadingSourceId && newSourceKind.trim() ? newSourceKind.trim() : null,
        source_reference:
          !selectedReadingSourceId && newSourceReference.trim() ? newSourceReference.trim() : null,
      });
      const createdSourceId = Number(createRes?.data?.reading_source_id);
      const usedSourceId = selectedReadingSourceId ? Number(selectedReadingSourceId) : createdSourceId;
      if (activePair?.id && Number.isFinite(usedSourceId) && usedSourceId > 0) {
        setCurrentSourceForPair(activePair.id, usedSourceId);
        setCurrentSourceId(usedSourceId);
      }

      setAddMsg("Word saved");
      // refresh summary and deck presence
      await load();

      // keep modal open for fast adding, but clear inputs
      setLearningText("");
      setNativeText("");
      setSourceSentence("");
      setSourcePage("");
      setContextNote("");
      setSelectedReadingSourceId(
        Number.isFinite(usedSourceId) && usedSourceId > 0 ? String(usedSourceId) : ""
      );
      setNewSourceTitle("");
      setNewSourceAuthor("");
      setNewSourceKind("");
      setNewSourceReference("");
      setDirtyNative(false);
      setPreviewMsg("");
    } catch (e2) {
      setAddMsg(extractError(e2));
    } finally {
      setAdding(false);
    }
  }

  useEffect(() => {
    if (activePairLoading) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePair?.id, activePairLoading, currentSourceId]);

  if (loading) return <p>Loading...</p>;

  const titleLeft = learningLang?.code || learningLang?.name || "Learning";
  const titleRight = nativeLang?.code || nativeLang?.name || "Translation";
  const primaryDeck = mainDeckCards[0] ?? null;
  const primaryDeckSummary = primaryDeck?.summary ?? null;
  const sectionCards = primaryDeck?.cards ?? [];
  const incompleteCards = sectionCards.filter((card) => {
    const missingMeaning = !String(card?.back || "").trim();
    const missingSentence = !String(card?.source_sentence || card?.example_sentence || "").trim();
    const missingSource = !card?.reading_source_id && !String(card?.source_title || "").trim();
    return missingMeaning || missingSentence || missingSource;
  });
  const hasStudyableCards = Number(primaryDeckSummary?.total_cards ?? sectionCards.length ?? 0) > 0;
  const currentSource =
    currentSourceId != null
      ? readingSources.find((source) => Number(source.id) === Number(currentSourceId)) ?? null
      : null;
  const selectedSource =
    selectedReadingSourceId != null && selectedReadingSourceId !== ""
      ? readingSources.find((source) => String(source.id) === String(selectedReadingSourceId)) ?? null
      : null;
  const editingSource =
    editReadingSourceId != null && editReadingSourceId !== ""
      ? readingSources.find((source) => String(source.id) === String(editReadingSourceId)) ?? null
      : null;
  const totalSources = readingSources.length;
  const totalSourceWords = readingSources.reduce(
    (sum, source) => sum + Number(source?.total_cards ?? 0),
    0
  );
  const totalDueAcrossSources = readingSources.reduce(
    (sum, source) => sum + Number(source?.due_cards ?? 0),
    0
  );
  const topSourcesByDue = [...readingSources]
    .sort((a, b) => Number(b?.due_cards ?? 0) - Number(a?.due_cards ?? 0))
    .slice(0, 3);

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", paddingBottom: 90 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          alignItems: "center",
          background: "#fff",
          border: "1px solid #ececec",
          borderRadius: 14,
          padding: "10px 12px",
        }}
      >
        <div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Active pair</div>
          <div style={{ fontWeight: 600 }}>{titleLeft} → {titleRight}</div>
          {primaryDeck ? <div style={{ fontSize: 12, opacity: 0.7 }}>Ready for reading review</div> : null}
        </div>
        <button style={{ width: 44, height: 44, borderRadius: 10 }} onClick={load} title="Refresh">
          ↻
        </button>
        <button
          style={{ minHeight: 40, borderRadius: 10, padding: "0 12px", fontWeight: 600 }}
          onClick={openAdd}
          title="Save word"
        >
          Save Word
        </button>
      </div>

      {error && (
        <pre style={{ padding: 12, background: "#ffecec" }}>{error}</pre>
      )}

      {!activePair ? (
        <div style={{ padding: 12, background: "#f5f5f5", marginTop: 14, opacity: 0.75 }}>
          Select an active pair to view your reading progress.
        </div>
      ) : null}

      {activePair && mainDeckCards.length === 0 ? (
        <div style={{ padding: 12, background: "#fff3cd", marginTop: 14 }}>
          Reading review is not ready for this pair yet.
        </div>
      ) : null}

      <div
        style={{
          marginTop: 14,
          border: "1px solid #e7e7e7",
          borderRadius: 16,
          background: "#fff",
          padding: 16,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Current source</div>
        {sourceWidgetError ? (
          <div style={{ fontSize: 12, color: "#b42318" }}>{sourceWidgetError}</div>
        ) : null}
        {!currentSource ? (
          <div style={{ fontSize: 13, opacity: 0.75 }}>
            No current source selected yet. Add the book or text you are reading to save words in context.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 6 }}>
            <div style={{ fontWeight: 600 }}>{currentSource.title}</div>
            {(currentSource.author || currentSource.kind) ? (
              <div style={{ fontSize: 13, opacity: 0.75 }}>
                {currentSource.author || "Unknown author"}
                {currentSource.kind ? ` · ${currentSource.kind}` : ""}
              </div>
            ) : null}
            <div style={{ fontSize: 13, opacity: 0.8 }}>
              Words: {Number(currentSource.total_cards ?? 0)} · Due: {Number(currentSource.due_cards ?? 0)}
            </div>
            {currentSource.last_added_at ? (
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                Last added: {new Date(currentSource.last_added_at).toLocaleString()}
              </div>
            ) : null}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <button onClick={() => setSourcePickerOpen(true)} style={{ minHeight: 36, borderRadius: 10, padding: "0 10px" }}>
            Change source
          </button>
          <button
            onClick={() => {
              if (!activePair?.id) return;
              clearCurrentSourceForPair(activePair.id);
              setCurrentSourceId(null);
              setSelectedReadingSourceId("");
            }}
            disabled={!currentSource}
            style={{ minHeight: 36, borderRadius: 10, padding: "0 10px", opacity: currentSource ? 1 : 0.5 }}
          >
            Clear
          </button>
        </div>
      </div>

      <div
        style={{
          marginTop: 14,
          border: "1px solid #e7e7e7",
          borderRadius: 16,
          background: "#fff",
          padding: 16,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>From your reading</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Sources</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totalSources}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Saved words</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totalSourceWords}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Due</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{totalDueAcrossSources}</div>
          </div>
        </div>
        {topSourcesByDue.length > 0 ? (
          <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
            {topSourcesByDue.map((source) => (
              <button
                key={source.id}
                onClick={() => nav(`/app/sources/${source.id}`)}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  border: "1px solid #e5e5e5",
                  borderRadius: 10,
                  padding: "8px 10px",
                  background: "#fff",
                }}
              >
                <span style={{ fontSize: 13, textAlign: "left" }}>{source.title}</span>
                <span style={{ fontSize: 12, opacity: 0.75 }}>Due {Number(source?.due_cards ?? 0)}</span>
              </button>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
            No source stats yet. Save words to build your reading overview.
          </div>
        )}
      </div>

      {primaryDeck ? (
        <div
          style={{
            marginTop: 14,
            border: "1px solid #e7e7e7",
            borderRadius: 16,
            background: "#fff",
            padding: 16,
          }}
        >
          <div style={{ fontSize: 14, opacity: 0.8 }}>{titleLeft} → {titleRight}</div>
          <div style={{ marginTop: 4, fontSize: 13, opacity: 0.7 }}>Review words from your reading</div>

          <div
            style={{
              marginTop: 14,
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: 10,
              textAlign: "center",
            }}
          >
            <div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>Weak memory</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{primaryDeckSummary?.total_new ?? "-"}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>Medium memory</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{primaryDeckSummary?.total_learning ?? "-"}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>Strong memory</div>
              <div style={{ fontSize: 26, fontWeight: 700 }}>{primaryDeckSummary?.total_mastered ?? "-"}</div>
            </div>
          </div>

          <button
            style={{
              marginTop: 14,
              width: "100%",
              minHeight: 48,
              borderRadius: 12,
              background: "#111",
              color: "#fff",
              border: "none",
              fontWeight: 600,
              opacity: hasStudyableCards ? 1 : 0.65,
            }}
            disabled={!hasStudyableCards}
            onClick={() => nav(`/app/study/${primaryDeck.deck.id}`)}
          >
            Start reading review
          </button>
          {!hasStudyableCards ? (
            <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
              Save a few words from your reading to start reviewing.
            </div>
          ) : null}
        </div>
      ) : null}

      {primaryDeck ? (
        <details style={{ marginTop: 14 }} open={wordsOpen} onToggle={(e) => setWordsOpen(e.currentTarget.open)}>
          <summary
            style={{
              listStyle: "none",
              cursor: "pointer",
              border: "1px solid #e5e5e5",
              borderRadius: 12,
              padding: "12px 14px",
              background: "#fff",
              fontWeight: 600,
            }}
          >
            Saved words ({sectionCards.length})
          </summary>
          <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
            {sectionCards.length === 0 ? (
              <div style={{ fontSize: 13, opacity: 0.7, padding: 8 }}>No saved words from your reading yet.</div>
            ) : (
              sectionCards.map((card) => {
                const isEditing =
                  editingDeckId === primaryDeck.deck.id && editingCardId === card.id;
                return (
                  <div
                    key={card.id}
                    style={{
                      border: "1px solid #eee",
                      borderRadius: 10,
                      padding: 8,
                      fontSize: 13,
                      background: "#fff",
                    }}
                  >
                    {isEditing ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <input
                          value={editFront}
                          onChange={(e) => setEditFront(e.target.value)}
                          style={{ width: "100%" }}
                          placeholder="Word"
                        />
                        <input
                          value={editBack}
                          onChange={(e) => setEditBack(e.target.value)}
                          style={{ width: "100%" }}
                          placeholder="Meaning"
                        />
                        <input
                          value={editExample}
                          onChange={(e) => setEditExample(e.target.value)}
                          style={{ width: "100%" }}
                          placeholder="Source sentence"
                        />
                        <details>
                          <summary style={{ cursor: "pointer", fontWeight: 600 }}>Source and advanced details</summary>
                          <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
                            <label>
                              Book or source
                              <select
                                value={editReadingSourceId}
                                onChange={(e) => setEditReadingSourceId(e.target.value)}
                                style={{ width: "100%" }}
                              >
                                {!card?.reading_source_id ? (
                                  <option value="">No linked source</option>
                                ) : null}
                                {readingSources.map((source) => (
                                  <option key={source.id} value={source.id}>
                                    {source.title}
                                    {source.author ? ` — ${source.author}` : ""}
                                  </option>
                                ))}
                              </select>
                            </label>
                            {editingSource ? (
                              <>
                                <div style={{ fontSize: 12, opacity: 0.75 }}>
                                  Source metadata will autofill from the linked source. You can still edit page and notes.
                                </div>
                                {renderSourceSummary(editingSource)}
                              </>
                            ) : (
                              <>
                                <label>
                                  Source title
                                  <input
                                    value={editSourceTitle}
                                    onChange={(e) => setEditSourceTitle(e.target.value)}
                                    style={{ width: "100%" }}
                                    placeholder="Book or text title"
                                  />
                                </label>
                                <label>
                                  Author
                                  <input
                                    value={editSourceAuthor}
                                    onChange={(e) => setEditSourceAuthor(e.target.value)}
                                    style={{ width: "100%" }}
                                    placeholder="Optional"
                                  />
                                </label>
                                <label>
                                  Kind
                                  <input
                                    value={editSourceKind}
                                    onChange={(e) => setEditSourceKind(e.target.value)}
                                    style={{ width: "100%" }}
                                    placeholder="book, article, essay..."
                                  />
                                </label>
                                <label>
                                  Reference
                                  <input
                                    value={editSourceReference}
                                    onChange={(e) => setEditSourceReference(e.target.value)}
                                    style={{ width: "100%" }}
                                    placeholder="Chapter, location, URL..."
                                  />
                                </label>
                              </>
                            )}
                            <label>
                              Source page
                              <input
                                value={editSourcePage}
                                onChange={(e) => setEditSourcePage(e.target.value)}
                                style={{ width: "100%" }}
                                placeholder="e.g. p. 42"
                              />
                            </label>
                            <label>
                              Context note
                              <input
                                value={editContextNote}
                                onChange={(e) => setEditContextNote(e.target.value)}
                                style={{ width: "100%" }}
                                placeholder="Short note (optional)"
                              />
                            </label>
                          </div>
                        </details>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button
                            style={{ padding: "6px 10px" }}
                            disabled={busyCardAction || !editFront.trim() || !editBack.trim()}
                            onClick={() => updateCard(primaryDeck.deck.id, card)}
                          >
                            Update
                          </button>
                          <button style={{ padding: "6px 10px" }} onClick={cancelEdit} disabled={busyCardAction}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: "grid", gap: 4 }}>
                        <div><strong>Word:</strong> {card.front}</div>
                        <div><strong>Meaning:</strong> {card.back}</div>
                        {card.example_sentence ? (
                          <div><strong>Source sentence:</strong> {card.example_sentence}</div>
                        ) : null}
                        <div><strong>Memory strength:</strong> {memoryStrengthFromCard(card)}</div>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                          <button
                            style={{ padding: "6px 10px" }}
                            disabled={busyCardAction}
                            onClick={() => startEdit(primaryDeck.deck.id, card)}
                          >
                            Edit
                          </button>
                          <button
                            style={{ padding: "6px 10px" }}
                            disabled={busyCardAction}
                            onClick={() => deleteCard(primaryDeck.deck.id, card.id)}
                          >
                            Delete
                          </button>
                          <button
                            style={{ padding: "6px 10px" }}
                            disabled={busyCardAction}
                            onClick={() => resetProgress(primaryDeck.deck.id, card.id)}
                          >
                            Reset progress
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </details>
      ) : null}

      {primaryDeck && incompleteCards.length > 0 ? (
        <details style={{ marginTop: 14 }} open={incompleteOpen} onToggle={(e) => setIncompleteOpen(e.currentTarget.open)}>
          <summary
            style={{
              listStyle: "none",
              cursor: "pointer",
              border: "1px solid #e5e5e5",
              borderRadius: 12,
              padding: "12px 14px",
              background: "#fff",
              fontWeight: 600,
            }}
          >
            Reading notes to complete ({incompleteCards.length})
          </summary>
          <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
            {incompleteCards.map((card) => {
              const missing = [];
              if (!String(card?.back || "").trim()) missing.push("meaning");
              if (!String(card?.source_sentence || card?.example_sentence || "").trim()) missing.push("sentence");
              if (!card?.reading_source_id && !String(card?.source_title || "").trim()) missing.push("source");
              return (
                <div
                  key={`incomplete-${card.id}`}
                  style={{
                    border: "1px solid #eee",
                    borderRadius: 10,
                    padding: 10,
                    fontSize: 13,
                    background: "#fff",
                    display: "grid",
                    gap: 6,
                  }}
                >
                  <div><strong>{card.front || "Untitled word"}</strong></div>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>Missing: {missing.join(", ")}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button
                      style={{ padding: "6px 10px" }}
                      onClick={() => {
                        if (card?.reading_source_id) {
                          nav(`/app/sources/${card.reading_source_id}?editCardId=${card.id}`);
                          return;
                        }
                        setWordsOpen(true);
                        setIncompleteOpen(true);
                        startEdit(primaryDeck.deck.id, card);
                      }}
                    >
                      Complete now
                    </button>
                    <button
                      style={{ padding: "6px 10px" }}
                      onClick={() => {
                        if (card?.reading_source_id) {
                          nav(`/app/decks/${card.reading_source_id}`);
                          return;
                        }
                        nav("/app/decks");
                      }}
                    >
                      Open source
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </details>
      ) : null}

      <Modal open={sourcePickerOpen} title="Choose source" onClose={() => setSourcePickerOpen(false)}>
        <select
          style={{
            width: "100%",
            borderRadius: 10,
            border: "1px solid #d1d5db",
            background: "#fff",
            padding: "10px 12px",
            fontSize: 14,
            outline: "none",
          }}
          value={currentSourceId ? String(currentSourceId) : ""}
          disabled={switchingSource || !readingSources.length}
          onChange={(e) => {
            const nextId = e.target.value;
            if (!activePair?.id || !nextId) return;
            if (String(currentSourceId) === String(nextId)) {
              setSourcePickerOpen(false);
              return;
            }
            setSwitchingSource(true);
            try {
              setCurrentSourceForPair(activePair.id, Number(nextId));
              setCurrentSourceId(Number(nextId));
              setSelectedReadingSourceId(String(nextId));
              setSourcePickerOpen(false);
            } finally {
              setSwitchingSource(false);
            }
          }}
        >
          {!currentSource ? (
            <option value="" disabled>
              Select a source
            </option>
          ) : null}
          {readingSources.map((source) => (
            <option key={source.id} value={String(source.id)}>
              {source.title}
              {source.author ? ` · ${source.author}` : ""}
            </option>
          ))}
        </select>
      </Modal>

      <button
        onClick={openAdd}
        disabled={!activePair}
        title="Save word"
        style={{
          position: "fixed",
          right: 18,
          bottom: 92,
          width: 52,
          height: 52,
          borderRadius: "50%",
          border: "none",
          background: "#111",
          color: "#fff",
          fontSize: 28,
          lineHeight: 1,
        }}
      >
        +
      </button>

      <Modal open={addOpen} title="Save word" onClose={() => setAddOpen(false)}>
        <form onSubmit={submitAdd} style={{ display: "grid", gap: 12 }}>
          <label>
            Word ({titleLeft})
            <input
              value={learningText}
              onChange={(e) => setLearningText(e.target.value)}
              style={{ width: "100%" }}
              placeholder="e.g. hello"
              autoFocus
            />
          </label>

          <label>
            Translation / meaning ({titleRight})
            <input
              value={nativeText}
              onChange={(e) => {
                setNativeText(e.target.value);
                setDirtyNative(true);
              }}
              style={{ width: "100%" }}
              placeholder="Auto-filled when available"
            />
          </label>
          <div style={{ fontSize: 12, opacity: 0.75 }}>
            {previewLoading ? "Looking up meaning..." : "Meaning auto-fills when available. You can edit it."}
            {previewMsg ? <span style={{ color: "crimson", marginLeft: 8 }}>{previewMsg}</span> : null}
          </div>

          <label>
            Sentence (optional)
            <input
              value={sourceSentence}
              onChange={(e) => setSourceSentence(e.target.value)}
              style={{ width: "100%" }}
              placeholder="Sentence where you found this word"
            />
          </label>

          <details>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>Source and advanced details</summary>
            <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
              <label>
                Book or source (optional)
                <select
                  value={selectedReadingSourceId}
                  onChange={(e) => handleSourceSelectionChange(e.target.value)}
                  style={{ width: "100%" }}
                >
                  <option value="">No source yet</option>
                  {readingSources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.title}
                      {source.author ? ` — ${source.author}` : ""}
                    </option>
                  ))}
                </select>
              </label>
              {selectedSource ? (
                <>
                  <div style={{ fontSize: 12, opacity: 0.75 }}>
                    Source metadata will autofill from the current linked source. You can still edit page and notes.
                  </div>
                  {renderSourceSummary(selectedSource)}
                </>
              ) : null}
              <label>
                Source page
                <input
                  value={sourcePage}
                  onChange={(e) => setSourcePage(e.target.value)}
                  style={{ width: "100%" }}
                  placeholder="e.g. p. 42"
                />
              </label>
              <label>
                Context note
                <input
                  value={contextNote}
                  onChange={(e) => setContextNote(e.target.value)}
                  style={{ width: "100%" }}
                  placeholder="Short note (optional)"
                />
              </label>
              {!selectedReadingSourceId ? (
                <>
                  <label>
                    Source title
                    <input
                      value={newSourceTitle}
                      onChange={(e) => setNewSourceTitle(e.target.value)}
                      style={{ width: "100%" }}
                      placeholder="Book or text title"
                    />
                  </label>
                  <label>
                    Author
                    <input
                      value={newSourceAuthor}
                      onChange={(e) => setNewSourceAuthor(e.target.value)}
                      style={{ width: "100%" }}
                      placeholder="Optional"
                    />
                  </label>
                  <label>
                    Kind
                    <input
                      value={newSourceKind}
                      onChange={(e) => setNewSourceKind(e.target.value)}
                      style={{ width: "100%" }}
                      placeholder="book, article, essay..."
                    />
                  </label>
                  <label>
                    Reference
                    <input
                      value={newSourceReference}
                      onChange={(e) => setNewSourceReference(e.target.value)}
                      style={{ width: "100%" }}
                      placeholder="Chapter, location, URL..."
                    />
                  </label>
                </>
              ) : null}
            </div>
          </details>

          <div style={{ display: "flex", gap: 10 }}>
            <button disabled={adding || !learningText.trim()}>
              {adding ? "Saving..." : "Save word"}
            </button>
            <button type="button" onClick={() => setAddOpen(false)}>
              Close
            </button>
          </div>

          {addMsg && (
            <pre style={{ padding: 12, background: "#f5f5f5" }}>{addMsg}</pre>
          )}
        </form>
      </Modal>
    </div>
  );
}
