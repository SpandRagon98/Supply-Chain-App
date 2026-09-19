"use client";

import { useEffect } from "react";

export default function ErrorBoundary({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error("Workspace route failed", error.digest); }, [error]);
  return <section className="card empty-state" role="alert"><div><h2>This workspace could not be loaded</h2><p>The failure was contained to this screen. Retry after checking the API connection.</p><button className="button" onClick={reset}>Try again</button></div></section>;
}
