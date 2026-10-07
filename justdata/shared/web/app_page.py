"""Template context for app_page.html, the analysis-app standard (spec 04 A1).

An app's entry route renders its template (which extends app_page.html) with
**app_page_context(...). The app name, purpose and source chips come from the
nav registry, so the header band always matches the drawer, the /apps
launcher and the landing roster.
"""

from typing import Iterable, Optional, Sequence

from justdata.shared.web.registry import NAV_GROUPS

# Exports app_results_toolbar.html knows how to render. An app lists only the
# ones it actually implements; the toolbar renders nothing else.
KNOWN_EXPORTS = ("csv", "pdf")


def find_app(key: str):
    """Return (group_label, AppEntry) for a registry key."""
    for group in NAV_GROUPS:
        for item in group.items:
            if item.key == key:
                return group.label, item
    raise KeyError(f"{key!r} is not in the nav registry")


def app_page_context(app_key: str, *, form_id: str,
                     sources: Sequence[dict] = (),
                     data_vintage: Optional[str] = None,
                     help_url: Optional[str] = None,
                     exports: Iterable[str] = (),
                     caveats: Sequence[str] = (),
                     shows_juxtaposition: bool = True,
                     exclusion_note: Optional[str] = None,
                     idle_message: Optional[str] = None) -> dict:
    """Context for app_page.html and its partials.

    sources: [{"name", "vintage", "url" (optional)}], the datasets this
        result actually draws on, shown in app_sources.html.
    data_vintage: a string such as "HMDA 2018 to 2024", or None to hide it.
        Read it from the data, never hardcode a guessed year.
    help_url: leave None until a guide or in-report methodology anchor exists.
    shows_juxtaposition: True for any result that puts lending or branch data
        next to race, ethnicity or income (platform rule, spec 04 A4).
    exclusion_note: a sentence on records the analysis drops, only when the
        code that drops them can be named (spec 04 decision 2, 2026-10-07).
    idle_message: replaces the default idle text; apps with a lender step
        pass one (spec 04 decision 4).
    """
    exports = tuple(exports)
    unknown = set(exports) - set(KNOWN_EXPORTS)
    if unknown:
        raise ValueError(f"unknown export(s): {sorted(unknown)}")
    group_label, app = find_app(app_key)
    return {
        "app": app,
        "app_name": app.name,
        "group_label": group_label,
        "form_id": form_id,
        "sources": list(sources),
        "data_vintage": data_vintage,
        "help_url": help_url,
        "exports": exports,
        "caveats": list(caveats),
        "shows_juxtaposition": shows_juxtaposition,
        "exclusion_note": exclusion_note,
        "idle_message": idle_message,
    }
