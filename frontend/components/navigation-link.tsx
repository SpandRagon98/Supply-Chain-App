"use client";

import { Activity, Boxes, CheckCheck, Factory, FileClock, GitFork, LayoutDashboard, PlayCircle, Settings, ShipWheel, Sparkles, TriangleAlert, Waypoints } from "lucide-react";
import { usePathname } from "next/navigation";

const icons = { dashboard: LayoutDashboard, alert: TriangleAlert, network: Waypoints, supplier: Factory, inventory: Boxes, shipment: ShipWheel, scenario: GitFork, recommendation: Sparkles, approval: CheckCheck, execution: Activity, workflow: Waypoints, simulation: PlayCircle, settings: Settings, audit: FileClock };

export function NavigationLink({ href, label, icon }: { href: string; label: string; icon: keyof typeof icons }) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === href : pathname.startsWith(href);
  const Icon = icons[icon];
  return <a className={`nav-link${active ? " active" : ""}`} href={href}><Icon size={17} /><span>{label}</span></a>;
}
