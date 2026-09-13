# Vercel Access Evidence

Last checked: 2026-09-07T07:26:46+03:00

This artifact records names and IDs only. It must never contain Vercel tokens,
environment values, cookies, bearer tokens, or provider secrets.

## Expected production project

| Field | Value |
| --- | --- |
| Production URL | `https://commerce-revenue-autopilot.vercel.app` |
| Vercel team slug | `malek-virtz` |
| Vercel team ID | `team_bGNbBWwra6PVZuM1WULcCW5r` |
| Vercel project name | `commerce-revenue-autopilot` |
| Vercel project ID | `prj_qd8XsbNvKkxWQvDqo5peOEUfgA2j` |
| Latest known deployment ID | `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx` |

## Connector result

| Check | Result |
| --- | --- |
| `_list_teams` | Passed; team visible as `malek-virtz` / `team_bGNbBWwra6PVZuM1WULcCW5r` |
| `_list_projects` for `team_bGNbBWwra6PVZuM1WULcCW5r` | Authenticated; only `medical-agentic-rag` was listed, not the production project |
| `_get_project` for `prj_qd8XsbNvKkxWQvDqo5peOEUfgA2j` | Project lookup returned `404 Not Found` |
| `_list_deployments` for the expected team/project | Authenticated request returned `403 Forbidden`: no permission to list deployments |
| `_get_deployment` for `dpl_3QYGLjukFXvhqN2rXaar2BRKkJpx` and `commerce-revenue-autopilot.vercel.app` | Deployment lookup returned `404 Not Found` |
| Public HTTP smoke | Public URL is reachable but fails the current deployment smoke contract: reserved API fallback and hidden OpenAPI behavior do not match this candidate |

## Current classification

The Vercel connector is authenticated enough to see the team, but not enough to inspect, deploy,
promote, roll back, or verify the expected production project. Public reachability is not deployment
control or current-release provenance. Deployment control remains `blocked_missing_access`.

The 2026-09-07 local recheck also found no configured Git remote, immutable `RELEASE_SHA`, Vercel
CLI executable, or non-empty `VERCEL_TOKEN` in the current process. Only key presence was checked;
no environment values were printed.

Do not create a replacement Vercel project. Preview deployment cannot be created until the
connector or CLI token can access the existing `commerce-revenue-autopilot` project.

Required deployment-control key names remain:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

These are names only, not values.

## Exact owner action

Grant the connected Vercel account access to the existing `malek-virtz` team project
`commerce-revenue-autopilot`, or provide scoped CI/CLI credentials for that same project. After
access is restored, run `_get_project`, `_get_deployment`, create a Preview deployment, run
`scripts/verify_deployment_smoke.py <preview-url>`, and promote only after the release gates pass.
