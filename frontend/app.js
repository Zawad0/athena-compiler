// =============================================================
//  Athena Compiler — React frontend (no-build, in-browser Babel)
//
//  HOW REACT WORKS HERE (quick primer):
//  - React is a library for building UIs from "components".
//  - A component is just a function that returns JSX (HTML-like
//    syntax that Babel turns into plain JS calls).
//  - `useState` stores a value that, when updated, re-renders
//    only the parts of the page that depend on it.
//  - `fetch` sends an HTTP request; `await` pauses until the
//    server replies, just like blocking I/O but non-blocking.
// =============================================================

const { useState } = React;

// ----- Default starter code per language -----
const STARTERS = {
  c: `#include <stdio.h>\n\nint main() {\n    printf("Hello from C!\\n");\n    return 0;\n}\n`,
  cpp: `#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello from C++!" << endl;\n    return 0;\n}\n`,
  java: `public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello from Java!");\n    }\n}\n`,
};

// ----- Maps API status → badge CSS class + human label -----
const STATUS_META = {
  success:        { cls: "badge-success", label: "✓ Success" },
  compile_error:  { cls: "badge-error",   label: "✗ Compile Error" },
  runtime_error:  { cls: "badge-error",   label: "✗ Runtime Error" },
  timeout:        { cls: "badge-warning", label: "⏱ Timeout" },
  output_limit:   { cls: "badge-warning", label: "⚠ Output Limit" },
  internal_error: { cls: "badge-info",    label: "⚙ Internal Error" },
  bad_request:    { cls: "badge-error",   label: "✗ Bad Request" },
};

// =============================================================
//  Component: Header
//  Just branding — no state, no props needed.
// =============================================================
function Header() {
  return (
    <header>
      <div className="logo" aria-hidden="true">Λ</div>
      <h1>Athena <span>Compiler</span></h1>
      <span className="header-sub">C · C++ · Java</span>
    </header>
  );
}

