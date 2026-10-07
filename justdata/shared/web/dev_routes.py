"""Development-only pages (spec 04 Part A acceptance).

/dev/app-states renders app_page.html with every AppStates state so the
standard can be checked in a browser. register_dev_routes() is called by
create_app() only when debug is on (DEBUG or FLASK_DEBUG), so the route does
not exist on any deployed service.
"""

import os

from flask import Blueprint, render_template

from justdata.shared.web.app_page import app_page_context

dev_bp = Blueprint("dev", __name__)


def debug_enabled(app) -> bool:
    return bool(app.debug) or os.getenv("FLASK_DEBUG", "").lower() in ("1", "true")


@dev_bp.route("/dev/app-states")
def app_states_preview():
    ctx = app_page_context(
        "lendsight",
        form_id="devStatesForm",
        sources=[{"name": "Example dataset", "vintage": "Preview only, no data is queried"}],
        exports=("csv", "pdf"),
        caveats=["Example caveat. Apps pass their own caveats."],
    )
    return render_template("dev_app_states.html", **ctx)


def register_dev_routes(app) -> bool:
    if not debug_enabled(app):
        return False
    app.register_blueprint(dev_bp)
    return True
