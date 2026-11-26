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

const { useState, useRef, useEffect } = React;

// ----- Default starter code per language -----
const STARTERS = {
  c: `#include <stdio.h>\n\nint main() {\n    printf("Hello from C!\\n");\n    return 0;\n}\n`,
  cpp: `#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello from C++!" << endl;\n    return 0;\n}\n`,
  java: `public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello from Java!");\n    }\n}\n`,
};

// ----- Maps CodeMirror mode strings per language -----
// The "clike" script (loaded in index.html) handles all three.
// These MIME types tell CodeMirror which dialect to highlight.
const CM_MODE = {
  c:    "text/x-csrc",
  cpp:  "text/x-c++src",
  java: "text/x-java",
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
      <img className="logo" src="favicon.png" alt="Athena Compiler logo" />
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
  const [result, setResult] = useState(null);
  const [input, setInput] = useState("");

  // textareaRef points to the real <textarea> DOM node.
  // CodeMirror.fromTextArea() reads it on init and then hides it.
  const textareaRef = useRef(null);

  // cmRef holds the live CodeMirror instance so we can call its
  // API (getValue, setValue, setOption) from event handlers.
  // We use a ref (not state) because changing the CM instance
  // should NOT trigger a React re-render.
  const cmRef = useRef(null);

  // --- Initialize CodeMirror once, after the first render ---
  // useEffect with [] runs exactly once: after the component
  // mounts and the <textarea> is in the DOM.
  useEffect(() => {
    cmRef.current = CodeMirror.fromTextArea(textareaRef.current, {
      mode:          CM_MODE["c"],   // start in C mode
      theme:         "dracula",      // dark theme loaded via CDN
      lineNumbers:   true,           // show line numbers in the gutter
      tabSize:       4,
      indentWithTabs: false,         // Tab key inserts spaces, not \t
      lineWrapping:  true,           // soft-wrap long lines
      autofocus:     true,
    });

    // Seed the editor with the C starter code.
    cmRef.current.setValue(STARTERS["c"]);
  }, []);  // [] = "run once on mount, never again"

  // When the user picks a different language tab:
  //  1. Update React's lang state (re-renders the tab UI)
  //  2. Tell CodeMirror to switch its highlighting mode
  //  3. Load that language's starter code into the editor
  //  4. Clear the old output panel
  function handleLangChange(newLang) {
    setLang(newLang);
    if (cmRef.current) {
      cmRef.current.setOption("mode", CM_MODE[newLang]);
      cmRef.current.setValue(STARTERS[newLang]);
    }
    setResult(null);
  }

  async function handleRun() {
    // Read the current editor text from CodeMirror, not from React state.
    const source = cmRef.current ? cmRef.current.getValue() : "";

    setResult("loading");
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: lang,
          source,
          input
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
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
        <div className="toolbar">
          <LanguageTabs selected={lang} onSelect={handleLangChange} disabled={isLoading} />
          <RunButton loading={isLoading} onClick={handleRun} />
          <span className="spacer" />
          <button
            className="clear-btn"
            onClick={() => {
              if (cmRef.current) cmRef.current.setValue("");
              setResult(null);
            }}
            disabled={isLoading}
            title="Clear editor"
          >
            Clear
          </button>
        </div>

        {lang === "java" && (
          <div className="java-hint">
            ⚠ Java: your public class must be named <strong>Main</strong> (the backend saves it as <code>Main.java</code>).
          </div>
        )}

        {/* CodeMirror wraps this textarea and replaces it with its
            own editor div. The ref lets us pass the DOM node to
            CodeMirror.fromTextArea() in useEffect above. */}
        <div className="editor-wrap">
          <textarea ref={textareaRef} />
        </div>

        <div className="output-panel input-panel">
          <div className="output-header">INPUT</div>
          <div className="output-body input-body">
            <textarea
              className="custom-input"
              placeholder="Enter your input here..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
            />
          </div>
        </div>

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