// =============================================================
//  Component: LanguageTabs
//  Shows three tab buttons; calls onSelect(lang) when clicked.
//  `selected` is the currently active language string.
// =============================================================
function LanguageTabs({ selected, onSelect, disabled }) {
  const langs = [
    { id: "c",    label: "C" },
    { id: "cpp",  label: "C++" },
    { id: "java", label: "Java" },
  ];
  return (
    <div className="lang-tabs" role="tablist" aria-label="Language">
      {langs.map(({ id, label }) => (
        <button
          key={id}
          role="tab"
          aria-selected={selected === id}
          className={"lang-tab" + (selected === id ? " active" : "")}
          onClick={() => onSelect(id)}
          disabled={disabled}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// =============================================================
//  Component: RunButton
//  Shows a spinner while loading, a play icon otherwise.
// =============================================================
function RunButton({ loading, onClick }) {
  return (
    <button className="run-btn" onClick={onClick} disabled={loading}>
      {loading
        ? <span className="spinner" aria-label="Running…" />
        : <span className="run-icon" aria-hidden="true" />}
      {loading ? "Running…" : "Run"}
    </button>
  );
}

// =============================================================
//  Component: OutputPanel
//  Renders the structured API response in labelled sections.
//  `result` is null (nothing run yet), "loading", or the JSON
//  object from /api/run.
// =============================================================
function OutputPanel({ result }) {
  // Nothing run yet
  if (result === null) {
    return (
      <div className="output-panel">
        <div className="output-header">Output</div>
        <div className="output-body">
          <div className="idle-msg">Hit Run to execute your code</div>
        </div>
      </div>
    );
  }

  // Still waiting for the server
  if (result === "loading") {
    return (
      <div className="output-panel">
        <div className="output-header">Output</div>
        <div className="output-body">
          <div className="idle-msg">Running…</div>
        </div>
      </div>
    );
  }

  // We have a result object from the API
  const meta = STATUS_META[result.status] || { cls: "badge-neutral", label: result.status };

  // Build a list of sections to render, only for non-empty fields
  const sections = [];

  if (result.message) {
    sections.push({ key: "msg", labelCls: "msg-label", label: "Message", preCls: "", text: result.message });
  }
  if (result.compile_output) {
    sections.push({ key: "compile", labelCls: "compile-label", label: "Compiler output", preCls: "compile-out", text: result.compile_output });
  }
  if (result.stdout) {
    sections.push({ key: "stdout", labelCls: "stdout-label", label: "Standard output", preCls: "", text: result.stdout });
  }
  if (result.stderr) {
    sections.push({ key: "stderr", labelCls: "stderr-label", label: "Standard error", preCls: "stderr-out", text: result.stderr });
  }

  return (
    <div className="output-panel">
      <div className="output-header">
        Output
        <span className={"status-badge " + meta.cls}>{meta.label}</span>
        {/* Show exit code when available */}
        {result.exit_code !== undefined && result.exit_code !== null && (
          <span style={{ fontSize: "0.78rem", color: "var(--overlay)", fontWeight: 400 }}>
            exit&nbsp;{result.exit_code}
          </span>
        )}
        {/* Show run duration on the right */}
        {result.duration_ms !== undefined && (
          <span className="duration">{result.duration_ms} ms</span>
        )}
      </div>

      <div className="output-body">
        {sections.length === 0 ? (
          // Success with no output at all
          <div className="idle-msg" style={{ color: "var(--green)" }}>
            Program exited with no output.
          </div>
        ) : (
          sections.map(s => (
            <div className="output-section" key={s.key}>
              <div className={"section-label " + s.labelCls}>{s.label}</div>
              {/* textContent equivalent: React escapes by default, no XSS risk */}
              <pre className={"output-pre " + s.preCls}>{s.text}</pre>
              {s.key === "stdout" && result.truncated && (
                <div className="truncated-warn">⚠ Output was truncated (hit the server cap).</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// =============================================================
//  Component: App  (root component, owns all state)
//
//  State:
//    lang    — which language tab is active ("c" | "cpp" | "java")
//    source  — what's in the textarea right now
//    result  — null | "loading" | API response object
// =============================================================
function App() {
  const [lang,   setLang]   = useState("c");
  const [source, setSource] = useState(STARTERS["c"]);
  const [result, setResult] = useState(null);

  // When the user clicks a language tab:
  // switch the tab AND load that language's starter code.
  function handleLangChange(newLang) {
    setLang(newLang);
    setSource(STARTERS[newLang]);
    setResult(null); // clear old output
  }

  // Send source to the backend and display the result.
  async function handleRun() {
    setResult("loading");
    try {
      // fetch() is the browser's built-in HTTP client.
      // We POST to a relative URL (/api/run) so it always
      // hits the same server that served this page — no
      // hardcoded host or port needed.
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: lang, source }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      // Network error (server not running, etc.)
      setResult({
        status: "internal_error",
        message: "Could not reach the server. Is the backend running?",
      });
    }
  }

  const isLoading = result === "loading";

  return (
    <>
      <Header />

      <main>
        {/* Toolbar: language selector + run + clear */}
        <div className="toolbar">
          <LanguageTabs selected={lang} onSelect={handleLangChange} disabled={isLoading} />
          <RunButton loading={isLoading} onClick={handleRun} />
          <span className="spacer" />
          <button
            className="clear-btn"
            onClick={() => { setSource(""); setResult(null); }}
            disabled={isLoading}
            title="Clear editor"
          >
            Clear
          </button>
        </div>

        {/* Java reminder: class must be named Main */}
        {lang === "java" && (
          <div className="java-hint">
            ⚠ Java: your public class must be named <strong>Main</strong> (the backend saves it as <code>Main.java</code>).
          </div>
        )}

        {/* Code editor */}
        <div className="editor-wrap">
          <textarea
            className="code-editor"
            value={source}
            onChange={e => setSource(e.target.value)}
            spellCheck={false}
            autoCapitalize="none"
            autoCorrect="off"
            aria-label="Source code editor"
            // Let Tab insert 4 spaces instead of jumping to the next widget
            onKeyDown={e => {
              if (e.key === "Tab") {
                e.preventDefault();
                const { selectionStart: s, selectionEnd: end, value: v } = e.target;
                const next = v.slice(0, s) + "    " + v.slice(end);
                setSource(next);
                // Restore cursor position after React re-renders
                requestAnimationFrame(() => {
                  e.target.selectionStart = e.target.selectionEnd = s + 4;
                });
              }
            }}
          />
        </div>

        {/* Output panel */}
        <OutputPanel result={result} />
      </main>

      <footer>
        Athena Compiler — Compiler Construction Project · runs on localhost
      </footer>
    </>
  );
}

// Mount the React app into the <div id="root"> in index.html.
// ReactDOM.createRoot is the React 18 way to start the app.
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
