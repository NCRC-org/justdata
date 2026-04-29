# MemberView

Member management and analytics surface. **In development** — currently
a stub that exposes a status endpoint; no analysis or reporting
functionality is wired up yet.

## Blueprint

- URL prefix: `/memberview`
- File: `blueprint.py` (`memberview_bp`)
- Routes:
  - `/` — landing/placeholder page (renders if a template is present)
  - `/api/status` — JSON status endpoint

## Data sources

None at this time.

## Reports

None.

## Templates

`templates/` directory exists but is currently empty (no top-level
templates and no `partials/`). The `static/` directory holds future
front-end assets.

## Notes

- The blueprint applies the same `ChoiceLoader` and auth decorators as
  other apps so the eventual UI inherits standard chrome.
- This app is registered last among "in-development" blueprints in
  `justdata/main/app.py`.
