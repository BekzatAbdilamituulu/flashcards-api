import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthApi } from "../api/endpoints";
import { tokens } from "../api/tokens";
import Button from "../components/Button";
import Card from "../components/Card";
import GoogleSignInButton from "../components/GoogleSignInButton";
import Input from "../components/Input";
import { completeSignIn } from "../utils/completeSignIn";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

export default function LoginPage() {
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");

    try {
      const res = await AuthApi.login(username.trim(), password);
      await completeSignIn(res.data, nav);
    } catch (e2) {
      tokens.clear();
      setError(extractError(e2));
    } finally {
      setBusy(false);
    }
  }

  async function onGoogleCredential(idToken) {
    setBusy(true);
    setError("");

    try {
      const res = await AuthApi.google(idToken);
      await completeSignIn(res.data, nav);
    } catch (e2) {
      tokens.clear();
      setError(extractError(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 flex items-center justify-center">
      <Card className="w-full max-w-[400px]">
        <h1 className="text-2xl font-bold">Login</h1>
        <p className="mt-1 text-sm text-gray-500">Welcome back to your reading vocabulary companion.</p>

        <form onSubmit={onSubmit} className="mt-6 grid gap-4">
          <label className="grid gap-2">
            <span className="text-sm text-gray-700">Username</span>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm text-gray-700">Password</span>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>

          <Button type="submit" variant="primary" disabled={busy} className="w-full">
            {busy ? "Logging in..." : "Login"}
          </Button>

          <div className="grid gap-2">
            <div className="relative py-1 text-center text-xs uppercase tracking-[0.2em] text-gray-400">
              <span className="bg-white px-2">Or</span>
            </div>
            <GoogleSignInButton
              disabled={busy}
              onCredential={onGoogleCredential}
              onError={setError}
            />
          </div>

          {error ? (
            <pre className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</pre>
          ) : null}
        </form>

        <p className="mt-4 text-sm text-gray-500">
          No account?{" "}
          <Link to="/register" className="font-medium text-black underline">
            Register
          </Link>
        </p>
      </Card>
    </div>
  );
}
