"""
InstaHotel — API Status & Credits
Check API connectivity and access billing pages.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import os
import streamlit as st
from app.components.ui import sidebar_css, page_title

sidebar_css()
page_title("API Status", "Check API keys and manage credits")


def _get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


# -------------------------------------------------------
# API definitions
# -------------------------------------------------------
APIS = [
    {
        "name": "Anthropic (Claude)",
        "key_name": "ANTHROPIC_API_KEY",
        "used_for": "Captions, scenarios, vision analysis, carousel AI",
        "billing_url": "https://console.anthropic.com/settings/billing",
        "test_fn": "_test_anthropic",
        "priority": "Required for all content generation",
    },
    {
        "name": "Google Gemini (Veo 3.1)",
        "key_name": "GOOGLE_GENAI_API_KEY",
        "used_for": "Veo video generation (fast & standard)",
        "billing_url": "https://aistudio.google.com/billing",
        "test_fn": "_test_google_genai",
        "priority": "Required for Veo reels",
    },
    {
        "name": "Replicate",
        "key_name": "REPLICATE_API_TOKEN",
        "used_for": "Kling video, MusicGen music, Real-ESRGAN upscale",
        "billing_url": "https://replicate.com/account/billing",
        "test_fn": "_test_replicate",
        "priority": "Required for Kling reels & music",
    },
    {
        "name": "Stability AI",
        "key_name": "STABILITY_API_KEY",
        "used_for": "Image upscale (fast/conservative/creative), outpaint",
        "billing_url": "https://platform.stability.ai/account/credits",
        "test_fn": "_test_stability",
        "priority": "Optional (photo enhancement only)",
    },
    {
        "name": "Instagram Graph API",
        "key_name": "INSTAGRAM_ACCESS_TOKEN",
        "used_for": "Publishing posts to Instagram",
        "billing_url": "https://developers.facebook.com/apps/",
        "test_fn": "_test_instagram",
        "priority": "Required for publishing",
    },
    {
        "name": "Supabase",
        "key_name": "SUPABASE_URL",
        "used_for": "Database, file storage",
        "billing_url": "https://supabase.com/dashboard/project/lngrockgpnwaizzyvwsk/settings/billing",
        "test_fn": "_test_supabase",
        "priority": "Required (core database)",
    },
]


# -------------------------------------------------------
# Test functions
# -------------------------------------------------------

def _test_anthropic() -> tuple[bool, str]:
    key = _get_secret("ANTHROPIC_API_KEY")
    if not key:
        return False, "Key not set"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        # Minimal test — just check we can create a client and the key format is valid
        if not key.startswith("sk-ant-"):
            return False, "Key format looks wrong (should start with sk-ant-)"
        # Try a tiny request to check credits
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, f"OK (model: {resp.model})"
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            return False, "No credits remaining"
        return False, str(e)[:100]
    except Exception as e:
        return False, str(e)[:100]


def _test_google_genai() -> tuple[bool, str]:
    key = _get_secret("GOOGLE_GENAI_API_KEY")
    if not key:
        return False, "Key not set"
    try:
        import httpx
        # List models endpoint is free — validates key + checks access
        resp = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": key, "pageSize": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return True, f"OK ({len(models)} models available)"
        elif resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
            return False, "Invalid API key"
        elif resp.status_code == 403:
            return False, "Key valid but access denied — check billing"
        return False, f"HTTP {resp.status_code}: {resp.text[:80]}"
    except Exception as e:
        return False, str(e)[:100]


def _test_replicate() -> tuple[bool, str]:
    key = _get_secret("REPLICATE_API_TOKEN")
    if not key:
        return False, "Key not set"
    try:
        import httpx
        # Check account + billing via API
        resp = httpx.get(
            "https://api.replicate.com/v1/account",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        acc = resp.json()
        username = acc.get("username", "?")
        acc_type = acc.get("type", "?")

        # Check billing — get current spend
        billing_resp = httpx.get(
            "https://api.replicate.com/v1/billing",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if billing_resp.status_code == 200:
            billing = billing_resp.json()
            spend = billing.get("total_amount", 0)
            limit = billing.get("hard_limit", 0)
            if limit and spend >= limit:
                return False, f"Spend limit reached (${spend:.2f} / ${limit:.2f})"
            return True, f"OK (@{username}, ${spend:.2f} / ${limit:.2f} limit)"
        return True, f"OK (@{username}, {acc_type})"
    except Exception as e:
        return False, str(e)[:100]


def _test_stability() -> tuple[bool, str]:
    key = _get_secret("STABILITY_API_KEY")
    if not key:
        return False, "Key not set"
    try:
        import httpx
        resp = httpx.get(
            "https://api.stability.ai/v1/user/balance",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            credits = resp.json().get("credits", 0)
            if isinstance(credits, (int, float)) and credits <= 0:
                return False, f"No credits remaining (balance: {credits:.1f})"
            return True, f"OK ({credits:.1f} credits)"
        elif resp.status_code == 401:
            return False, "Invalid API key"
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)[:100]


def _test_instagram() -> tuple[bool, str]:
    token = _get_secret("INSTAGRAM_ACCESS_TOKEN")
    account_id = _get_secret("INSTAGRAM_ACCOUNT_ID")
    if not token:
        return False, "Token not set"
    if not account_id:
        return False, "Account ID not set"
    try:
        import httpx
        resp = httpx.get(
            f"https://graph.instagram.com/v21.0/{account_id}",
            params={"fields": "username", "access_token": token},
            timeout=10,
        )
        if resp.status_code == 200:
            username = resp.json().get("username", "?")
            return True, f"OK (@{username})"
        return False, f"HTTP {resp.status_code}: {resp.text[:80]}"
    except Exception as e:
        return False, str(e)[:100]


def _test_supabase() -> tuple[bool, str]:
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    if not url or not key:
        return False, "URL or key not set"
    try:
        from src.database import test_connection
        if test_connection():
            return True, "OK"
        return False, "Connection failed"
    except Exception as e:
        return False, str(e)[:100]


TEST_FNS = {
    "_test_anthropic": _test_anthropic,
    "_test_google_genai": _test_google_genai,
    "_test_replicate": _test_replicate,
    "_test_stability": _test_stability,
    "_test_instagram": _test_instagram,
    "_test_supabase": _test_supabase,
}


# -------------------------------------------------------
# Auto-test on load (cached 5 min)
# -------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _run_all_tests() -> dict[str, tuple[bool, str]]:
    """Test all APIs, cached 5 min to avoid hammering on every rerun."""
    results = {}
    for api in APIS:
        test_fn = TEST_FNS.get(api["test_fn"])
        if test_fn:
            try:
                results[api["key_name"]] = test_fn()
            except Exception as e:
                results[api["key_name"]] = (False, str(e)[:100])
    return results


with st.spinner("Checking API connections..."):
    test_results = _run_all_tests()

# -------------------------------------------------------
# Render
# -------------------------------------------------------

for api in APIS:
    key_name = api["key_name"]
    key_val = _get_secret(key_name)
    ok, msg = test_results.get(key_name, (False, "Not tested"))

    with st.container(border=True):
        col_info, col_status, col_action = st.columns([3, 2, 1])

        with col_info:
            st.markdown(f"**{api['name']}**")
            st.caption(api["used_for"])
            st.caption(f"*{api['priority']}*")

        with col_status:
            if not key_val:
                st.error("Key not configured")
            elif ok:
                st.success(msg)
            else:
                st.error(msg)

        with col_action:
            if not ok:
                st.link_button(":material/warning: Add Credits", api["billing_url"], use_container_width=True, type="primary")
            else:
                st.link_button("Billing", api["billing_url"], use_container_width=True)

# -------------------------------------------------------
# Refresh
# -------------------------------------------------------
st.divider()

if st.button("Re-test All", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.caption("API keys are stored in `.env` at the project root. On Streamlit Cloud, use the Secrets manager.")
