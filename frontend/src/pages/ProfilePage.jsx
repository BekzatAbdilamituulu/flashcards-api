import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UsersApi, ProgressApi, AuthApi } from "../api/endpoints";
import { tokens } from "../api/tokens";
import { useActivePair } from "../context/ActivePairContext";
import Button from "../components/Button";
import Card from "../components/Card";
import Layout from "../components/Layout";

function formatDate(d) {
  return d.toISOString().split("T")[0];
}

function getMonthMatrix(year, month) {
  const first = new Date(year, month - 1, 1);
  const last = new Date(year, month, 0);

  const startDay = first.getDay(); // 0=Sun
  const daysInMonth = last.getDate();

  const cells = [];
  for (let i = 0; i < startDay; i++) cells.push(null);

  for (let d = 1; d <= daysInMonth; d++) {
    cells.push(new Date(year, month - 1, d));
  }

  return cells;
}

function colorForCount(count) {
  if (!count) return "#eee";
  if (count < 5) return "#c6e48b";
  if (count < 10) return "#7bc96f";
  if (count < 20) return "#239a3b";
  return "#196127";
}

function textClassForCount(count) {
  // Use white text for darker cells.
  return count >= 10 ? "text-white" : "text-gray-900";
}

export default function ProfilePage() {
  const nav = useNavigate();
  const { activePair, loading: activePairLoading } = useActivePair();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const [summary, setSummary] = useState(null);
  const [streak, setStreak] = useState(null);
  const [todayAdded, setTodayAdded] = useState(null);
  const [monthly, setMonthly] = useState(null);

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;

  useEffect(() => {
    async function load() {
      if (!activePair?.id) {
        setLoading(false);
        setError("");
        setUser(null);
        setSummary(null);
        setStreak(null);
        setTodayAdded(null);
        setMonthly(null);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const params = { pair_id: activePair.id };
        const [userRes, summaryRes, streakRes, todayAddedRes, monthlyRes] = await Promise.all([
          UsersApi.me(),
          ProgressApi.summary(params),
          ProgressApi.streak(params),
          ProgressApi.todayAdded(params),
          ProgressApi.monthly(year, month, params),
        ]);

        setUser(userRes.data);
        setSummary(summaryRes.data);
        setStreak(streakRes.data);
        setTodayAdded(todayAddedRes.data);
        setMonthly(monthlyRes.data);
      } catch (e) {
        setError(e?.message ?? "Failed to load profile");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [year, month, activePair?.id]);

  const monthMatrix = useMemo(() => {
    return getMonthMatrix(year, month);
  }, [year, month]);

  const monthlyMap = useMemo(() => {
    const map = {};
    monthly?.items?.forEach((d) => {
      map[d.date] = d.cards_done;
    });
    return map;
  }, [monthly]);

  async function onLogout() {
    const refresh = tokens.getRefresh();
    try {
      if (refresh) {
        await AuthApi.logout(refresh);
      }
    } catch {
      // best-effort logout; continue with local token cleanup
    } finally {
      tokens.clear();
      nav("/login", { replace: true });
    }
  }

  return (
    <Layout className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Profile</h1>
        <p className="text-sm text-gray-600">
          Your learning goals and progress across the active pair.
        </p>
      </div>

      {!activePairLoading && !activePair ? (
        <Card>
          <p className="text-sm text-gray-700">Select an active pair to view progress stats.</p>
        </Card>
      ) : null}

      {error ? (
        <pre className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</pre>
      ) : null}

      {activePair?.id && loading ? (
        <Card>
          <p className="text-sm text-gray-700">Loading profile…</p>
        </Card>
      ) : null}

      {user ? (
        <Card>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="text-sm font-medium text-gray-500">Signed in as</div>
              <div className="text-xl font-semibold text-gray-900">{user.username}</div>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
                  <span className="text-gray-600">Daily card target</span>
                  <div className="font-semibold text-gray-900">{user.daily_card_target}</div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
                  <span className="text-gray-600">Daily new target</span>
                  <div className="font-semibold text-gray-900">{user.daily_new_target}</div>
                </div>
              </div>
            </div>

            <div className="shrink-0">
              <Button variant="secondary" onClick={onLogout}>
                Logout
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {streak ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <h2 className="text-sm font-medium text-gray-500">Streak</h2>
            <div className="mt-2">
              <div className="text-3xl font-semibold text-gray-900">{streak.current_streak}</div>
              <div className="mt-1 text-sm text-gray-600">Current</div>
            </div>
            <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div className="text-xs text-gray-600">Best</div>
              <div className="text-lg font-semibold text-gray-900">{streak.best_streak}</div>
            </div>
          </Card>

          {summary ? (
            <Card className="lg:col-span-2">
              <h2 className="text-sm font-medium text-gray-500">Summary</h2>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="text-xs text-gray-600">Total cards</div>
                  <div className="text-xl font-semibold text-gray-900">{summary.total_cards}</div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="text-xs text-gray-600">Strong memory</div>
                  <div className="text-xl font-semibold text-gray-900">{summary.total_mastered}</div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="text-xs text-gray-600">Medium memory</div>
                  <div className="text-xl font-semibold text-gray-900">{summary.total_learning}</div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="text-xs text-gray-600">Weak memory</div>
                  <div className="text-xl font-semibold text-gray-900">{summary.total_new}</div>
                </div>
              </div>
            </Card>
          ) : (
            <Card className="lg:col-span-2">
              <h2 className="text-sm font-medium text-gray-500">Summary</h2>
              <p className="mt-2 text-sm text-gray-600">Not enough data yet.</p>
            </Card>
          )}
        </div>
      ) : null}

      {todayAdded ? (
        <Card>
          <h2 className="text-sm font-medium text-gray-500">Today Added</h2>
          <div className="mt-2 text-3xl font-semibold text-gray-900">{todayAdded.count}</div>
          <div className="mt-1 text-sm text-gray-600">cards added today</div>
        </Card>
      ) : null}

      {monthly ? (
        <Card>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-sm font-medium text-gray-500">Monthly progress</h2>
              <div className="mt-1 text-xl font-semibold text-gray-900">
                {year} - {month}
              </div>
            </div>

            <div className="text-xs text-gray-600">
              Each cell shows number of cards done that day.
            </div>
          </div>

          <div className="mt-4">
            <div className="grid grid-cols-7 gap-2">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d} className="px-1 text-center text-[11px] font-medium text-gray-500">
                  {d}
                </div>
              ))}
            </div>

            <div className="mt-2 grid grid-cols-7 gap-2">
              {monthMatrix.map((date, i) => {
                if (!date) return <div key={`empty-${i}`} className="h-9" />;

                const key = formatDate(date);
                const count = monthlyMap[key] || 0;
                const bg = colorForCount(count);

                return (
                  <div
                    key={key}
                    role="img"
                    aria-label={`${key}: ${count} cards done`}
                    title={`${key}: ${count} cards`}
                    className={[
                      "flex h-9 items-center justify-center rounded-md text-xs font-semibold",
                      textClassForCount(count),
                    ].join(" ")}
                    style={{ background: bg }}
                  >
                    {date.getDate()}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-gray-600">
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: colorForCount(0) }} />
              0
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: colorForCount(4) }} />
              1-4
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: colorForCount(9) }} />
              5-9
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: colorForCount(19) }} />
              10-19
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: colorForCount(20) }} />
              20+
            </div>
          </div>
        </Card>
      ) : null}
    </Layout>
  );
}
