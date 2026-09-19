# Execution and verification

Phase 12 uses adapter interfaces and a deterministic mock ERP adapter. Execution actions are keyed by tenant-scoped idempotency keys, so repeated requests return the original action rather than producing duplicate external effects. Verification compares predicted and actual structured outcomes, persists variance, and advances the incident to resolved, monitoring, or renewed mitigation.
