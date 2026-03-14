function normalizeStatus(value) {
  return String(value || "").trim().toLowerCase();
}

function toStageNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

function memoryStrengthFromStage(stage) {
  const n = toStageNumber(stage);
  if (n == null) return "Weak";
  if (n >= 4) return "Strong";
  if (n >= 2) return "Medium";
  return "Weak";
}

export function memoryStrengthFromStatus(status, stage = null) {
  const key = normalizeStatus(status);

  if (key === "mastered" || key === "strong") return "Strong";
  if (key === "learning" || key === "medium") {
    const byStage = memoryStrengthFromStage(stage);
    return byStage === "Weak" ? "Medium" : byStage;
  }
  if (key === "new" || key === "weak" || key === "difficult" || key === "hard") return "Weak";
  return memoryStrengthFromStage(stage);
}

export function memoryStrengthFromCard(card) {
  const status = card?.status || card?.progress_status || card?.study_status;
  const stage = card?.stage ?? card?.progress?.stage ?? card?.user_progress?.stage;
  return memoryStrengthFromStatus(status, stage);
}
