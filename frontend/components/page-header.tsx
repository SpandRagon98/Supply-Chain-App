export function PageHeader({ eyebrow = "Supply chain control", title, description }: { eyebrow?: string; title: string; description: string }) {
  return <header><p className="eyebrow">{eyebrow}</p><h1 className="page-title">{title}</h1><p className="page-subtitle">{description}</p></header>;
}
