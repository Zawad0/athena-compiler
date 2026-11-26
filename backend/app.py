from pathlib import Path
from flask import Flask, jsonify, request

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

ALLOWED_LANGUAGES = {"c", "cpp", "java"}
MAX_SOURCE_BYTES = 100_000


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/run")
def run():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status="bad_request", message="Body must be JSON"), 400

    language = data.get("language")
    source = data.get("source")
    if language not in ALLOWED_LANGUAGES:
        return jsonify(status="bad_request", message="Unknown language"), 400
    if not isinstance(source, str) or not source.strip():
        return jsonify(status="bad_request", message="Source is empty"), 400
    if len(source.encode()) > MAX_SOURCE_BYTES:
        return jsonify(status="bad_request", message="Source too large"), 400

    return jsonify(
        status="success",
        compile_output="",
        stdout=f"[FAKE] pretend output for {language}\n",
        stderr="",
        exit_code=0,
        duration_ms=0,
        truncated=False,
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
