import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { AuthApi } from "../api/endpoints";
import { tokens } from "../api/tokens";
import GoogleSignInButton from "../components/GoogleSignInButton";
import { completeSignIn } from "../utils/completeSignIn";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

export default function WelcomePage() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onGoogleCredential(idToken) {
    setBusy(true);
    setError("");

    try {
      const res = await AuthApi.google(idToken);
      await completeSignIn(res.data, nav);
    } catch (e) {
      tokens.clear();
      setError(extractError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto min-h-screen w-full max-w-3xl px-6 py-10 text-stone-900">
      <section className="space-y-4 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
        <h1 className="text-3xl font-bold leading-tight">
          Remember the words you discover while reading.
        </h1>
        <p className="text-base text-stone-700">
          A calm, focused vocabulary companion for people who learn languages through books.
        </p>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            to="/register"
            className="rounded-xl bg-black px-4 py-2 text-sm font-medium text-white"
          >
            Start building your reading vocabulary
          </Link>
          <Link
            to="/login"
            className="rounded-xl border border-stone-300 px-4 py-2 text-sm font-medium text-stone-800"
          >
            Save words from your reading
          </Link>
        </div>

        <div className="pt-2">
          <GoogleSignInButton
            disabled={busy}
            onCredential={onGoogleCredential}
            onError={setError}
          />
        </div>

        {error ? (
          <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
        ) : null}
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">Why reading learners struggle</h2>
          <ul className="mt-3 space-y-2 text-sm text-stone-700">
            <li>New words are easy to forget.</li>
            <li>Notes get scattered across books and apps.</li>
            <li>Dictionary lookups interrupt reading flow.</li>
            <li>Meaning is lost without the original sentence.</li>
          </ul>
        </article>

        <article className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">A focused solution</h2>
          <ul className="mt-3 space-y-2 text-sm text-stone-700">
            <li>Capture vocabulary in seconds.</li>
            <li>Keep the sentence where you found it.</li>
            <li>Review with focus and at your own pace.</li>
            <li>Build a personal, intellectual dictionary by source.</li>
          </ul>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-stone-200 bg-white p-5 text-sm text-stone-700 shadow-sm">
        <p>
          Learn at your pace. Grow your vocabulary gradually. A quiet tool for deep learners.
        </p>
        <div className="mt-4">
          <Link to="/register" className="font-medium underline">
            Create your personal book vocabulary
          </Link>
        </div>
      </section>
    </div>
  );
}
