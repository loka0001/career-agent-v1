# ADR-001: Modular Monolith

**Status:** Accepted

Use one React/FastAPI deployable with explicit API, application, domain, repository, and integration modules. Two known workflows do not justify service discovery, network failure modes, or distributed transactions. Module interfaces preserve a future extraction path if measured scale requires it.
