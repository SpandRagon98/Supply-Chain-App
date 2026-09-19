import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { RecordList } from "../../components/record-list";
import { getCollection, type Inventory } from "../../lib/api";

export default async function InventoryPage() {
  const inventory = await getCollection<Inventory>("/inventory");
  return <><PageHeader eyebrow="Inventory posture" title="Inventory coverage" description="Review on-hand, allocated, safety stock, consumption, days of supply, and deterministic projected stockout dates." />{inventory?.length ? <RecordList columns={[{ key: "facility_id", label: "Facility" }, { key: "material_id", label: "Material" }, { key: "on_hand_quantity", label: "On hand" }, { key: "allocated_quantity", label: "Allocated" }, { key: "unit_of_measure", label: "Unit" }]} rows={inventory} /> : <DataUnavailable title="Coverage requires the inventory API" description="Each value will retain a drill-down to its snapshot, consumption history, facility, material, and incident lineage. Nothing is calculated in the presentation layer." />}</>;
}
