export function StatusPill({ value }: { value: string }) {
  const tone = ["SUCCEEDED", "APPROVED", "PUBLISHED", "CONNECTED", "MOCK_MODE", "RECOMMENDED"].includes(value)
    ? "healthy"
    : ["FAILED", "REJECTED", "ERROR", "CRITICAL"].includes(value)
      ? "danger"
      : "unavailable";
  return <span className={`status ${tone}`}>{value.replaceAll("_", " ")}</span>;
}
