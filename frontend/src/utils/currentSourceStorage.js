const STORAGE_KEY = "deeplex.current_source_by_pair";

function readMap() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed;
  } catch {
    return {};
  }
}

function writeMap(value) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Ignore storage failures; this is UX convenience only.
  }
}

export function getCurrentSourceForPair(pairId) {
  if (!pairId) return null;
  const map = readMap();
  const value = map[String(pairId)];
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

export function setCurrentSourceForPair(pairId, sourceId) {
  if (!pairId || !sourceId) return;
  const map = readMap();
  map[String(pairId)] = Number(sourceId);
  writeMap(map);
}

export function clearCurrentSourceForPair(pairId) {
  if (!pairId) return;
  const map = readMap();
  delete map[String(pairId)];
  writeMap(map);
}
