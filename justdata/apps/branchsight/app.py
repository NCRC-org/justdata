"""Standalone entry point for local development only.

Production uses justdata/main/app.py which mounts branchsight_bp at /branchsight.
This file allows running branchsight in isolation during development.
"""
from flask import Flask
from justdata.apps.branchsight.blueprint import branchsight_bp

app = Flask(__name__)
app.register_blueprint(branchsight_bp, url_prefix="")

if __name__ == "__main__":
    app.run(debug=True, port=8003)
