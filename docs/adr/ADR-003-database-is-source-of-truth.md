# ADR-003: Database Is the Source of Truth

**Status:** Accepted

SQL owns product price, stock, status, content version, approval, and publication attempts. Chroma stores searchable text and stable identifiers only. Every retrieved product is reloaded from SQL before filtering, ranking, or response generation, preventing stale vector metadata from becoming a sales claim.
