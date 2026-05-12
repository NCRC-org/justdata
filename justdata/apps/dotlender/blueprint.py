"""DotLender blueprint — HMDA dot-density lending map with PDF canvas export."""
from flask import Blueprint, render_template

from justdata.main.auth import staff_required


dotlender_bp = Blueprint(
    "dotlender",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dotlender/static",
)


@dotlender_bp.route("/")
@staff_required
def index():
    """Filter page — DotLender main view."""
    return render_template(
        "dotlender_main.html",
        app_name="DotLender",
        app_description="HMDA dot-density lending map by race/ethnicity and tract demographics.",
    )


@dotlender_bp.route("/health")
def health():
    """Smoke test target — no auth required."""
    return {"status": "ok", "app": "dotlender"}
