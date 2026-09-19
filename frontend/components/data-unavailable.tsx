import { DatabaseZap } from "lucide-react";

export function DataUnavailable({ title, description }: { title: string; description: string }) {
  return <section className="card empty-state"><div><DatabaseZap size={30} aria-hidden="true" /><h2>{title}</h2><p>{description}</p></div></section>;
}
