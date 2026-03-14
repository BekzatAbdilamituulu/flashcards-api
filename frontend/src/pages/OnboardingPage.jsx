import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DecksApi, LanguagesApi, UsersApi } from "../api/endpoints";
import PairForm from "../components/PairForm";
import Card from "../components/Card";
import { useActivePair } from "../context/ActivePairContext";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function findLangIdByCode(langs, code) {
  const targetCode = String(code || "").toLowerCase();
  const hit = langs.find((language) => String(language.code || "").toLowerCase() === targetCode);
  return hit ? String(hit.id) : "";
}

export default function OnboardingPage() {
  const nav = useNavigate();
  const { refreshPairs } = useActivePair();

  const [languages, setLanguages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [initialLearningId, setInitialLearningId] = useState("");
  const [initialTranslationId, setInitialTranslationId] = useState("");

  async function loadLanguages() {
    setLoading(true);
    setError("");

    try {
      const res = await LanguagesApi.list();
      const langs = res.data ?? [];
      setLanguages(langs);

      const en = findLangIdByCode(langs, "en");
      const ru = findLangIdByCode(langs, "ru");

      if (en && ru) {
        setInitialLearningId(en);
        setInitialTranslationId(ru);
      } else if (langs.length >= 2) {
        setInitialLearningId(String(langs[0].id));
        const second = langs.find((item) => item.id !== langs[0].id);
        setInitialTranslationId(second ? String(second.id) : String(langs[1].id));
      }
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit({ learningId, translationId }) {
    setSaving(true);
    setError("");

    try {
      await UsersApi.setDefaults(learningId, translationId);
      await UsersApi.addPair(learningId, translationId);

      const source = languages.find((language) => Number(language.id) === Number(learningId));
      const target = languages.find((language) => Number(language.id) === Number(translationId));
      const sourceLabel = (source?.code || source?.name || "source").toLowerCase();
      const targetLabel = (target?.code || target?.name || "target").toLowerCase();

      await DecksApi.create({
        name: `My source (${sourceLabel}→${targetLabel})`,
        source_language_id: learningId,
        target_language_id: translationId,
        deck_type: "users",
      }).catch(() => {});

      await refreshPairs();
      nav("/app", { replace: true });
    } catch (e) {
      setError(extractError(e));
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadLanguages();
  }, []);

  if (loading) return <p>Loading...</p>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Learn languages through reading</h1>
        <p className="mt-1 text-sm text-gray-600">
          Save new words while reading books and remember them long-term.
        </p>
      </div>

      <Card className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">Keep words in context</h2>
          <p className="text-sm text-gray-600">
            Add the sentence where you found the word. Context helps memory.
          </p>
        </div>
        <div>
          <h2 className="text-base font-semibold">Review calmly</h2>
          <p className="text-sm text-gray-600">
            A simple reading review system helps you remember without pressure.
          </p>
        </div>
        <div>
          <h2 className="text-base font-semibold">Build your personal vocabulary library</h2>
          <p className="text-sm text-gray-600">
            Organize words by books, articles, and sources.
          </p>
        </div>
      </Card>

      <Card>
        <PairForm
          languages={languages}
          initialLearningId={initialLearningId}
          initialTranslationId={initialTranslationId}
          submitLabel="Start reading smarter"
          saving={saving}
          error={error}
          onSubmit={handleSubmit}
        />
      </Card>
    </div>
  );
}
