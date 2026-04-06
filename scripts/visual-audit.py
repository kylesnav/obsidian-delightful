#!/usr/bin/env python3
"""
Visual audit automation for the Delightful Obsidian theme.

Captures ~70 screenshots across baseline views, accent colors, style
permutations, and UX details using Chrome DevTools Protocol (CDP).

Prerequisites:
  - Obsidian running with:  --remote-debugging-port=9222 --remote-allow-origins=*
  - Python 3.9+ with websocket-client:  pip install websocket-client
  - Vault notes present:
      Projects/Delightful Obsidian Update/theme-test.md
      Projects/Delightful Obsidian Update/theme-density-test.md
      Working/2026-04-04.md

Usage:
  python3 scripts/visual-audit.py

Output:
  screenshots/audit/{baseline,accents,permutations,ux-detail,reports}/
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CDP_PORT = 9222
CDP_HOST = "localhost"

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent / "screenshots" / "audit"

SUBDIRS = ["baseline", "accents", "permutations", "ux-detail", "reports"]

# Note paths inside the vault
NOTE_THEME_TEST = "Projects/Delightful Obsidian Update/theme-test.md"
NOTE_DENSITY = "Projects/Delightful Obsidian Update/theme-density-test.md"
NOTE_DAILY = "Working/2026-04-04.md"

# Tracking
_shot_count = 0
_failures: list[str] = []

# ---------------------------------------------------------------------------
# Directory setup
# ---------------------------------------------------------------------------

def ensure_dirs() -> None:
    for sub in SUBDIRS:
        (BASE_DIR / sub).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# CDP connection
# ---------------------------------------------------------------------------

_ws = None
_msg_id = 0


def discover_target() -> str:
    """Query the CDP /json endpoint and return the WebSocket URL for Obsidian."""
    url = f"http://{CDP_HOST}:{CDP_PORT}/json"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            targets = json.loads(resp.read())
    except Exception as e:
        print(
            f"ERROR: Cannot reach CDP at {url}\n"
            f"       Is Obsidian running with --remote-debugging-port={CDP_PORT} "
            f"--remote-allow-origins=* ?\n"
            f"       ({e})"
        )
        sys.exit(1)

    # Prefer a page whose URL mentions obsidian
    for t in targets:
        if t.get("type") == "page" and "obsidian" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]

    # Fallback: first page target
    pages = [t for t in targets if t.get("type") == "page"]
    if pages:
        return pages[0]["webSocketDebuggerUrl"]

    print("ERROR: No page targets found at CDP endpoint.")
    sys.exit(1)


def connect() -> None:
    """Establish the single persistent WebSocket connection."""
    global _ws
    import websocket

    ws_url = discover_target()
    print(f"Connecting to {ws_url}")
    _ws = websocket.create_connection(ws_url, suppress_origin=True)
    print("CDP connection established.\n")


def disconnect() -> None:
    global _ws
    if _ws:
        _ws.close()
        _ws = None

# ---------------------------------------------------------------------------
# CDP helpers
# ---------------------------------------------------------------------------

def cdp(method: str, params: dict | None = None) -> dict:
    """Send a CDP command on the persistent connection and return the result."""
    global _msg_id
    _msg_id += 1
    msg: dict = {"id": _msg_id, "method": method}
    if params:
        msg["params"] = params
    _ws.send(json.dumps(msg))
    while True:
        raw = _ws.recv()
        response = json.loads(raw)
        if response.get("id") == _msg_id:
            if "error" in response:
                raise RuntimeError(f"CDP error: {response['error']}")
            return response.get("result", {})
        # else: event or out-of-order message -- keep reading


def evaluate(js: str) -> str | None:
    """Evaluate JavaScript in the page and return the string value (or None)."""
    result = cdp("Runtime.evaluate", {
        "expression": js,
        "awaitPromise": True,
        "returnByValue": True,
    })
    inner = result.get("result", {})
    if inner.get("type") == "undefined":
        return None
    return inner.get("value")

# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def screenshot(name: str, subdir: str) -> None:
    """Capture a PNG screenshot into BASE_DIR/subdir/name.png."""
    global _shot_count
    filepath = BASE_DIR / subdir / f"{name}.png"
    try:
        result = cdp("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(result["data"])
        with open(filepath, "wb") as f:
            f.write(data)
        _shot_count += 1
        size_kb = len(data) / 1024
        print(f"  [{_shot_count:>3}] {subdir}/{name}.png  ({size_kb:.0f} KB)")
    except Exception as e:
        _failures.append(f"{subdir}/{name}: {e}")
        print(f"  [ERR] {subdir}/{name}.png  FAILED: {e}")

# ---------------------------------------------------------------------------
# Theme / view helpers
# ---------------------------------------------------------------------------

def set_theme(mode: str) -> None:
    """Switch between 'obsidian' (dark) and 'moonstone' (light)."""
    evaluate(f"app.changeTheme('{mode}')")
    time.sleep(0.5)


def open_note(path: str) -> None:
    """Open a note by vault-relative path."""
    # Escape single quotes in path
    safe = path.replace("'", "\\'")
    evaluate(f"app.workspace.openLinkText('{safe}', '', false)")
    time.sleep(0.8)


def set_mode(mode: str) -> None:
    """Switch to 'reading' or 'source' view on the active leaf."""
    if mode == "source":
        js = """
        (() => {
            const leaf = app.workspace.activeLeaf;
            if (leaf && leaf.view && leaf.view.setState) {
                leaf.view.setState({ mode: 'source', source: true }, { history: false });
            }
        })()
        """
    else:
        js = """
        (() => {
            const leaf = app.workspace.activeLeaf;
            if (leaf && leaf.view && leaf.view.setState) {
                leaf.view.setState({ mode: 'preview' }, { history: false });
            }
        })()
        """
    evaluate(js)
    time.sleep(0.4)


def scroll_to(px: int) -> None:
    """Scroll the reading-view pane to the given pixel offset."""
    evaluate(f"""
    (() => {{
        const el = document.querySelector('.markdown-preview-view');
        if (el) el.scrollTop = {px};
    }})()
    """)
    time.sleep(0.3)


def scroll_source_to(px: int) -> None:
    """Scroll the source/edit-view pane to the given pixel offset."""
    evaluate(f"""
    (() => {{
        const el = document.querySelector('.cm-scroller');
        if (el) el.scrollTop = {px};
    }})()
    """)
    time.sleep(0.3)

# ---------------------------------------------------------------------------
# Style toggle helpers
# ---------------------------------------------------------------------------

# Maps style key -> (body class to add, body class to remove if any)
_STYLE_CLASSES = {
    "accent-pink":       ("delightful-accent-pink",   None),
    "accent-danger":     ("delightful-accent-danger",  None),
    "accent-gold":       ("delightful-accent-gold",    None),
    "accent-cyan":       ("delightful-accent-cyan",    None),
    "accent-green":      ("delightful-accent-green",   None),
    "accent-purple":     ("delightful-accent-purple",  None),
    "shadow-subtle":     ("delightful-shadow-subtle",  None),
    "shadow-none":       ("delightful-shadow-none",    None),
    "border-subtle":     ("delightful-border-subtle",  None),
    "heading-compact":   ("delightful-heading-compact", None),
    "heading-large":     ("delightful-heading-large",  None),
    "animations-off":    ("delightful-animations-off", None),
}


def set_style(settings: dict) -> None:
    """Toggle body classes for accent/shadow/border/heading/animations.

    settings is a dict like {'accent-pink': True, 'shadow-subtle': True}.
    """
    adds = []
    for key, enabled in settings.items():
        if enabled and key in _STYLE_CLASSES:
            cls = _STYLE_CLASSES[key][0]
            adds.append(cls)

    if adds:
        cls_str = "','".join(adds)
        evaluate(f"document.body.classList.add('{cls_str}')")
    time.sleep(0.3)


def reset_style() -> None:
    """Remove all delightful style-variant classes from body."""
    all_classes = [v[0] for v in _STYLE_CLASSES.values()]
    cls_str = "','".join(all_classes)
    evaluate(f"document.body.classList.remove('{cls_str}')")
    time.sleep(0.3)

# ---------------------------------------------------------------------------
# Debug CSS injection
# ---------------------------------------------------------------------------

_DEBUG_STYLE_ID = "delightful-debug-overlay"


def inject_debug_css(css: str) -> None:
    """Inject (or replace) a debug style element."""
    escaped = css.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    evaluate(f"""
    (() => {{
        let s = document.getElementById('{_DEBUG_STYLE_ID}');
        if (!s) {{
            s = document.createElement('style');
            s.id = '{_DEBUG_STYLE_ID}';
            document.head.appendChild(s);
        }}
        s.textContent = `{escaped}`;
    }})()
    """)
    time.sleep(0.2)


def remove_debug_css() -> None:
    """Remove the debug overlay style element."""
    evaluate(f"document.getElementById('{_DEBUG_STYLE_ID}')?.remove()")
    time.sleep(0.1)

# ---------------------------------------------------------------------------
# Modals and palettes
# ---------------------------------------------------------------------------

def open_settings() -> None:
    evaluate("app.setting.open()")
    time.sleep(0.5)


def open_command_palette() -> None:
    evaluate("app.commands.executeCommandById('command-palette:open')")
    time.sleep(0.4)


def open_graph() -> None:
    evaluate("app.commands.executeCommandById('graph:open')")
    time.sleep(0.8)


def close_modal() -> None:
    """Press Escape via CDP Input events."""
    cdp("Input.dispatchKeyEvent", {
        "type": "keyDown",
        "key": "Escape",
        "code": "Escape",
        "windowsVirtualKeyCode": 27,
        "nativeVirtualKeyCode": 27,
    })
    cdp("Input.dispatchKeyEvent", {
        "type": "keyUp",
        "key": "Escape",
        "code": "Escape",
        "windowsVirtualKeyCode": 27,
        "nativeVirtualKeyCode": 27,
    })
    time.sleep(0.3)

# ---------------------------------------------------------------------------
# Zoom (device metrics override)
# ---------------------------------------------------------------------------

_DEFAULT_WIDTH = 1440
_DEFAULT_HEIGHT = 900


def zoom(scale: float) -> None:
    """Simulate zoom by overriding device metrics."""
    cdp("Emulation.setDeviceMetricsOverride", {
        "width": int(_DEFAULT_WIDTH / scale),
        "height": int(_DEFAULT_HEIGHT / scale),
        "deviceScaleFactor": 2,
        "mobile": False,
    })
    time.sleep(0.4)


def zoom_reset() -> None:
    """Clear device metrics override."""
    cdp("Emulation.clearDeviceMetricsOverride")
    time.sleep(0.3)


# =========================================================================
# CAPTURE SEQUENCES
# =========================================================================

# ---------------------------------------------------------------------------
# Tier 1 -- Baseline (20 shots)
# ---------------------------------------------------------------------------

def tier1_baseline() -> None:
    print("\n=== Tier 1: Baseline ===")

    modes = [
        ("light", "moonstone"),
        ("dark",  "obsidian"),
    ]

    for label, theme_name in modes:
        print(f"\n--- {label} mode ---")
        set_theme(theme_name)

        # Reading view of theme-test.md at various scroll positions
        open_note(NOTE_THEME_TEST)
        set_mode("reading")
        scroll_to(0)
        screenshot(f"baseline-{label}-reading-top", "baseline")

        scroll_to(1100)
        screenshot(f"baseline-{label}-reading-mid", "baseline")

        scroll_to(2200)
        screenshot(f"baseline-{label}-reading-bottom", "baseline")

        # Daily note
        open_note(NOTE_DAILY)
        set_mode("reading")
        screenshot(f"baseline-{label}-daily", "baseline")

        # Density test
        open_note(NOTE_DENSITY)
        set_mode("reading")
        screenshot(f"baseline-{label}-density", "baseline")

        # Source/edit view
        open_note(NOTE_THEME_TEST)
        set_mode("source")
        screenshot(f"baseline-{label}-source", "baseline")

        # Settings modal
        open_settings()
        screenshot(f"baseline-{label}-settings", "baseline")
        close_modal()

        # Command palette
        open_command_palette()
        screenshot(f"baseline-{label}-command", "baseline")
        close_modal()

        # Graph view
        open_graph()
        screenshot(f"baseline-{label}-graph", "baseline")
        close_modal()

        # Sidebar
        screenshot(f"baseline-{label}-sidebar", "baseline")


# ---------------------------------------------------------------------------
# Tier 2 -- Accents (12 shots)
# ---------------------------------------------------------------------------

def tier2_accents() -> None:
    print("\n=== Tier 2: Accents ===")

    accents = ["pink", "danger", "gold", "cyan", "green", "purple"]
    modes = [
        ("light", "moonstone"),
        ("dark",  "obsidian"),
    ]

    for accent in accents:
        for label, theme_name in modes:
            set_theme(theme_name)
            reset_style()
            set_style({f"accent-{accent}": True})

            open_note(NOTE_THEME_TEST)
            set_mode("reading")
            scroll_to(1100)
            screenshot(f"accent-{accent}-{label}", "accents")

            reset_style()


# ---------------------------------------------------------------------------
# Tier 3 -- Permutations (12 shots, dark mode only)
# ---------------------------------------------------------------------------

def tier3_permutations() -> None:
    print("\n=== Tier 3: Permutations ===")

    set_theme("obsidian")

    combos: list[tuple[str, dict, str, str | None, int | None]] = [
        # (name, style_dict, note, view_mode, scroll_px)
        ("shadow-subtle-reading",      {"shadow-subtle": True},                     NOTE_THEME_TEST, "reading", 0),
        ("shadow-none-reading",        {"shadow-none": True},                       NOTE_THEME_TEST, "reading", 0),
        ("shadow-none-settings",       {"shadow-none": True},                       None,            None,      None),
        ("border-subtle-reading",      {"border-subtle": True},                     NOTE_THEME_TEST, "reading", 0),
        ("border-subtle-settings",     {"border-subtle": True},                     None,            None,      None),
        ("border-shadow-subtle",       {"border-subtle": True, "shadow-subtle": True}, NOTE_THEME_TEST, "reading", 0),
        ("heading-compact-reading",    {"heading-compact": True},                   NOTE_THEME_TEST, "reading", 0),
        ("heading-large-reading",      {"heading-large": True},                     NOTE_THEME_TEST, "reading", 0),
        ("heading-large-border",       {"heading-large": True, "border-subtle": True}, NOTE_THEME_TEST, "reading", 0),
        ("animations-off-source",      {"animations-off": True},                    NOTE_THEME_TEST, "source",  None),
        ("all-subtle-combo",           {
            "shadow-subtle": True,
            "border-subtle": True,
            "heading-compact": True,
        },                                                                           NOTE_THEME_TEST, "reading", 0),
    ]

    for name, styles, note, view_mode, scroll_px in combos:
        reset_style()
        set_style(styles)

        if note:
            open_note(note)
        if view_mode:
            set_mode(view_mode)
        if scroll_px is not None:
            scroll_to(scroll_px)

        # Special handling for settings shots
        if "settings" in name:
            open_settings()
            screenshot(name, "permutations")
            close_modal()
        else:
            screenshot(name, "permutations")

    # Canvas shot -- attempt but skip gracefully if unavailable
    reset_style()
    set_style({"shadow-none": True})
    try:
        evaluate("app.commands.executeCommandById('canvas:new-file')")
        time.sleep(1.0)
        screenshot("shadow-none-canvas", "permutations")
        close_modal()
    except Exception:
        print("  [SKIP] shadow-none-canvas (canvas not available)")

    reset_style()


# ---------------------------------------------------------------------------
# Tier 4 -- UX Detail (16 shots)
# ---------------------------------------------------------------------------

def tier4_ux_detail() -> None:
    print("\n=== Tier 4: UX Detail ===")

    debug_heading_css = """
    .markdown-rendered h1, .markdown-rendered h2, .markdown-rendered h3,
    .markdown-rendered h4, .markdown-rendered h5, .markdown-rendered h6 {
        outline: 2px solid red !important;
        outline-offset: -1px;
    }
    .markdown-rendered p {
        outline: 2px solid blue !important;
        outline-offset: -1px;
    }
    """

    # --- Spacing debug (4 shots) ---
    print("\n  -- Spacing debug --")
    for label, theme_name in [("light", "moonstone"), ("dark", "obsidian")]:
        set_theme(theme_name)

        # Headings debug on theme-test
        open_note(NOTE_THEME_TEST)
        set_mode("reading")
        scroll_to(0)
        inject_debug_css(debug_heading_css)
        screenshot(f"spacing-headings-{label}", "ux-detail")
        remove_debug_css()

        # Density debug
        open_note(NOTE_DENSITY)
        set_mode("reading")
        inject_debug_css(debug_heading_css)
        screenshot(f"spacing-density-{label}", "ux-detail")
        remove_debug_css()

    # --- Zoomed shots (3 shots) ---
    print("\n  -- Zoomed detail --")
    set_theme("obsidian")

    # Inline code zoom
    open_note(NOTE_THEME_TEST)
    set_mode("reading")
    scroll_to(0)
    zoom(2.0)
    screenshot("zoom-inline-code-dark", "ux-detail")

    # Callout zoom
    scroll_to(1100)
    screenshot("zoom-callout-dark", "ux-detail")

    # Table zoom
    scroll_to(2200)
    screenshot("zoom-table-dark", "ux-detail")
    zoom_reset()

    # --- Scrollbar (2 shots) ---
    print("\n  -- Scrollbar --")
    for label, theme_name in [("light", "moonstone"), ("dark", "obsidian")]:
        set_theme(theme_name)
        # Scroll sidebar file-explorer to reveal scrollbar thumb
        evaluate("""
        (() => {
            const el = document.querySelector('.nav-files-container');
            if (el) el.scrollTop = 200;
        })()
        """)
        time.sleep(0.4)
        screenshot(f"scrollbar-{label}", "ux-detail")

    # --- Focus ring (2 shots) ---
    print("\n  -- Focus ring --")
    set_theme("obsidian")

    # Focus a clickable element
    evaluate("""
    (() => {
        const btn = document.querySelector('.clickable-icon');
        if (btn) btn.focus();
    })()
    """)
    time.sleep(0.3)
    screenshot("focus-ring-button", "ux-detail")

    # Focus input in settings
    open_settings()
    evaluate("""
    (() => {
        const input = document.querySelector('.setting-item input, .setting-item .search-input-container input');
        if (input) input.focus();
    })()
    """)
    time.sleep(0.3)
    screenshot("focus-ring-settings-input", "ux-detail")
    close_modal()

    # --- Hover (1 shot) ---
    print("\n  -- Hover --")
    # Move mouse over a nav item
    evaluate("""
    (() => {
        const el = document.querySelector('.nav-file-title');
        if (el) {
            const rect = el.getBoundingClientRect();
            window.__hoverX = rect.x + rect.width / 2;
            window.__hoverY = rect.y + rect.height / 2;
        }
    })()
    """)
    hx = evaluate("window.__hoverX") or 200
    hy = evaluate("window.__hoverY") or 300
    cdp("Input.dispatchMouseEvent", {
        "type": "mouseMoved",
        "x": float(hx),
        "y": float(hy),
    })
    time.sleep(0.3)
    screenshot("hover-nav-item", "ux-detail")

    # --- Checkboxes zoomed (1 shot) ---
    print("\n  -- Checkboxes --")
    open_note(NOTE_DAILY)
    set_mode("reading")
    # Scroll to task area if needed
    evaluate("""
    (() => {
        const cb = document.querySelector('.task-list-item');
        if (cb) cb.scrollIntoView({ block: 'center' });
    })()
    """)
    time.sleep(0.3)
    zoom(2.0)
    screenshot("zoom-checkboxes", "ux-detail")
    zoom_reset()

    # --- Tag colors zoomed (1 shot) ---
    print("\n  -- Tags --")
    open_note(NOTE_THEME_TEST)
    set_mode("reading")
    evaluate("""
    (() => {
        const tag = document.querySelector('.tag, a.tag');
        if (tag) tag.scrollIntoView({ block: 'center' });
    })()
    """)
    time.sleep(0.3)
    zoom(2.0)
    screenshot("zoom-tag-colors", "ux-detail")
    zoom_reset()

    # --- Blockquote nesting zoomed (1 shot) ---
    print("\n  -- Blockquotes --")
    evaluate("""
    (() => {
        const bq = document.querySelector('blockquote blockquote, .markdown-rendered blockquote');
        if (bq) bq.scrollIntoView({ block: 'center' });
    })()
    """)
    time.sleep(0.3)
    zoom(2.0)
    screenshot("zoom-blockquote-nesting", "ux-detail")
    zoom_reset()

    # --- Code syntax zoomed (1 shot) ---
    print("\n  -- Code syntax --")
    evaluate("""
    (() => {
        const pre = document.querySelector('pre code, .markdown-rendered pre');
        if (pre) pre.scrollIntoView({ block: 'center' });
    })()
    """)
    time.sleep(0.3)
    zoom(2.0)
    screenshot("zoom-code-syntax", "ux-detail")
    zoom_reset()


# ---------------------------------------------------------------------------
# Tier 5 -- Computed Values
# ---------------------------------------------------------------------------

COMPUTED_JS = """
JSON.stringify({
  headings: ['h1','h2','h3','h4','h5','h6'].map(tag => {
    const el = document.querySelector(`.markdown-rendered ${tag}`);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { tag, fontSize: cs.fontSize, marginTop: cs.marginTop, marginBottom: cs.marginBottom, lineHeight: cs.lineHeight };
  }).filter(Boolean),
  paragraphs: Array.from(document.querySelectorAll('.markdown-rendered p')).slice(0,3).map(p => {
    const cs = getComputedStyle(p);
    return { marginTop: cs.marginTop, marginBottom: cs.marginBottom, lineHeight: cs.lineHeight };
  }),
  inlineCode: (() => {
    const c = document.querySelector('.markdown-rendered code:not(pre code)');
    if (!c) return null;
    const cs = getComputedStyle(c);
    const ps = getComputedStyle(c.parentElement);
    return { fontSize: cs.fontSize, parentFontSize: ps.fontSize, padding: cs.padding, border: cs.border, borderRadius: cs.borderRadius };
  })()
}, null, 2)
"""


def tier5_computed_values() -> None:
    print("\n=== Tier 5: Computed Values ===")

    set_theme("obsidian")
    open_note(NOTE_THEME_TEST)
    set_mode("reading")
    time.sleep(0.5)

    scales = [
        ("default",  {}),
        ("compact",  {"heading-compact": True}),
        ("large",    {"heading-large": True}),
    ]

    for scale_name, style in scales:
        reset_style()
        if style:
            set_style(style)
        time.sleep(0.3)

        raw = evaluate(COMPUTED_JS)
        if raw:
            out_path = BASE_DIR / "reports" / f"computed-spacing-{scale_name}.json"
            with open(out_path, "w") as f:
                f.write(raw)
            print(f"  Saved {out_path.name}")
        else:
            print(f"  [WARN] No computed values for {scale_name}")
            _failures.append(f"computed-spacing-{scale_name}: no data returned")

    reset_style()


# =========================================================================
# Main
# =========================================================================

def main() -> None:
    print("Delightful Obsidian Theme -- Visual Audit")
    print(f"Output: {BASE_DIR}\n")

    # Verify Obsidian is reachable before doing anything
    url = f"http://{CDP_HOST}:{CDP_PORT}/json"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            targets = json.loads(resp.read())
        print(f"Found {len(targets)} CDP target(s).")
    except Exception as e:
        print(
            f"ERROR: Cannot connect to Obsidian CDP on port {CDP_PORT}.\n"
            f"  Start Obsidian with:\n"
            f"    open -a Obsidian --args --remote-debugging-port={CDP_PORT} --remote-allow-origins=*\n"
            f"  ({e})"
        )
        sys.exit(1)

    ensure_dirs()
    connect()

    try:
        tier1_baseline()
        tier2_accents()
        tier3_permutations()
        tier4_ux_detail()
        tier5_computed_values()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nFATAL: {e}")
        _failures.append(f"fatal: {e}")
    finally:
        # Clean up any leftover debug CSS or style overrides
        try:
            remove_debug_css()
            reset_style()
            zoom_reset()
        except Exception:
            pass
        disconnect()

    # Summary
    print("\n" + "=" * 50)
    print("AUDIT COMPLETE")
    print(f"  Screenshots captured: {_shot_count}")
    print(f"  Failures:             {len(_failures)}")
    print(f"  Output directory:     {BASE_DIR}")
    if _failures:
        print("\n  Failed items:")
        for f in _failures:
            print(f"    - {f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
