import { UsersApi } from "../api/endpoints";
import { tokens } from "../api/tokens";

export async function completeSignIn(tokenPayload, navigate) {
  tokens.set(tokenPayload);

  try {
    const pairsRes = await UsersApi.pairs();
    const pairs = pairsRes.data ?? [];

    if (pairs.length === 0) navigate("/onboarding", { replace: true });
    else navigate("/app", { replace: true });
  } catch (error) {
    tokens.clear();
    throw error;
  }
}
