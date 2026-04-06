#!/usr/bin/env python3
"""
CDP helper for Obsidian theme development.
Connects to Obsidian via Chrome DevTools Protocol for:
- Screenshots
- Live CSS injection
- DOM class crawling
- Computed style queries

Usage:
  python3 scripts/cdp.py screenshot [filename]
  python3 scripts/cdp.py crawl
  python3 scripts/cdp.py inject <css_file>
  python3 scripts/cdp.py style <selector> <property>

Requires: pip install websocket-client
Obsidian must be running with: --remote-debugging-port=9333
"""

import sys
import json
import base64
import urllib.request

CDP_PORT = 9333
CDP_HOST = "localhost"


def get_page_ws():
    """Get the WebSocket URL for the Obsidian main page."""
    url = f"http://{CDP_HOST}:{CDP_PORT}/json"
    try:
        with urllib.request.urlopen(url) as resp:
            targets = json.loads(resp.read())
    except Exception as e:
        print(f"Error: Cannot connect to CDP on port {CDP_PORT}. Is Obsidian running with --remote-debugging-port={CDP_PORT}?")
        sys.exit(1)

    for target in targets:
        if target.get("type") == "page" and "obsidian" in target.get("url", "").lower():
            return target["webSocketDebuggerUrl"]

    # Fallback: first page target
    pages = [t for t in targets if t.get("type") == "page"]
    if pages:
        return pages[0]["webSocketDebuggerUrl"]

    print("Error: No page targets found")
    sys.exit(1)


def cdp_send(ws, method, params=None, msg_id=1):
    """Send a CDP command and return the result."""
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    while True:
        response = json.loads(ws.recv())
        if response.get("id") == msg_id:
            return response.get("result", {})


def connect():
    """Connect to Obsidian via CDP."""
    import websocket
    page_ws = get_page_ws()
    ws = websocket.create_connection(page_ws, suppress_origin=True)
    return ws


def screenshot(filename="obsidian-screenshot.png"):
    """Capture a screenshot of Obsidian."""
    ws = connect()
    result = cdp_send(ws, "Page.captureScreenshot", {"format": "png"})
    data = base64.b64decode(result["data"])
    with open(filename, "wb") as f:
        f.write(data)
    print(f"Screenshot saved: {filename} ({len(data)} bytes)")
    ws.close()


def crawl():
    """Crawl all CSS classes in the current Obsidian page."""
    ws = connect()
    result = cdp_send(ws, "Runtime.evaluate", {
        "expression": "[...new Set([...document.querySelectorAll('*')].flatMap(e=>[...e.classList]))].sort().join('\\n')"
    })
    classes = result.get("result", {}).get("value", "")
    print(classes)
    print(f"\n--- {len(classes.split(chr(10)))} unique classes ---")
    ws.close()


def inject(css_file):
    """Inject a CSS file into Obsidian for live preview."""
    with open(css_file, "r") as f:
        css = f.read()
    # Escape backticks and backslashes for template literal
    css = css.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    ws = connect()
    cdp_send(ws, "Runtime.evaluate", {
        "expression": f"let s=document.getElementById('delightful-live')||document.createElement('style');s.id='delightful-live';s.textContent=`{css}`;if(!s.parentNode)document.head.appendChild(s);"
    })
    print(f"Injected {css_file} into Obsidian")
    ws.close()


def style(selector, prop):
    """Query a computed style value."""
    ws = connect()
    result = cdp_send(ws, "Runtime.evaluate", {
        "expression": f"getComputedStyle(document.querySelector('{selector}')).{prop}"
    })
    value = result.get("result", {}).get("value", "not found")
    print(f"{selector} → {prop}: {value}")
    ws.close()


def reload():
    """Reload the Obsidian theme."""
    ws = connect()
    cdp_send(ws, "Runtime.evaluate", {
        "expression": "app.customCss.readThemes().then(() => app.customCss.requestLoadTheme())"
    })
    print("Theme reloaded in Obsidian")
    ws.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "screenshot":
        filename = sys.argv[2] if len(sys.argv) > 2 else "obsidian-screenshot.png"
        screenshot(filename)
    elif cmd == "crawl":
        crawl()
    elif cmd == "inject":
        if len(sys.argv) < 3:
            print("Usage: cdp.py inject <css_file>")
            sys.exit(1)
        inject(sys.argv[2])
    elif cmd == "style":
        if len(sys.argv) < 4:
            print("Usage: cdp.py style <selector> <property>")
            sys.exit(1)
        style(sys.argv[2], sys.argv[3])
    elif cmd == "reload":
        reload()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
