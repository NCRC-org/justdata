"""Standalone entry point for local development only.

Production uses justdata/main/app.py which mounts lenderprofile_bp at /lenderprofile.
This file allows running lenderprofile in isolation during development.
"""
from flask import Flask
from justdata.apps.lenderprofile.blueprint import lenderprofile_bp

app = Flask(__name__)
app.register_blueprint(lenderprofile_bp, url_prefix="")

# Gunicorn / run.py
application = app

if __name__ == "__main__":
    app.run(debug=True, port=8006)
