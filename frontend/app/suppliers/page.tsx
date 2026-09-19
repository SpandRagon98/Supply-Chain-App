import { DataUnavailable } from "../../components/data-unavailable";
import { PageHeader } from "../../components/page-header";
import { RecordList } from "../../components/record-list";
import { getCollection, type Supplier } from "../../lib/api";

export default async function SuppliersPage() {
  const suppliers = await getCollection<Supplier>("/suppliers");
  return <><PageHeader eyebrow="Master data" title="Suppliers" description="Evaluate supplier sites, approved material relationships, resilience signals, and criticality." />{suppliers?.length ? <RecordList columns={[{ key: "code", label: "Code" }, { key: "name", label: "Supplier" }, { key: "country_code", label: "Country" }, { key: "criticality", label: "Criticality" }, { key: "status", label: "Status" }]} rows={suppliers} /> : <DataUnavailable title="Supplier records will appear here" description="The table is connected to the tenant-scoped suppliers API and will recover when its backend data source is reachable." />}</>;
}
