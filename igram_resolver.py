"""
Instagram media URL resolver via igram.world using Playwright headless browser.
"""
import threading
from playwright.sync_api import sync_playwright

_lock = threading.Lock()


def resolve(instagram_url: str, timeout: int = 20000) -> list[str]:
    """
    Resolve an Instagram URL to direct media download URLs.

    Args:
        instagram_url: Instagram reel/post URL.
        timeout: Max wait time for API response in ms.

    Returns:
        List of direct media URLs.
    """
    media_urls = []

    with _lock, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://igram.world/", wait_until="networkidle")

        # Dismiss cookie consent overlay.
        consent_btn = page.query_selector("button.fc-cta-consent, .fc-button-label")
        if consent_btn:
            consent_btn.click()
            page.wait_for_timeout(500)

        # Fill URL.
        input_el = page.query_selector("input[type='text']")
        if not input_el:
            browser.close()
            return []
        input_el.fill(instagram_url)

        # Capture API response.
        api_response = []

        def on_response(response):
            if "convert" in response.url:
                try:
                    api_response.append(response.json())
                except:
                    pass

        page.on("response", on_response)

        # Click download.
        button = page.query_selector("button[type='submit'], button.btn")
        if button:
            button.click()

        # Wait for API response.
        page.wait_for_timeout(timeout)
        browser.close()

    # Extract URLs from response (handles both flat and nested carousel formats).
    def _extract(obj):
        if isinstance(obj, str) and obj.startswith("http"):
            media_urls.append(obj)
        elif isinstance(obj, dict):
            u = obj.get("url", "")
            if isinstance(u, str) and u.startswith("http"):
                media_urls.append(u)
            else:
                for v in obj.values():
                    if isinstance(v, (list, dict)):
                        _extract(v)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item)

    _extract(api_response)

    # Deduplicate preserving order.
    seen = set()
    unique = []
    for u in media_urls:
        if u not in seen and "igram.world" in u:
            seen.add(u)
            unique.append(u)

    return unique


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.instagram.com/reel/DWMdSJCCdgc/"
    print(f"Resolving: {url}")

    urls = resolve(url)
    if urls:
        print(f"Found {len(urls)} media URL(s):")
        for u in urls:
            print(f"  {u[:150]}")
    else:
        print("No media URLs found.")
