# Demo Script Index

Last verified: 2026-09-01

Use [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for the current isolated local demonstration. Its bootstrap
commands are the same commands proven by `.agents/skills/commerce-clean-bootstrap/SKILL.md`.

The required evidence sequence is:

1. generate fresh local secrets and seed the isolated SQLite demo;
2. start the API, Vite frontend, and persistent worker independently;
3. confirm liveness/readiness and browser login;
4. demonstrate customer message → grounded citations → reviewed reply → queued/sent state → audit;
5. demonstrate product → draft → edit/approval → worker publication → audit;
6. distinguish deterministic/demo results from every provider capability that still requires real
   credentials and a deployed acceptance test.

Never use a reusable password from source or documentation, and never describe a demo adapter as a
live provider result.
