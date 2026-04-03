export default function ProgressBar({
  value = 0,
  max = 100,
  label,
  className = "",
  trackClassName = "bg-stone-200",
  fillClassName = "bg-black",
}) {
  const safeMax = Number.isFinite(Number(max)) ? Number(max) : 0;
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0;

  const percent =
    safeMax > 0 ? Math.min(100, Math.max(0, (safeValue / safeMax) * 100)) : 0;

  return (
    <div className={["w-full", className].join(" ").trim()}>
      {label ? <div className="mb-1 text-xs text-gray-600">{label}</div> : null}
      <div
        className={[
          "h-2 w-full overflow-hidden rounded-full",
          trackClassName,
        ].join(" ")}
        role="progressbar"
        aria-label={label || "Progress"}
        aria-valuemin={0}
        aria-valuemax={safeMax}
        aria-valuenow={safeValue}
      >
        <div
          className={["h-2 rounded-full", fillClassName].join(" ").trim()}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

