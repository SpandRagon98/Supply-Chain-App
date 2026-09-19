export type HealthPayload = { status: "healthy" | "unhealthy"; checks: Record<string, { status: string }> };
type Envelope<T> = { data: T; meta: { request_id: string } };
export type Overview = { active_incidents: number; suppliers: number; orders: number; revenue_at_risk: string };
export type Incident = { id: string; incident_number: string; title: string; severity: string; confidence: string; status: string; started_at: string };
export type Supplier = { id: string; code: string; name: string; country_code: string; criticality: number; status: string };
export type Inventory = { id: string; facility_id: string; material_id: string | null; on_hand_quantity: string; allocated_quantity: string; unit_of_measure: string };
export type Shipment = { id: string; shipment_number: string; status: string; carrier: string | null; transportation_mode: string; estimated_arrival_at: string | null };

const apiUrl =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function getHealth(): Promise<HealthPayload | null> {
  return getResource<HealthPayload>("/health/live");
}

export async function getOverview(): Promise<Overview | null> {
  return getResource<Overview>("/dashboard/overview");
}

export async function getCollection<T>(path: string): Promise<T[] | null> {
  return getResource<T[]>(path);
}

export async function getResource<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiUrl}${path}`, { next: { revalidate: 15 } });
    if (!response.ok) return null;
    return (await response.json() as Envelope<T>).data;
  } catch {
    return null;
  }
}
