# ADR-004: Public Image Storage for Meta

**Status:** Accepted

Local storage supports preview and automated tests. Real Meta publishing requires a public HTTPS URL, so production uses the Cloudinary adapter. The Meta adapters reject non-HTTPS image URLs instead of sending an inaccessible filesystem path or claiming success.
