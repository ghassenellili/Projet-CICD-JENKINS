"""Flask HTTP server for the SRE Error Budget Calculator."""

import os
from flask import Flask, jsonify, render_template_string, request

from app import __version__
from app.calculator import (
    calculate_allowed_downtime,
    calculate_burn_rate,
    calculate_request_budget,
    evaluate_release_gate,
)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SRE Error Budget Calculator</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; background: #f8fafc; color: #0f172a; }
        .card { background: white; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 1.25rem; }
        h1 { margin-top: 0; color: #1e3a8a; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: 600; font-size: 0.85rem; background: #dbeafe; color: #1e40af; }
        code { background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9rem; }
        ul { line-height: 1.7; }
    </style>
</head>
<body>
    <div class="card">
        <h1>SRE Error Budget Calculator <span class="badge">v{{ version }}</span></h1>
        <p>Evaluate Service Level Objectives (SLOs), calculate allowed downtime, and enforce automated release gates (<strong>GO / CAUTION / NO-GO</strong>) before deploying to production.</p>
    </div>
    <div class="card">
        <h2>HTTP API Endpoints</h2>
        <ul>
            <li><code>GET /health</code> &rarr; Liveness check (returns <code>OK</code> with HTTP 200)</li>
            <li><code>GET /slo/downtime?slo=99.9&amp;days=30</code> &rarr; Allowed downtime in minutes and seconds</li>
            <li><code>POST /slo/budget</code> &rarr; Request-based error budget consumption</li>
            <li><code>POST /slo/burn-rate</code> &rarr; Burn rate and SRE alert severity</li>
            <li><code>POST /slo/release-check</code> &rarr; Automated deployment gate (GO / CAUTION / NO-GO)</li>
        </ul>
    </div>
</body>
</html>
"""


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
            return render_template_string(DASHBOARD_HTML, version=__version__), 200
        return jsonify({
            "service": "error-budget-calculator",
            "version": __version__,
            "status": "running",
            "endpoints": [
                "GET /health",
                "GET /slo/downtime?slo=99.9&days=30",
                "POST /slo/budget",
                "POST /slo/burn-rate",
                "POST /slo/release-check",
            ],
        }), 200

    @app.get("/health")
    def health():
        """Health check endpoint required by Jenkins smoke test and Docker HEALTHCHECK."""
        return "OK", 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/slo/downtime")
    def downtime():
        """Calculate allowed downtime for a given SLO and evaluation window."""
        try:
            slo_raw = request.args.get("slo", "99.9")
            days_raw = request.args.get("days", "30")
            slo = float(slo_raw)
            days = int(days_raw)
            result = calculate_allowed_downtime(slo, days)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/slo/budget")
    def budget():
        """Calculate remaining request error budget from JSON payload."""
        data = request.get_json(silent=True) or {}
        try:
            slo = data.get("slo_target")
            total = data.get("total_requests")
            failed = data.get("failed_requests")
            result = calculate_request_budget(slo, total, failed)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/slo/burn-rate")
    def burn_rate():
        """Calculate error budget burn rate from JSON payload."""
        data = request.get_json(silent=True) or {}
        try:
            slo = data.get("slo_target")
            observed = data.get("observed_error_rate_percent")
            result = calculate_burn_rate(slo, observed)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/slo/release-check")
    def release_check():
        """Evaluate whether a production release is permitted (GO / CAUTION / NO-GO)."""
        data = request.get_json(silent=True) or {}
        try:
            slo = data.get("slo_target")
            total = data.get("total_requests")
            failed = data.get("failed_requests")
            incident = data.get("active_critical_incident", False)
            result = evaluate_release_gate(slo, total, failed, incident)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
