"""
InstaHotel — Authentication (Supabase Auth)
Gate the app behind login: Google OAuth (primary) + email/password (fallback).

Shared Supabase project with hotelPandL + suppliers — users created in any
sibling app can sign in here.
"""
import os

import streamlit as st

from src.database import get_supabase


_CODE_VERIFIER_KEY = "supabase.auth.token-code-verifier"


@st.cache_resource
def _get_cv_store():
    """Server-side store for PKCE code_verifier (survives Streamlit reruns)."""
    return {}


def _get_app_url() -> str:
    """Return the app URL (production via secrets, else local dev)."""
    try:
        if st.secrets.get("APP_URL"):
            return st.secrets["APP_URL"]
    except Exception:
        pass
    return os.getenv("APP_URL", "http://localhost:8501")


def handle_oauth_callback():
    """Exchange ?code= URL param for a Supabase session. Call at top of main.py."""
    params = st.query_params
    if "code" not in params:
        return

    code = params["code"]
    store = _get_cv_store()
    code_verifier = store.get("cv")

    if not code_verifier:
        st.error("OAuth session expired. Please try signing in again.")
        st.query_params.clear()
        return

    try:
        client = get_supabase()
        # Restore code_verifier into the client's storage so the exchange matches
        client.auth._storage.set_item(_CODE_VERIFIER_KEY, code_verifier)
        response = client.auth.exchange_code_for_session({"auth_code": code})
        if response.session:
            st.session_state["auth_access_token"] = response.session.access_token
            st.session_state["auth_refresh_token"] = response.session.refresh_token
            st.session_state["auth_user_email"] = response.user.email
    except Exception as e:
        st.error(f"OAuth login failed: {e}")

    # Force a fresh OAuth URL + code_verifier pair on the next login attempt
    store.pop("cv", None)
    store.pop("oauth_url", None)
    st.query_params.clear()


def check_auth() -> bool:
    """Return True if the user has a valid session."""
    access_token = st.session_state.get("auth_access_token")
    refresh_token = st.session_state.get("auth_refresh_token")

    if not access_token or not refresh_token:
        return False

    try:
        client = get_supabase()
        client.auth.set_session(access_token, refresh_token)
        session = client.auth.get_session()
        if session:
            st.session_state["auth_access_token"] = session.access_token
            st.session_state["auth_refresh_token"] = session.refresh_token
            return True
    except Exception:
        _clear_auth_state()

    return False


def login_form(app_name: str = "InstaHotel"):
    """Render login page: Google OAuth button + email/password fallback."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"## :material/lock: {app_name}")
        st.caption("Sign in to continue")

        # -- Google OAuth (primary) --
        try:
            store = _get_cv_store()
            # Generate OAuth URL only once — reuse on reruns so code_verifier stays matched
            if "oauth_url" not in store:
                client = get_supabase()
                response = client.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": _get_app_url()},
                })
                store["oauth_url"] = response.url
                store["cv"] = client.auth._storage.get_item(_CODE_VERIFIER_KEY)

            st.link_button(
                ":material/login: Sign in with Google",
                url=store["oauth_url"],
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Google login failed: {e}")

        st.divider()
        st.caption("Or sign in with email")

        # -- Email/password (fallback) --
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter email and password.")
                return
            try:
                client = get_supabase()
                response = client.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                st.session_state["auth_access_token"] = response.session.access_token
                st.session_state["auth_refresh_token"] = response.session.refresh_token
                st.session_state["auth_user_email"] = response.user.email
                st.rerun()
            except Exception as e:
                msg = str(e)
                if "Invalid login credentials" in msg:
                    st.error("Invalid email or password.")
                else:
                    st.error(f"Login failed: {msg}")

        # Forgot password
        if st.button("Forgot password?", key="forgot_pw"):
            st.session_state["show_reset"] = True

        if st.session_state.get("show_reset"):
            reset_email = st.text_input(
                "Enter your email to receive a reset link", key="reset_email"
            )
            if st.button("Send reset link", key="send_reset"):
                if not reset_email:
                    st.error("Please enter your email.")
                else:
                    try:
                        get_supabase().auth.reset_password_for_email(reset_email)
                        st.success("Reset link sent! Check your inbox.")
                        st.session_state["show_reset"] = False
                    except Exception as e:
                        st.error(f"Failed to send reset link: {e}")


def logout():
    """Sign out and clear session."""
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    _clear_auth_state()
    st.rerun()


def _clear_auth_state():
    for key in ("auth_access_token", "auth_refresh_token", "auth_user_email"):
        st.session_state.pop(key, None)
