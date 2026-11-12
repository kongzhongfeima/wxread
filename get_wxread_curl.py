from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

OUTPUT = Path(__file__).resolve().parent / "wxread_curl.txt"


def bash_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    captured = []

    def capture(response):
        url = urlsplit(response.url)
        if (
            captured
            or url.hostname != "weread.qq.com"
            or url.path != "/web/book/read"
            or response.request.method != "POST"
        ):
            return

        try:
            result = response.json()
        except Exception:
            return

        if not isinstance(result, dict) or result.get("succ") != 1:
            print("发现 read 请求，但未成功，请继续正常阅读。")
            return

        request = response.request
        headers = request.all_headers()
        if not headers.get("cookie"):
            print("没有捕获到 Cookie，请继续阅读后重试。")
            return

        parts = ["curl " + bash_quote(request.url)]
        for name, value in headers.items():
            if not name.startswith(":"):
                parts.append("-H " + bash_quote(f"{name}: {value}"))

        if request.post_data:
            parts.append("--data-raw " + bash_quote(request.post_data))

        OUTPUT.write_text(" \\\n  ".join(parts), encoding="utf-8")
        captured.append(True)
        print(f"获取成功，已保存到：{OUTPUT}")

    # 在整个浏览器会话中监听，新标签页也能捕获。
    context.on("response", capture)
    page.goto("https://weread.qq.com/", wait_until="domcontentloaded")
    print("请扫码登录，打开《三体》并阅读、翻页，等待自动捕获。")
    print("需要停止时，在终端按 Ctrl+C。")

    try:
        while not captured and context.pages:
            context.pages[0].wait_for_timeout(500)
    except KeyboardInterrupt:
        print("已停止。")
    finally:
        browser.close()
