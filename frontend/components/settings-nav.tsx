const links = [
  ["/settings/integrations", "Integrations"],
  ["/settings/ai", "AI configuration"],
  ["/settings/risk", "Risk & optimization"],
  ["/audit", "Audit explorer"],
] as const;

export function SettingsNav() {
  return <nav className="tab-nav" aria-label="Settings sections">{links.map(([href, label]) => <a key={href} href={href}>{label}</a>)}</nav>;
}
