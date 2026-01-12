"""
MemberView Blueprint for main JustData app.
Member management and analytics - in development.
"""

from flask import Blueprint, render_template, jsonify
from jinja2 import ChoiceLoader, FileSystemLoader
import logging
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Configure logging
logger = logging.getLogger(__name__)

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
memberview_bp = Blueprint(
    'memberview',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/memberview/static'
)


@memberview_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search both blueprint templates and shared templates."""
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    shared_loader = FileSystemLoader(str(SHARED_TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        blueprint_loader,
        shared_loader
    ])


@memberview_bp.route('/')
@require_access('memberview', 'full')
def index():
    """Main MemberView page."""
    return jsonify({
        'status': 'in_development',
        'message': 'MemberView is currently in development.',
        'version': __version__
    })


@memberview_bp.route('/api/status')
@require_access('memberview', 'full')
def api_status():
    """Get MemberView status."""
    return jsonify({
        'success': True,
        'status': 'in_development',
        'version': __version__
    })
