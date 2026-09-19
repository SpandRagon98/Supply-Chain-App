"use client";

export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <section className="card empty-state" role="alert"><div><h2>This workspace could not be loaded</h2><p>The failure was contained to this screen. Retry after checking the API connection.</p><button className="button" onClick={reset}>Try again</button></div></section>;
}
