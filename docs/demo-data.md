# Nova Electronics demo data

Phase 3 provides a deterministic, connected dataset for the fictional tenant **Nova Electronics**. It is large enough to exercise procurement, inventory, demand, logistics, multi-level BOM traversal, and later disruption workflows while remaining understandable during a product demonstration.

## Seed command

With Docker running, execute this repeatable command from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/seed-demo.ps1
```

The script migrates the database before running `python -m app.seed`. Stable UUIDv5 identities and SQLAlchemy merge semantics make the command idempotent: running it again updates the Nova records without duplicating them. The entire seed runs in one transaction.

For an already configured local Python environment, the equivalent command is:

```powershell
cd backend
alembic upgrade head
python -m app.seed
```

## Dataset profile

| Area | Seeded records |
| --- | ---: |
| Organization | 1 |
| Users, roles, and assignments | 21 |
| Suppliers, sites, and scorecards | 73 |
| Materials and approved supplier sources | 98 |
| Products, BOMs, and BOM components | 85 |
| Plants, warehouses, and distribution centers | 8 |
| Inventory and consumption history | 296 |
| Purchase orders and lines | 86 |
| Customers, orders, and lines | 144 |
| Shipments and tracking events | 80 |
| Mock connector configurations | 5 |
| Signal source configurations | 5 |
| **Total** | **902** |

The network includes 18 suppliers across India and Asia, 40 materials, 10 products, 10 versioned BOMs, 8 facilities, 18 customers, 30 purchase orders, 42 customer orders, and 20 shipments.

## Scenario-ready structure

The dataset intentionally contains evidence and pressure points for later phases without precomputing their conclusions:

- **Taiwan typhoon:** Formosa Silicon Works has Tainan and Hsinchu sites and is the primary source for the critical `CPU-X9`. Hanseong is an approved alternate with a different lead time and cost.
- **Port closure:** international shipments travel by ocean and include Singapore tracking events, allowing a closure to affect selected inbound flows.
- **Supplier shutdown:** the critical `CELL-LI6` battery cell is single-sourced from Kyoto Battery Systems, making propagation and mitigation behavior visible.
- **Inventory pressure:** `CPU-X9`, `PWR-IC-42`, and `CELL-LI6` have deliberately shaped stocks across warehouses and plants, backed by three monthly consumption periods.
- **Demand impact:** open and partially fulfilled customer orders connect finished products to customer priority and revenue.
- **Multi-level propagation:** finished products consume intermediate motherboard, battery, and display assemblies; those assemblies consume raw materials.

No random generator or wall-clock value influences the data. Snapshot times, commercial documents, status distributions, and identifiers are stable, so automated demonstrations and tests can assert exact outcomes.
