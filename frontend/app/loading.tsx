export default function Loading() {
  return <div className="loading-state" role="status" aria-live="polite">
    <span className="loading-pulse" />
    <div><strong>Loading workspace</strong><p>Retrieving tenant-scoped decision data…</p></div>
  </div>;
}
