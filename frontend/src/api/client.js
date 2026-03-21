import axios from "axios";
import { tokens } from "./tokens";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const access = tokens.getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let refreshingPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    if (error?.response?.status !== 401) return Promise.reject(error);
    if (original?._retry) return Promise.reject(error);
    original._retry = true;

    const refresh = tokens.getRefresh();
    if (!refresh) {
      tokens.clear();
      return Promise.reject(error);
    }

    try {
      if (!refreshingPromise) {
        refreshingPromise = axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refresh },
          { timeout: 15000 }
        );
      }

      const refreshRes = await refreshingPromise;
      refreshingPromise = null;

      tokens.set(refreshRes.data);

      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${tokens.getAccess()}`;
      return api(original);
    } catch (e) {
      refreshingPromise = null;
      tokens.clear();
      return Promise.reject(e);
    }
  }
);
