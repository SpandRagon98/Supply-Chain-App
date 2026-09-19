import { PageHeader } from "../../components/page-header";

const nodes = [
  ["Supplier", "Supplier sites and capacity context"],
  ["Material", "Approved source and dependency coverage"],
  ["Product", "Multi-level BOM propagation"],
  ["Facility", "Inventory and consumption coverage"],
  ["Customer order", "Lineaged commercial exposure"],
  ["Decision", "Scenario, approval, execution, verification"],
];

export default function SupplyNetworkPage() {
  return <>
    <PageHeader eyebrow="Operational topology" title="Supply network" description="Explore the dependency path from a disrupted supplier through materials, BOMs, facilities, orders, and mitigations." />
    <section className="card network-map" aria-label="Supply network relationship model">{nodes.map(([label, detail]) => <article className="network-node" key={label}><strong>{label}</strong><span>{detail}</span></article>)}</section>
    <p className="page-subtitle">The graph is intentionally a structural view until the tenant-aware network API is exposed. It will render computed NetworkX traversal results rather than infer relationships in the browser.</p>
  </>;
}
