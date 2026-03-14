import { useEffect, useMemo, useState } from "react";
import { UsersApi, ProgressApi } from "../api/endpoints";
import { useActivePair } from "../context/ActivePairContext";

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

export default function ProfilePage() {
  const { activePair, loading: activePairLoading } = useActivePair();
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
        setSummary(null);
        setStreak(null);
        setTodayAdded(null);
        setMonthly(null);
        return;
      }

      const params = { pair_id: activePair.id };
      const [
        userRes,
        summaryRes,
        streakRes,
        todayAddedRes,
        monthlyRes,
      ] = await Promise.all([
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

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
      <h2>Profile</h2>

      {user && (
        <div style={{ marginBottom: 20 }}>
          <strong>{user.username}</strong>
          <div>Daily card target: {user.daily_card_target}</div>
          <div>Daily new target: {user.daily_new_target}</div>
        </div>
      )}

      {!activePairLoading && !activePair ? (
        <div style={{ marginBottom: 20, opacity: 0.75 }}>
          Select an active pair to view progress stats.
        </div>
      ) : null}

      {streak && (
        <div style={{ marginBottom: 20 }}>
          <h3>🔥 Streak</h3>
          <div>Current: {streak.current_streak}</div>
          <div>Best: {streak.best_streak}</div>
        </div>
      )}

      {summary && (
        <div style={{ marginBottom: 20 }}>
          <h3>Summary</h3>
          <div>Total cards: {summary.total_cards}</div>
          <div>Strong memory: {summary.total_mastered}</div>
          <div>Medium memory: {summary.total_learning}</div>
          <div>Weak memory: {summary.total_new}</div>
        </div>
      )}

      {todayAdded && (
        <div style={{ marginBottom: 20 }}>
          <h3>📌 Today Added</h3>
          <div>{todayAdded.count} cards added today</div>
        </div>
      )}

      <div>
        <h3>📅 {year} - {month}</h3>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, 1fr)",
            gap: 6,
            maxWidth: 400,
          }}
        >
          {monthMatrix.map((date, i) => {
            if (!date)
              return <div key={i} style={{ height: 40 }} />;

            const key = formatDate(date);
            const count = monthlyMap[key] || 0;

            return (
              <div
                key={key}
                title={`${key}: ${count} cards`}
                style={{
                  height: 40,
                  background: colorForCount(count),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  borderRadius: 6,
                }}
              >
                {date.getDate()}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
