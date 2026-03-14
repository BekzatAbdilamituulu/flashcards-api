import { api } from "./client";

export const API_PAGE_LIMIT = 200;

/**
 * @typedef {Object} DeckPayload
 * @property {string} [name]
 * @property {number} [pair_id]
 * @property {number} [source_language_id]
 * @property {number} [target_language_id]
 * @property {string} [source_type]
 * @property {string} [author_name]
 */

/**
 * @typedef {Object} CardPayload
 * @property {string} [front]
 * @property {string} [back]
 * @property {string|null} [example_sentence]
 * @property {string|null} [content_kind]
 * @property {string|null} [source_sentence]
 * @property {string|null} [source_page]
 * @property {string|null} [context_note]
 */

export const AuthApi = {
  register: (username, password) =>
    api.post("/api/v1/auth/register", { username, password }),
  login: (username, password) =>
    api.post("/api/v1/auth/login-json", { username, password }),
  refresh: (payload) => api.post("/api/v1/auth/refresh", payload),
  logout: (refresh_token) => api.post("/api/v1/auth/logout", { refresh_token }),
};

export const UsersApi = {
  me: () => api.get("/api/v1/users/me"),
  pairs: () => api.get("/api/v1/users/me/learning-pairs"),
  defaultPair: () => api.get("/api/v1/users/me/default-learning-pair"),
  setDefaultPair: (pairId) => api.put(`/api/v1/users/me/learning-pairs/${pairId}/default`),
  setDefaults: (learningId, nativeId) =>
    api.put("/api/v1/users/me/languages", {
      default_source_language_id: learningId,
      default_target_language_id: nativeId,
    }),
  addPair: (learningId, nativeId) =>
    api.post("/api/v1/users/me/learning-pairs", {
      source_language_id: learningId,
      target_language_id: nativeId,
      make_default: true,
    }),
};

export const LanguagesApi = {
  list: () => api.get("/api/v1/languages"),
};

export const DecksApi = {
  list: (limit = 50, offset = 0, params = {}) =>
    api.get("/api/v1/decks", { params: { limit, offset, ...params } }),
  /** @param {DeckPayload} payload */
  create: (payload) => api.post("/api/v1/decks", payload),
  get: (deckId) => api.get(`/api/v1/decks/${deckId}`),
  /** @param {DeckPayload} payload */
  update: (deckId, payload) => api.patch(`/api/v1/decks/${deckId}`, payload),
  delete: (deckId) => api.delete(`/api/v1/decks/${deckId}`),
};

export const CardsApi = {
  list: (deckId, limit = 50, offset = 0, params = {}) =>
    api.get(`/api/v1/decks/${deckId}/cards`, { params: { limit, offset, ...params } }),
  /** @param {CardPayload} payload */
  create: (deckId, payload) => api.post(`/api/v1/decks/${deckId}/cards`, payload),
  /** @param {CardPayload} payload */
  update: (deckId, cardId, payload) =>
    api.patch(`/api/v1/decks/${deckId}/cards/${cardId}`, payload),
  delete: (deckId, cardId) => api.delete(`/api/v1/decks/${deckId}/cards/${cardId}`),
  reset: (deckId, cardId) => api.post(`/api/v1/decks/${deckId}/cards/${cardId}/reset`),
};

export const ProgressApi = {
  summary: (params = {}) =>
    api.get("/api/v1/progress/summary", { params }),
  streak: (params = {}) => api.get("/api/v1/progress/streak", { params }),
  daily: (fromDate, toDate, params = {}) =>
    api.get("/api/v1/progress/daily", {
      params: { from_date: fromDate, to_date: toDate, ...params },
    }),
    todayAdded: (params = {}) =>
      api.get("/api/v1/progress/today-added", { params }),

    monthly: (year, month, params = {}) =>
      api.get("/api/v1/progress/month", {
        params: { year, month, ...params },
      }),
};

export const InboxApi = {
  addWord: (payload) => api.post("/api/v1/inbox/word", payload),
  bulkImport: (payload) => api.post("/api/v1/inbox/bulk", payload),
};

export const AutoApi = {
  preview: (payload) => api.post("/api/v1/auto/preview", payload),
};

export const StudyApi = {
  next: (deckId, params = {}) => api.get(`/api/v1/study/decks/${deckId}/next`, { params }),
  status: (deckId, params = {}) => api.get(`/api/v1/study/decks/${deckId}/status`, { params }),
  answer: (cardId, learned) => api.post(`/api/v1/study/${cardId}`, { learned }),
};

export const LibraryApi = {
  listDecks: (filters = {}) => api.get("/api/v1/library/decks", { params: filters }),
  listDeckCards: (deckId, limit = 50, offset = 0, params = {}) =>
    api.get(`/api/v1/library/decks/${deckId}/cards`, { params: { limit, offset, ...params } }),
  importCard: (cardId) => api.post(`/api/v1/library/cards/${cardId}/import`, {}),
  importSelected: (deckId, card_ids) =>
    api.post(`/api/v1/library/decks/${deckId}/import-selected`, { card_ids }),
};

export const ReadingSourcesApi = {
  list: (params = {}) => api.get("/api/v1/reading-sources", { params }),
  create: (payload) => api.post("/api/v1/reading-sources", payload),
  get: (sourceId) => api.get(`/api/v1/reading-sources/${sourceId}`),
  getDetail: (sourceId, limit = 50, offset = 0) =>
    api.get(`/api/v1/reading-sources/${sourceId}/detail`, { params: { limit, offset } }),
  listCards: (sourceId, limit = 50, offset = 0) =>
    api.get(`/api/v1/reading-sources/${sourceId}/cards`, { params: { limit, offset } }),
};
