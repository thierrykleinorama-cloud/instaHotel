"""
InstaHotel - Database Connection Module
Handles Supabase connection following the hotelPandL singleton pattern.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# Singleton
_supabase_client: Optional[Client] = None

# Table name constants
TABLE_MEDIA_LIBRARY = "media_library"
TABLE_TAG_CORRECTIONS = "tag_corrections"
TABLE_EDITORIAL_RULES = "editorial_rules"
TABLE_SEASONAL_THEMES = "seasonal_themes"
TABLE_EDITORIAL_CALENDAR = "editorial_calendar"


def _get_secret(key: str) -> Optional[str]:
    """Get a secret from st.secrets (Streamlit Cloud) or os.environ (local)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def get_supabase() -> Client:
    """Get or create Supabase client (singleton)."""
    global _supabase_client
    if _supabase_client is None:
        url = _get_secret("SUPABASE_URL")
        key = _get_secret("SUPABASE_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env or Streamlit secrets"
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


def test_connection() -> bool:
    """Test database connection by querying media_library."""
    try:
        client = get_supabase()
        client.table(TABLE_MEDIA_LIBRARY).select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
