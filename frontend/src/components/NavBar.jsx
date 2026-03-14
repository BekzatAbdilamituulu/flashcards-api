import { Link, useNavigate } from "react-router-dom";
import { AuthApi } from "../api/endpoints";
import { tokens } from "../api/tokens";

export default function NavBar() {
  const nav = useNavigate();

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
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        marginBottom: 16,
        paddingBottom: 10,
        borderBottom: "1px solid #e5e5e5",
      }}
    >
      <div style={{ display: "flex", gap: 12 }}>
        <Link to="/app">Dashboard</Link>
        <Link to="/app/sources">Sources</Link>
        <Link to="/app/profile">Profile</Link>
        <Link to="/app/progress">Progress</Link>
      </div>
      <button onClick={onLogout}>Logout</button>
    </div>
  );
}
