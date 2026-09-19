import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { RecordList } from "../../components/record-list";
import { getCollection, type Shipment } from "../../lib/api";

export default async function ShipmentsPage() {
  const shipments = await getCollection<Shipment>("/shipments");
  return <><PageHeader eyebrow="Logistics execution" title="Shipments" description="Monitor in-transit and delayed shipments, their source events, and downstream facility exposure." />{shipments ? <RecordList columns={[{ key: "shipment_number", label: "Shipment" }, { key: "status", label: "Status" }, { key: "carrier", label: "Carrier" }, { key: "transportation_mode", label: "Mode" }, { key: "estimated_arrival_at", label: "ETA" }]} rows={shipments} /> : <DataUnavailable title="Shipment telemetry will appear here" description="The tenant-scoped shipment API will populate this screen with event timelines and incident links. Delays remain distinguishable from confirmed disruption impacts." />}</>;
}
