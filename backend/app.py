# =============================================================
#  app.py — Flask web server: HTTP layer only
#
#  Responsibilities of THIS file:
#    - Serve the frontend (index.html, style.css, app.js)
#    - Receive POST /api/run, validate input, call runner.py
#    - Return JSON
#
#  What this file does NOT do:
#    - Compile or run any code  (that's runner.py's job)
#    - Know anything about languages  (that's languages.py's job)
#
#  WHY split it this way?
#  runner.py can be run and tested from the terminal without
#  starting the web server.  app.py can be replaced (e.g. with
#  FastAPI) without touching any execution logic.
# =============================================================

from pathlib import Path
from flask import Flask, jsonify, request

import config
from runner import run_code

# Flask serves the frontend/ directory as static files.
# static_url_path="" means  /style.css  maps to  frontend/style.css.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

# The set of language keys we accept.  Any value not in this set
# is rejected with HTTP 400 before we touch the filesystem.
ALLOWED_LANGUAGES = {"c", "cpp", "java"}


@app.get("/")
def index():
    """Serve the main page."""
    return app.send_static_file("index.html")


@app.post("/api/run")
def api_run():
    """
    Accepts: POST /api/run
    Body:    { "language": "c"|"cpp"|"java", "source": "<code>" }
    Returns: JSON result dict (see §8 of project context for the full schema)

    HTTP 400 is returned for bad input (not a program error — those
    get HTTP 200 with status="compile_error" etc.).
    """

    # --- Input validation ---
    # request.get_json(silent=True) returns None if the body isn't
    # valid JSON (instead of raising an exception).
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status="bad_request", message="Body must be JSON"), 400

    language = data.get("language")
    source   = data.get("source")
    stdin_text = data.get("input", "")

    if not isinstance(stdin_text, str):
        return jsonify(
            status="bad_request",
            message="Input must be a string"
        ), 400

    if len(stdin_text.encode("utf-8")) > config.MAX_INPUT_BYTES:
        return jsonify(
            status="bad_request",
            message=f"Input exceeds {config.MAX_INPUT_BYTES} bytes"
        ), 400

    if language not in ALLOWED_LANGUAGES:
        return jsonify(status="bad_request",
                       message=f"Unknown language {language!r}. "
                               f"Allowed: {sorted(ALLOWED_LANGUAGES)}"), 400

    if not isinstance(source, str) or not source.strip():
        return jsonify(status="bad_request", message="Source must be a non-empty string"), 400

    if len(source.encode()) > config.MAX_SOURCE_BYTES:
        return jsonify(status="bad_request",
                       message=f"Source exceeds {config.MAX_SOURCE_BYTES} bytes"), 400

    # --- Delegate to runner (never raises) ---
    result = run_code(language, source, stdin_text)

    # runner.py returns a dict; jsonify turns it into an HTTP response.
    return jsonify(result)


if __name__ == "__main__":
    print(f"Athena Compiler running at http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
