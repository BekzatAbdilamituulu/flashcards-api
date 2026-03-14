import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ProgressApi } from "../api/endpoints";
import { useActivePair } from "../context/ActivePairContext";
import { memoryStrengthFromStatus } from "../utils/memoryStrength";

function extractError(e) {
  if (e?.response?.data) return JSON.stringify(e.response.data);
  return e?.message ?? "Request failed";
}

function formatDateISO(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function shortLabel(dateStr) {
  const [, m, d] = dateStr.split("-");
  return `${m}/${d}`;
}

export default function ProgressPage() {
  const { activePair, loading: activePairLoading } = useActivePair();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [daily, setDaily] = useState([]);

  const chartData = useMemo(() => {
    return daily.map((d) => ({
      ...d,
      label: shortLabel(d.date),
    }));
  }, [daily]);

  async function load() {
    if (!activePair?.id) {
      setSummary(null);
      setDaily([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    const to = new Date();
    const from = new Date();
    from.setDate(to.getDate() - 13);

    try {
      const params = { pair_id: activePair.id };
      const [summaryRes, dailyRes] = await Promise.all([
        ProgressApi.summary(params),
        ProgressApi.daily(formatDateISO(from), formatDateISO(to), params),
      ]);

      setSummary(summaryRes.data);
      setDaily(dailyRes.data?.items ?? []);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activePairLoading) {
      setLoading(true);
      return;
    }
    if (!activePair?.id) {
      setSummary(null);
      setDaily([]);
      setLoading(false);
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePair?.id, activePairLoading]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h1 style={{ marginTop: 0 }}>Reading growth</h1>
        <button onClick={load} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && <pre style={{ padding: 12, background: "#ffecec" }}>{error}</pre>}

      {loading || activePairLoading ? <p>Loading...</p> : null}

      {!loading && !activePairLoading && !activePair ? (
        <p style={{ opacity: 0.75 }}>Select an active pair to view progress.</p>
      ) : null}

      {!loading && summary ? (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
              marginBottom: 16,
            }}
          >
            <div style={{ background: "#f5f5f5", padding: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>Words reviewed today</div>
              <strong>{summary.today_cards_done}</strong>
            </div>
            <div style={{ background: "#f5f5f5", padding: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>Review answers</div>
              <strong>{summary.today_reviews_done}</strong>
            </div>
            <div style={{ background: "#f5f5f5", padding: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>New words introduced</div>
              <strong>{summary.today_new_done}</strong>
            </div>
            <div style={{ background: "#f5f5f5", padding: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>Streak</div>
              <strong>{summary.current_streak}</strong>
            </div>
            <div style={{ background: "#f5f5f5", padding: 12 }}>
              <div style={{ opacity: 0.7, fontSize: 12 }}>Words saved today</div>
              <strong>{summary.today_added_cards}</strong>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, fontSize: 13, opacity: 0.8 }}>Memory Strength</div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: 10,
              }}
            >
              <div style={{ background: "#f5f5f5", padding: 12 }}>
                <div style={{ opacity: 0.7, fontSize: 12 }}>{memoryStrengthFromStatus("new")}</div>
                <strong>{summary.total_new ?? 0}</strong>
              </div>
              <div style={{ background: "#f5f5f5", padding: 12 }}>
                <div style={{ opacity: 0.7, fontSize: 12 }}>{memoryStrengthFromStatus("learning")}</div>
                <strong>{summary.total_learning ?? 0}</strong>
              </div>
              <div style={{ background: "#f5f5f5", padding: 12 }}>
                <div style={{ opacity: 0.7, fontSize: 12 }}>{memoryStrengthFromStatus("mastered")}</div>
                <strong>{summary.total_mastered ?? 0}</strong>
              </div>
            </div>
          </div>
        </>
      ) : null}

      {!loading && !error ? (
        <div style={{ width: "100%", height: 320, background: "#fff", border: "1px solid #eee", padding: 8 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 12, right: 16, left: 4, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cards_done" stroke="#1f77b4" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="reviews_done" stroke="#2ca02c" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="new_done" stroke="#ff7f0e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </div>
  );
}
