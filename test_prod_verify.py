"""Verify production deploy of InstaHotel auth on instanoucentista.streamlit.app."""
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs

URL = "https://instanoucentista.streamlit.app/"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    # Streamlit renders client-side; the link with the OAuth href is the
    # most reliable signal that auth.py has executed.
    pg.wait_for_selector("a[href*='supabase.co/auth/v1/authorize']", timeout=120000)
    print("OK: login screen rendered on prod")

    pg.screenshot(path="test_prod_login.png", full_page=True)

    google_btn = pg.locator("a:has-text('Sign in with Google')").first
    href = google_btn.get_attribute("href")
    u = urlparse(href)
    q = parse_qs(u.query)
    print(f"OAuth host: {u.netloc}")
    print(f"OAuth provider: {q.get('provider', ['?'])[0]}")
    print(f"OAuth redirect_to: {q.get('redirect_to', ['?'])[0]}")
    print(f"OAuth has PKCE: {'code_challenge' in q} method={q.get('code_challenge_method', ['?'])[0]}")

    rt = q.get("redirect_to", [""])[0]
    expected = "https://instanoucentista.streamlit.app"
    if rt == expected:
        print(f"PASS: redirect_to matches prod URL")
    elif rt == "http://localhost:8501":
        print(f"FAIL: redirect_to is localhost — APP_URL not set in Streamlit Cloud secrets")
    else:
        print(f"FAIL: unexpected redirect_to '{rt}' (expected '{expected}')")

    # Confirm no page-discovery leak
    body = pg.content()
    leaks = [n for n in ("Stats", "Gallery", "Batch Generate", "Carousel") if n in body]
    print(f"Nav leak check: {'CLEAN' if not leaks else 'LEAKED: ' + str(leaks)}")
    b.close()
