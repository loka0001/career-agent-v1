# ADR-002: No LLM Supervisor

**Status:** Accepted

HTTP routes choose one of two explicit use cases. An LLM extracts structured content but never decides workflow transitions or business rules. This makes state, errors, costs, and tests deterministic and removes an unnecessary orchestration dependency.
