"use client";

import { Boxes, Factory, Gauge, LayoutDashboard, ShipWheel, TriangleAlert, Waypoints } from "lucide-react";
import { usePathname } from "next/navigation";

const icons = { dashboard: LayoutDashboard, alert: TriangleAlert, network: Waypoints, supplier: Factory, inventory: Boxes, shipment: ShipWheel, risk: Gauge };

export function NavigationLink({ href, label, icon }: { href: string; label: string; icon: keyof typeof icons }) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === href : pathname.startsWith(href);
  const Icon = icons[icon];
  return <a className={`nav-link${active ? " active" : ""}`} href={href}><Icon size={17} /><span>{label}</span></a>;
}
