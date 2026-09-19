import type { ReactNode } from "react";
import { Bell, Search, Sparkles } from "lucide-react";
import Link from "next/link";

import { NavigationLink } from "./navigation-link";

const navigation = [
  { href: "/", label: "Command center", icon: "dashboard" },
  { href: "/disruptions", label: "Disruptions", icon: "alert" },
  { href: "/supply-network", label: "Supply network", icon: "network" },
  { href: "/suppliers", label: "Suppliers", icon: "supplier" },
  { href: "/inventory", label: "Inventory", icon: "inventory" },
  { href: "/shipments", label: "Shipments", icon: "shipment" },
] as const;

const decisionNavigation = [
  { href: "/decisions/scenarios", label: "Scenarios", icon: "scenario" },
  { href: "/decisions/recommendations", label: "Recommendations", icon: "recommendation" },
  { href: "/approvals", label: "Approvals", icon: "approval" },
  { href: "/executions", label: "Executions", icon: "execution" },
] as const;

const controlNavigation = [
  { href: "/workflows", label: "Workflows", icon: "workflow" },
  { href: "/simulations", label: "Simulations", icon: "simulation" },
  { href: "/settings/integrations", label: "Settings", icon: "settings" },
  { href: "/audit", label: "Audit", icon: "audit" },
] as const;

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/">
          <span className="brand-mark"><Sparkles size={17} /></span>
          <span>Autopilot</span>
        </Link>
        <nav aria-label="Primary navigation">
          <p className="nav-label">Operations</p>
          {navigation.map((item) => <NavigationLink key={item.href} {...item} />)}
          <p className="nav-label">Decisioning</p>
          {decisionNavigation.map((item) => <NavigationLink key={item.href} {...item} />)}
          <p className="nav-label">Control plane</p>
          {controlNavigation.map((item) => <NavigationLink key={item.href} {...item} />)}
        </nav>
        <div className="sidebar-foot">Nova Electronics<br />Decision workspace</div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="search"><Search size={16} /> Search disruptions, suppliers, orders…</div>
          <div className="top-actions"><Bell size={18} aria-label="Notifications" /><span>Operations team</span><div className="avatar">NE</div></div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
