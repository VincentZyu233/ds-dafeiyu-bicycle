import pathlib
import subprocess
import tempfile
import threading
import http.server
import socketserver
import functools
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "assets" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# (commit, 中文标签, 文件名)
VERSIONS = [
    ("fc91e7e1", "蓝色大肥鱼", "v1-fish"),
    ("9636ff8c", "大肥鱼猫娘", "v2-catgirl"),
    ("af80531c", "蓝发鲸鱼女仆", "v3-whale-maid"),
    ("HEAD", "鲸鱼女仆·海边场景", "v4-scene"),
]


def get_html(commit: str) -> str:
    if commit == "HEAD":
        return (REPO / "index.html").read_text(encoding="utf-8")
    r = subprocess.run(
        ["git", "show", f"{commit}:index.html"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git show {commit} 失败: {r.stderr}")
    return r.stdout


def launch(pw):
    candidates = [
        {"executable_path": CHROME},
        {"executable_path": EDGE},
        {"channel": "chrome"},
        {"channel": "msedge"},
    ]
    last = None
    for kw in candidates:
        try:
            return pw.chromium.launch(headless=True, **kw)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def main() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dafeiyu-"))
    names = []
    for commit, _label, fname in VERSIONS:
        p = tmp / f"{fname}.html"
        p.write_text(get_html(commit), encoding="utf-8")
        names.append(fname)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    try:
        with sync_playwright() as pw:
            browser = launch(pw)
            page = browser.new_page(viewport={"width": 1200, "height": 675})
            for fname in names:
                page.goto(f"http://127.0.0.1:{port}/{fname}.html", wait_until="networkidle")
                page.add_style_tag(
                    content="* { animation: none !important; transition: none !important; }"
                )
                page.wait_for_timeout(400)
                dest = OUT / f"{fname}.png"
                page.screenshot(path=str(dest))
                print(f"saved {dest}")
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
