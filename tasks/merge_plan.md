# Merge Plan: Hotel P&L + InstaHotel into One Streamlit App

**Created:** 2026-02-25
**Approach:** Option B — Single codebase, namespaced pages, one Streamlit Cloud deployment

---

## 1. Current State of Both Apps

### 1.1 Hotel P&L (`hotelPandL/`)

**Purpose:** Financial management tool — P&L, cash flow, bank reconciliation.

**Entry point:** `app/main.py`
- Uses legacy Streamlit `pages/` directory convention (auto-discovered)
- `st.set_page_config(...)` called in **every** page file (11 times total)
- sys.path inserts `src/` at the top of each page file
- `load_dotenv(_project_root / ".env")` repeated at top of each page
- No `st.navigation()` or `st.Page()` usage (pure legacy multi-page)

**Pages (10):**
| # | File | Title | Description |
|---|------|-------|-------------|
| - | `main.py` | Hotel P&L Management | Landing page, DB status sidebar |
| 1 | `1_Factures.py` | Factures | Expense invoice CRUD (uses shared `invoice_page.py`) |
| 2 | `2_Revenus.py` | Revenus | Revenue invoice CRUD (same shared component) |
| 3 | `3_Import_Banque.py` | Import Banque | Bank statement import (N43, CSV), credit card ventilation |
| 4 | `4_Rapprochement.py` | Rapprochement | Invoice-to-bank-transaction matching (most complex page) |
| 5 | `5_PnL.py` | P&L | Annual P&L report with expand/collapse, budget editing |
| 6 | `6_CashFlow.py` | Cash Flow | 3-level drill-down cash flow, bank balances, VAT quarterly |
| 7 | `7_Controles.py` | Controles | Data anomaly detection and exclusion |
| 8 | `8_Groupes.py` | Groupes | P&L group dimension management |
| 9 | `9_Categories.py` | Categories | P&L category dimension management |
| 10 | `10_Backup.py` | Backup | Database backup to Supabase storage |

**Components (2):**
- `app/components/ui.py` — `sidebar_css()`, `page_title(text)`, `compact_metrics(items)`
- `app/components/invoice_page.py` — Shared invoice/revenue page renderer

**Services (10 files, ~3,800 LOC):**
- `src/database.py` — Supabase singleton, `_get_secret()`, table constants
- `src/models.py` — Pydantic models: Invoice, BankTransaction, Match, DimGroup, etc.
- `src/utils.py` — Date helpers, VAT calculation, ID generation
- `src/services/bank.py` — N43 parsing, CSV import, ventilation (877 LOC)
- `src/services/cashflow.py` — Annual cash flow summary, bank positions, VAT (725 LOC)
- `src/services/invoices.py` — CRUD, payment status (429 LOC)
- `src/services/matching.py` — Match suggestions, automatch (377 LOC)
- `src/services/backup.py` — DB dump to Supabase Storage (376 LOC)
- `src/services/exceptions.py` — Anomaly detection (313 LOC)
- `src/services/dimensions.py` — Groups/categories CRUD (273 LOC)
- `src/services/pnl.py` — P&L summary computation (237 LOC)
- `src/services/supplier_rules.py` — Auto-categorization rules (112 LOC)
- `src/services/budget.py` — Budget read/write (71 LOC)

**Import pattern:** Each page does:
```python
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))
from services.bank import ...
```
Services import from sibling modules as: `from database import get_supabase`

**DB tables (hotelPandL):** invoices, bank_transactions, matches, dim_groups, dim_categories, bank_positions, pnl_budgets, pnl_settings, supplier_rules, vat_quarterly

---

### 1.2 InstaHotel (`instaHotel/`)

**Purpose:** Instagram content pipeline — media library, AI analysis, editorial calendar.

**Entry point:** `app/main.py`
- Uses legacy Streamlit `pages/` directory convention
- `st.set_page_config(...)` called **only** in `main.py` (NOT in page files)
- sys.path inserts project root at top of each page
- No `load_dotenv` in pages (handled by `src/database.py`)
- Uses `st.switch_page()` and `st.page_link()` with relative paths

**Pages (9):**
| # | File | Title | Description |
|---|------|-------|-------------|
| - | `main.py` | Media Explorer | Landing page, DB status + media count sidebar |
| 1 | `1_Stats.py` | Stats & Gaps | Overview metrics, distribution charts, gap alerts |
| 2 | `2_Gallery.py` | Gallery | Filterable photo/video grid with pagination |
| 3 | `3_Image_Details.py` | Image Details | Full-size image, tag editor, delete |
| 4 | `4_Video_Details.py` | Video Details | Video player, per-scene analysis, tag editor |
| 5 | `5_AI_Lab.py` | AI Lab | Hub linking to Captions and Enhancement |
| 6 | `6_AI_Captions.py` | AI Captions | Instagram caption generation (ES/EN/FR) |
| 7 | `7_AI_Enhancement.py` | AI Enhancement | Upscale, retouch, outpaint |
| 8 | `8_Calendar.py` | Calendar | Editorial posting calendar |
| 9 | `9_Rules.py` | Rules & Themes | Weekly posting rules, seasonal themes |

**Components (4):**
- `app/components/ui.py` — `sidebar_css()`, `page_title(icon_text, title)` (different signature!)
- `app/components/media_selector.py` — Sidebar media selector for AI pages
- `app/components/media_grid.py` — Thumbnail grid with Drive download
- `app/components/tag_editor.py` — Tag correction form

**Services (10 files, ~2,000 LOC):**
- `src/database.py` — Supabase singleton, `_get_secret()`, table constants
- `src/models.py` — VisionAnalysis, SceneAnalysis, MediaItem
- `src/utils.py` — Image encoding, aspect ratio detection
- `src/prompts/caption_generation.py` — Caption generation prompt
- `src/prompts/enhancement.py` — Enhancement prompts
- `src/services/google_drive.py` — OAuth, file listing, download (144 LOC)
- `src/services/media_queries.py` — Supabase queries with Streamlit caching (90 LOC)
- `src/services/media_indexer.py` — Drive scan + Claude Vision indexing (261 LOC)
- `src/services/vision_analyzer.py` — Claude Vision API calls (175 LOC)
- `src/services/video_analyzer.py` — Video frame extraction + analysis (243 LOC)
- `src/services/caption_generator.py` — AI caption generation (119 LOC)
- `src/services/editorial_engine.py` — Calendar generation, media scoring (295 LOC)
- `src/services/editorial_queries.py` — Editorial rules/themes/calendar CRUD (247 LOC)
- `src/services/image_enhancer.py` — Stability AI + Replicate APIs (404 LOC)

**Import pattern:** Each page does:
```python
_root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.insert(0, _root)
from app.components.ui import sidebar_css, page_title
from src.services.media_queries import ...
```
Services import as: `from src.database import get_supabase`

**Cross-page navigation:**
- `2_Gallery.py` -> `st.switch_page("pages/3_Image_Details.py")`
- `3_Image_Details.py` -> `st.switch_page("pages/4_Video_Details.py")`
- `5_AI_Lab.py` -> `st.page_link("pages/6_AI_Captions.py", ...)`
- `6_AI_Captions.py` -> `st.page_link("pages/5_AI_Lab.py", ...)`
- `7_AI_Enhancement.py` -> `st.page_link("pages/5_AI_Lab.py", ...)`

**DB tables (instaHotel):** media_library, tag_corrections, editorial_rules, seasonal_themes, editorial_calendar

---

## 2. Dependency Analysis

### 2.1 requirements.txt Comparison

| Package | hotelPandL | instaHotel | Notes |
|---------|-----------|------------|-------|
| streamlit | >=1.33.0 | >=1.30.0 | Use >=1.33.0 (higher) |
| supabase | >=2.3.0 | >=2.3.0 | Same |
| pandas | >=2.1.0 | - | Only P&L needs it |
| numpy | >=1.26.0 | - | Only P&L needs it |
| openpyxl | >=3.1.0 | - | Excel import |
| xlrd | >=2.0.1 | - | Legacy Excel |
| python-dateutil | >=2.8.2 | - | Date parsing |
| python-dotenv | >=1.0.0 | >=1.0.0 | Same |
| anthropic | - | >=0.80 | Claude API |
| google-api-python-client | - | >=2.100.0 | Drive API |
| google-auth-oauthlib | - | >=1.1.0 | Drive auth |
| google-auth-httplib2 | - | >=0.1.1 | Drive auth |
| Pillow | - | >=10.0.0 | Image processing |
| pillow-heif | - | >=0.14.0 | HEIC support |
| opencv-python-headless | - | >=4.8.0 | Video processing |
| pydantic | - | >=2.0.0 | Data models (both use it but only instaHotel pins) |
| httpx | - | >=0.28 | Enhancement APIs |
| replicate | - | >=1.0 | AI enhancement |

**No conflicts.** All packages are compatible. The merged `requirements.txt` is the union.

### 2.2 Environment Variables

| Variable | hotelPandL | instaHotel | Notes |
|----------|-----------|------------|-------|
| SUPABASE_URL | Yes | Yes | Same value (same project) |
| SUPABASE_KEY | Yes | Yes | Same value |
| SUPABASE_SERVICE_KEY | Yes | - | P&L backup |
| SUPABASE_ACCESS_TOKEN | Yes | - | P&L backup |
| DATABASE_URL | Yes | - | P&L (unused?) |
| SUPABASE_SERVICE_ROLE_KEY | - | Yes | Same as SERVICE_KEY? Check. |
| ANTHROPIC_API_KEY | - | Yes | Claude Vision + captions |
| DRIVE_FOLDER_ID | - | Yes | Google Drive folder |
| STABILITY_API_KEY | - | Yes | Image enhancement |
| REPLICATE_API_TOKEN | - | Yes | Image enhancement |
| GOOGLE_APPLICATION_CREDENTIALS | Yes (optional) | - | Sheets export |
| GOOGLE_DRIVE_TOKEN | - | Yes (Cloud) | Via st.secrets for Drive |

**No conflicts.** The merged `.env` is the union. Both use `SUPABASE_URL` and `SUPABASE_KEY` with the same values. The service key names differ slightly (`SUPABASE_SERVICE_KEY` vs `SUPABASE_SERVICE_ROLE_KEY`) — normalize to one.

### 2.3 `st.set_page_config` Conflict

This is the **biggest technical issue.**

- **hotelPandL** calls `st.set_page_config()` in every page file (11 calls)
- **instaHotel** calls it only in `main.py` (1 call)

In Streamlit's legacy multipage mode, `st.set_page_config()` must be the first Streamlit command on each page and can only be called once per page run. When migrating to `st.navigation()`, `set_page_config` should be called exactly once in the entrypoint.

**Resolution:** Move to `st.navigation()` API. Remove all `st.set_page_config()` calls from page files. Call it once in the new `main.py`.

---

## 3. Proposed Combined Directory Structure

```
hotelNoucentista/          # Renamed repo (or keep instaHotel)
|
|-- app/
|   |-- main.py            # NEW: Hub landing page + st.navigation()
|   |
|   |-- pages/
|   |   |-- pnl/           # Hotel P&L pages
|   |   |   |-- factures.py
|   |   |   |-- revenus.py
|   |   |   |-- import_banque.py
|   |   |   |-- rapprochement.py
|   |   |   |-- pnl.py
|   |   |   |-- cashflow.py
|   |   |   |-- controles.py
|   |   |   |-- groupes.py
|   |   |   |-- categories.py
|   |   |   |-- backup.py
|   |   |
|   |   |-- insta/          # InstaHotel pages
|   |   |   |-- stats.py
|   |   |   |-- gallery.py
|   |   |   |-- image_details.py
|   |   |   |-- video_details.py
|   |   |   |-- ai_lab.py
|   |   |   |-- ai_captions.py
|   |   |   |-- ai_enhancement.py
|   |   |   |-- calendar.py
|   |   |   |-- rules.py
|   |
|   |-- components/
|   |   |-- __init__.py
|   |   |-- ui.py           # MERGED: combine both ui.py into one
|   |   |-- invoice_page.py # From hotelPandL
|   |   |-- media_selector.py  # From instaHotel
|   |   |-- media_grid.py      # From instaHotel
|   |   |-- tag_editor.py      # From instaHotel
|
|-- src/
|   |-- __init__.py
|   |-- shared/             # Shared across both modules
|   |   |-- __init__.py
|   |   |-- database.py     # MERGED: unified Supabase singleton + all table constants
|   |
|   |-- pnl/               # Hotel P&L business logic
|   |   |-- __init__.py
|   |   |-- models.py       # From hotelPandL/src/models.py
|   |   |-- utils.py        # From hotelPandL/src/utils.py
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- bank.py
|   |   |   |-- cashflow.py
|   |   |   |-- invoices.py
|   |   |   |-- matching.py
|   |   |   |-- backup.py
|   |   |   |-- exceptions.py
|   |   |   |-- dimensions.py
|   |   |   |-- pnl.py
|   |   |   |-- supplier_rules.py
|   |   |   |-- budget.py
|   |
|   |-- insta/              # InstaHotel business logic
|   |   |-- __init__.py
|   |   |-- models.py       # From instaHotel/src/models.py
|   |   |-- utils.py        # From instaHotel/src/utils.py
|   |   |-- prompts/
|   |   |   |-- __init__.py
|   |   |   |-- caption_generation.py
|   |   |   |-- enhancement.py
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- google_drive.py
|   |   |   |-- media_queries.py
|   |   |   |-- media_indexer.py
|   |   |   |-- vision_analyzer.py
|   |   |   |-- video_analyzer.py
|   |   |   |-- caption_generator.py
|   |   |   |-- editorial_engine.py
|   |   |   |-- editorial_queries.py
|   |   |   |-- image_enhancer.py
|
|-- scripts/                # Utility scripts (merged from both)
|   |-- pnl/                # hotelPandL scripts
|   |   |-- seed_data.py
|   |   |-- backup_db.py
|   |   |-- ...
|   |-- insta/              # instaHotel scripts
|   |   |-- run_indexer.py
|   |   |-- test_connection.py
|   |   |-- ...
|
|-- supabase/               # Schema files (merged)
|   |-- pnl_schema.sql
|   |-- insta_schema.sql
|   |-- insta_schema_phase1b.sql
|   |-- insta_schema_phase2.sql
|
|-- .env                    # Merged environment variables
|-- .env.example            # Merged example
|-- .gitignore              # Merged
|-- .streamlit/
|   |-- config.toml         # Theme + server settings
|   |-- secrets.toml.example
|-- requirements.txt        # Merged
|-- tasks/                  # Project tracking
|-- README.md               # (if needed)
```

---

## 4. Step-by-Step Migration Plan

### Phase 0: Preparation (in instaHotel repo)

0. **Create a `merge` branch** from `local` to do all work.
1. **Commit everything** on both repos. Ensure clean working trees.
2. **Back up** both repos (zip or extra branch).

### Phase 1: Bring in hotelPandL Code

**Strategy:** Copy files from hotelPandL into instaHotel (not git subtree or submodule — keep it simple since hotelPandL has no ongoing development).

1. **Copy `hotelPandL/src/` into `instaHotel/src/pnl/`:**
   ```bash
   mkdir -p src/pnl/services
   cp hotelPandL/src/models.py src/pnl/models.py
   cp hotelPandL/src/utils.py src/pnl/utils.py
   cp hotelPandL/src/services/*.py src/pnl/services/
   touch src/pnl/__init__.py src/pnl/services/__init__.py
   ```

2. **Reorganize instaHotel src into `src/insta/`:**
   ```bash
   mkdir -p src/insta/services src/insta/prompts
   mv src/models.py src/insta/models.py
   mv src/utils.py src/insta/utils.py
   mv src/prompts/* src/insta/prompts/
   mv src/services/* src/insta/services/
   touch src/insta/__init__.py src/insta/services/__init__.py src/insta/prompts/__init__.py
   ```

3. **Create unified `src/shared/database.py`:**
   - Merge both `database.py` files into one
   - All table constants from both apps in one file
   - Single `get_supabase()` singleton, single `_get_secret()`, single `test_connection()`
   - `test_connection()` should query a table that exists in both schemas (or just test connectivity)

4. **Copy hotelPandL pages into `app/pages/pnl/`:**
   ```bash
   mkdir -p app/pages/pnl
   cp hotelPandL/app/pages/*.py app/pages/pnl/
   ```
   Rename to remove numeric prefixes (navigation will handle ordering):
   - `1_Factures.py` -> `factures.py`
   - `2_Revenus.py` -> `revenus.py`
   - etc.

5. **Reorganize instaHotel pages into `app/pages/insta/`:**
   ```bash
   mkdir -p app/pages/insta
   mv app/pages/*.py app/pages/insta/
   ```
   Rename to remove numeric prefixes.

6. **Copy hotelPandL components:**
   ```bash
   cp hotelPandL/app/components/invoice_page.py app/components/
   ```

7. **Merge `ui.py` files** (see Section 5 for details).

8. **Copy hotelPandL scripts:**
   ```bash
   mkdir -p scripts/pnl
   cp hotelPandL/scripts/*.py scripts/pnl/
   ```
   Move existing instaHotel scripts:
   ```bash
   mkdir -p scripts/insta
   mv scripts/*.py scripts/insta/   # (except archive/)
   ```

9. **Copy schema files:**
   ```bash
   cp hotelPandL/supabase/schema.sql supabase/pnl_schema.sql
   ```

### Phase 2: Rewrite Entry Point (`app/main.py`)

Replace `app/main.py` with a new hub using `st.navigation()`:

```python
"""
Hotel Noucentista — Unified Dashboard
Hub for P&L and Instagram management.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

# Page config — called exactly ONCE
st.set_page_config(
    page_title="Hotel Noucentista",
    page_icon=":hotel:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages
pnl_pages = [
    st.Page("pages/pnl/factures.py", title="Factures", icon=":material/receipt_long:"),
    st.Page("pages/pnl/revenus.py", title="Revenus", icon=":material/payments:"),
    st.Page("pages/pnl/import_banque.py", title="Import Banque", icon=":material/account_balance:"),
    st.Page("pages/pnl/rapprochement.py", title="Rapprochement", icon=":material/link:"),
    st.Page("pages/pnl/pnl.py", title="P&L", icon=":material/bar_chart:"),
    st.Page("pages/pnl/cashflow.py", title="Cash Flow", icon=":material/attach_money:"),
    st.Page("pages/pnl/controles.py", title="Controles", icon=":material/warning:"),
    st.Page("pages/pnl/groupes.py", title="Groupes", icon=":material/folder:"),
    st.Page("pages/pnl/categories.py", title="Categories", icon=":material/category:"),
    st.Page("pages/pnl/backup.py", title="Backup", icon=":material/backup:"),
]

insta_pages = [
    st.Page("pages/insta/stats.py", title="Stats", icon=":material/monitoring:"),
    st.Page("pages/insta/gallery.py", title="Gallery", icon=":material/photo_library:"),
    st.Page("pages/insta/image_details.py", title="Image Details", icon=":material/image:"),
    st.Page("pages/insta/video_details.py", title="Video Details", icon=":material/videocam:"),
    st.Page("pages/insta/ai_lab.py", title="AI Lab", icon=":material/smart_toy:"),
    st.Page("pages/insta/ai_captions.py", title="AI Captions", icon=":material/edit_note:"),
    st.Page("pages/insta/ai_enhancement.py", title="AI Enhancement", icon=":material/auto_awesome:"),
    st.Page("pages/insta/calendar.py", title="Calendar", icon=":material/calendar_month:"),
    st.Page("pages/insta/rules.py", title="Rules", icon=":material/tune:"),
]

pg = st.navigation({
    "P&L": pnl_pages,
    "Instagram": insta_pages,
})

# Shared sidebar footer
with st.sidebar:
    st.divider()
    st.caption("Hotel Noucentista")

pg.run()
```

**Key points:**
- `st.navigation()` replaces the old `pages/` auto-discovery
- Groups ("P&L" and "Instagram") create visual sections in the sidebar
- `st.set_page_config()` is called once, here only
- Each page file becomes a simple script (no `set_page_config` needed)

### Phase 3: Rewrite All Imports

This is the most mechanical but critical step.

#### 3.1 hotelPandL Pages (now in `app/pages/pnl/`)

**Remove from every page:**
```python
# DELETE these lines:
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))
from dotenv import load_dotenv
load_dotenv(_project_root / ".env")
st.set_page_config(...)
```

**Replace service imports:**
```python
# OLD (hotelPandL):
from services.bank import parse_bank_csv, ...
from services.invoices import get_all_invoices, ...
from database import get_supabase, TABLE_INVOICES
from utils import end_of_month
from components.ui import page_title, compact_metrics

# NEW:
from src.pnl.services.bank import parse_bank_csv, ...
from src.pnl.services.invoices import get_all_invoices, ...
from src.shared.database import get_supabase, TABLE_INVOICES
from src.pnl.utils import end_of_month
from app.components.ui import pnl_page_title, compact_metrics
```

#### 3.2 instaHotel Pages (now in `app/pages/insta/`)

**Remove from every page:**
```python
# DELETE these lines:
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
```

**Replace service imports:**
```python
# OLD (instaHotel):
from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media
from src.database import get_supabase, TABLE_MEDIA_LIBRARY

# NEW:
from app.components.ui import sidebar_css, insta_page_title
from src.insta.services.media_queries import fetch_all_media
from src.shared.database import get_supabase, TABLE_MEDIA_LIBRARY
```

#### 3.3 Components

**`app/components/invoice_page.py`** — rewrite imports:
```python
# OLD:
from services.invoices import ...
from services.dimensions import ...
from database import get_supabase, TABLE_MATCHES

# NEW:
from src.pnl.services.invoices import ...
from src.pnl.services.dimensions import ...
from src.shared.database import get_supabase, TABLE_MATCHES
```

**`app/components/media_selector.py`** — rewrite imports:
```python
# OLD:
from src.services.media_queries import ...
from src.services.google_drive import ...

# NEW:
from src.insta.services.media_queries import ...
from src.insta.services.google_drive import ...
```

Same pattern for `media_grid.py` and `tag_editor.py`.

#### 3.4 Services (internal cross-references)

**hotelPandL services** import from siblings and `database`:
```python
# OLD (inside src/services/bank.py):
from database import get_supabase, TABLE_BANK_TRANSACTIONS
from utils import end_of_month

# NEW (inside src/pnl/services/bank.py):
from src.shared.database import get_supabase, TABLE_BANK_TRANSACTIONS
from src.pnl.utils import end_of_month
```

**instaHotel services** import from `src.database`:
```python
# OLD (inside src/services/media_queries.py):
from src.database import get_supabase, TABLE_MEDIA_LIBRARY

# NEW (inside src/insta/services/media_queries.py):
from src.shared.database import get_supabase, TABLE_MEDIA_LIBRARY
```

#### 3.5 Cross-page Navigation (instaHotel only)

Update `st.switch_page()` and `st.page_link()` paths:

```python
# OLD:
st.switch_page("pages/3_Image_Details.py")
st.switch_page("pages/4_Video_Details.py")
st.page_link("pages/5_AI_Lab.py", ...)
st.page_link("pages/6_AI_Captions.py", ...)
st.page_link("pages/7_AI_Enhancement.py", ...)

# NEW:
st.switch_page("pages/insta/image_details.py")
st.switch_page("pages/insta/video_details.py")
st.page_link("pages/insta/ai_lab.py", ...)
st.page_link("pages/insta/ai_captions.py", ...)
st.page_link("pages/insta/ai_enhancement.py", ...)
```

### Phase 4: Merge Config Files

#### 4.1 Merged `requirements.txt`

```
# Web Framework
streamlit>=1.33.0

# Database
supabase>=2.3.0

# Data Processing (P&L)
pandas>=2.1.0
numpy>=1.26.0
openpyxl>=3.1.0
xlrd>=2.0.1
python-dateutil>=2.8.2

# AI (InstaHotel)
anthropic>=0.80

# Google Drive API (InstaHotel)
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1

# Image processing (InstaHotel)
Pillow>=10.0.0
pillow-heif>=0.14.0

# Video processing (InstaHotel)
opencv-python-headless>=4.8.0

# Data models
pydantic>=2.0.0

# Image enhancement APIs (InstaHotel)
httpx>=0.28
replicate>=1.0

# Environment
python-dotenv>=1.0.0
```

#### 4.2 Merged `.env.example`

```bash
# Supabase (shared)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Anthropic (InstaHotel)
ANTHROPIC_API_KEY=sk-ant-your-key

# Google Drive (InstaHotel)
DRIVE_FOLDER_ID=12eYoajc5F8YKEwPmcNrgne8kmxGQG5wt

# Image Enhancement (InstaHotel)
STABILITY_API_KEY=your-stability-key
REPLICATE_API_TOKEN=your-replicate-token

# Google Sheets (P&L — optional)
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

#### 4.3 Merged `.streamlit/config.toml`

Use instaHotel's dark theme:
```toml
[theme]
primaryColor = "#FF6B35"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1A1D23"
textColor = "#FAFAFA"

[server]
headless = true
```

#### 4.4 Merged `.streamlit/secrets.toml.example`

```toml
SUPABASE_URL = "https://lngrockgpnwaizzyvwsk.supabase.co"
SUPABASE_KEY = "your-anon-key"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"

ANTHROPIC_API_KEY = "sk-ant-your-key"
STABILITY_API_KEY = "your-stability-key"
REPLICATE_API_TOKEN = "your-replicate-token"

DRIVE_FOLDER_ID = "12eYoajc5F8YKEwPmcNrgne8kmxGQG5wt"
GOOGLE_DRIVE_TOKEN = '{"token": "...", ...}'
```

#### 4.5 Merged `.gitignore`

Union of both, with additions for the new structure:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.venv/

# Environment
.env
*.env.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Credentials
*credentials*.json
*token*.json
*.pem
*.key

# Streamlit
.streamlit/secrets.toml

# Test
.pytest_cache/
.coverage
htmlcov/

# Jupyter
.ipynb_checkpoints/

# Temp
nul
supabase/.temp/
tmp_videos/

# Database backups
backups/

# Claude Code
.claude/

# Screenshots
screenshots/
test_screenshots/
```

### Phase 5: Merge the `ui.py` Components

The two `ui.py` files have conflicting function signatures:

**hotelPandL:**
```python
def sidebar_css():  # Injects CSS separator between 7th and 8th sidebar items
def page_title(text: str):  # Renders bold markdown
def compact_metrics(items: list):  # Renders metrics line
```

**instaHotel:**
```python
def sidebar_css():  # Injects thumbnail CSS + AI Lab indent
def page_title(icon_text: str, title: str):  # Renders heading + caption
```

**Resolution:** Merge into one `ui.py` with renamed functions where they differ:

```python
"""
Shared UI components for Hotel Noucentista dashboard.
"""
import streamlit as st


def sidebar_css():
    """Inject all custom CSS. Call once per page."""
    st.markdown("""
    <style>
    /* Tighter sidebar padding */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }
    /* Thumbnail grid (InstaHotel) */
    .thumb-container { ... }
    .thumb-badge { ... }
    .thumb-quality { ... }
    </style>
    """, unsafe_allow_html=True)


def pnl_page_title(text: str):
    """P&L page title — compact bold markdown."""
    sidebar_css()
    st.markdown(f"**{text}**")


def insta_page_title(icon_text: str, title: str):
    """InstaHotel page title — heading + caption."""
    st.markdown(f"## {icon_text}")
    st.caption(title)


def compact_metrics(items: list):
    """Render metrics as a single compact line."""
    parts = [f"{label}: {value}" for label, value in items]
    st.markdown(
        f'<p style="font-size:0.85rem; margin:0 0 0.5rem 0;">{" | ".join(parts)}</p>',
        unsafe_allow_html=True,
    )
```

**Impact:** All hotelPandL pages change `from components.ui import page_title` to `from app.components.ui import pnl_page_title as page_title` (or just replace calls). All instaHotel pages change `from app.components.ui import page_title` to `from app.components.ui import insta_page_title as page_title`.

Alternative (simpler): keep both `page_title` and call the 2-arg version `page_title_sub` or just overload based on argument count. But explicit renaming is safer.

### Phase 6: Merge `database.py`

Create `src/shared/database.py`:

```python
"""
Hotel Noucentista - Unified Database Connection
Supabase singleton shared by P&L and InstaHotel modules.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# Singleton
_supabase_client: Optional[Client] = None

# --- Table constants: P&L ---
TABLE_INVOICES = "invoices"
TABLE_BANK_TRANSACTIONS = "bank_transactions"
TABLE_MATCHES = "matches"
TABLE_DIM_GROUPS = "dim_groups"
TABLE_DIM_CATEGORIES = "dim_categories"
TABLE_BANK_POSITIONS = "bank_positions"
TABLE_PNL_BUDGETS = "pnl_budgets"
TABLE_PNL_SETTINGS = "pnl_settings"
TABLE_SUPPLIER_RULES = "supplier_rules"
TABLE_VAT_QUARTERLY = "vat_quarterly"

# --- Table constants: InstaHotel ---
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
    """Test database connection."""
    try:
        client = get_supabase()
        # Query a table that always exists
        client.table(TABLE_DIM_GROUPS).select("*").limit(1).execute()
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
```

### Phase 7: Test and Validate

1. **Run the app locally:**
   ```bash
   cd hotelNoucentista && streamlit run app/main.py --server.headless true
   ```

2. **Test each section:**
   - Navigate to every P&L page — verify data loads, forms work
   - Navigate to every InstaHotel page — verify media loads, thumbnails render
   - Test cross-page navigation (Gallery -> Image Details, AI Lab -> Captions)
   - Test sidebar grouping (P&L section, Instagram section)

3. **Common errors to watch for:**
   - `ModuleNotFoundError` — missed import rewrite
   - `st.set_page_config() can only be called once` — leftover call in a page
   - `st.switch_page()` path not found — path not updated
   - Widget key collisions between sections (unlikely, keys are already namespaced)

### Phase 8: Streamlit Cloud Deployment

1. **Update repository name** on GitHub if desired (or keep `instaHotel`)
2. **Update Streamlit Cloud app settings:**
   - Main file path: `app/main.py`
   - Python version: 3.11+
   - Secrets: merge all secrets from both apps
3. **Push `merge` branch to `main`**
4. **Verify** the deployed app works with both sections

---

## 5. Risks and Gotchas

### 5.1 `st.navigation()` requires Streamlit >= 1.36

The `st.navigation()` API with page grouping was introduced in Streamlit 1.36. The current `requirements.txt` pins `>=1.33.0`. **Update to `>=1.36.0`.**

If you want the latest features (like `st.Page` with `url_path` customization), use `>=1.37.0`.

### 5.2 sys.path Approach Must Be Consistent

With `st.navigation()`, all pages are run from the **main entry point's directory context**. The working directory will be the project root (where `streamlit run app/main.py` is called from) or the `app/` directory.

**Recommended:** Set `sys.path.insert(0, project_root)` once in `app/main.py` before `pg.run()`. Then all pages can use absolute imports like `from src.pnl.services.bank import ...` without any path manipulation.

```python
# In app/main.py, before pg.run():
import sys
from pathlib import Path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
```

### 5.3 Hardcoded Paths in Services

`google_drive.py` has a hardcoded path:
```python
CREDS_FILE = Path(r"c:\Users\michael\agents-lab\google_credentials.json")
TOKEN_FILE = _project_root / ".google_token_drive.json"
```

After restructure, `_project_root` will compute differently since the file moves from `src/services/` to `src/insta/services/`. Fix with:
```python
_project_root = Path(__file__).parent.parent.parent.parent  # One more .parent
```

Or better, compute from an anchor:
```python
_project_root = Path(__file__).resolve()
while not (_project_root / ".env").exists() and _project_root != _project_root.parent:
    _project_root = _project_root.parent
```

### 5.4 Sidebar CSS Assumptions

hotelPandL's `sidebar_css()` inserts CSS targeting `li:nth-child(8)` to add a separator. With `st.navigation()`, the sidebar structure changes — these CSS hacks will need to be removed or adapted to the new grouped navigation (which already visually separates sections).

### 5.5 `st.cache_data` Namespace

Both apps use `@st.cache_data`. Cache keys include the function's module path, so after moving files the cache will naturally reset. No conflict risk, but first load after migration will be slower.

### 5.6 Session State Key Collisions

Both apps use session state keys. Quick review:
- **hotelPandL:** Keys like `txn_created`, `confirm_delete_txn`, `pnl_expanded`, `cf_expanded`, `editing_group`, etc.
- **instaHotel:** Keys like `selected_media_id`, `selected_video_id`, `cap_result`, `enh_result`, `enh_session_costs`, etc.

**No collisions detected.** The namespacing is already sufficient.

### 5.7 Google Drive Token File Location

The token file `.google_token_drive.json` is at the project root. After merge, this stays in the same place. No change needed, but `google_drive.py`'s `_project_root` computation must be updated (see 5.3).

### 5.8 Database Connection Test

hotelPandL's `test_connection()` queries `dim_groups`. instaHotel's queries `media_library`. The unified version should use one that always exists. `dim_groups` is a good choice since it's a simple dimension table.

### 5.9 hotelPandL `load_dotenv` in Every File

hotelPandL calls `load_dotenv(_project_root / ".env")` in both page files and `database.py`. The pages do it as a safety measure. After migration, the unified `database.py` handles it. Remove `load_dotenv` from all page files.

### 5.10 Invoice Page Component Path Nesting

`app/components/invoice_page.py` has its own `sys.path.insert` to find `src`:
```python
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))
```
This must be removed and replaced with proper absolute imports.

---

## 6. Git Strategy

### Option A: Simple Copy (Recommended)

1. Work in the **instaHotel** repo on a `merge` branch
2. Copy hotelPandL files in manually (preserving content, not git history)
3. The hotelPandL repo stays as-is (archived / read-only)
4. Single commit: "Merge hotelPandL into unified app"

**Pros:** Clean, simple, no history complications.
**Cons:** Lose hotelPandL git history in the merged repo.

### Option B: Git Subtree (Not Recommended)

Could use `git subtree add --prefix=src/pnl ...` but:
- hotelPandL history includes many files that won't exist at the same paths
- Adds complexity for minimal benefit
- Both repos share the same Supabase project but have divergent structures

**Verdict:** Option A. The hotelPandL repo with full history is preserved separately.

---

## 7. Merged `requirements.txt` (Final)

```
# Hotel Noucentista — Combined Dependencies

# Web Framework
streamlit>=1.36.0

# Database
supabase>=2.3.0

# Data Processing (P&L)
pandas>=2.1.0
numpy>=1.26.0
openpyxl>=3.1.0
xlrd>=2.0.1
python-dateutil>=2.8.2

# AI (Instagram)
anthropic>=0.80

# Google Drive API (Instagram)
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1

# Image processing (Instagram)
Pillow>=10.0.0
pillow-heif>=0.14.0

# Video processing (Instagram)
opencv-python-headless>=4.8.0

# Data models
pydantic>=2.0.0

# Image enhancement APIs (Instagram)
httpx>=0.28
replicate>=1.0

# Environment
python-dotenv>=1.0.0
```

---

## 8. Estimated Effort

| Task | Effort | Notes |
|------|--------|-------|
| Phase 0: Preparation | 5 min | Branch, backup |
| Phase 1: Copy + reorganize files | 30 min | Mechanical file moves |
| Phase 2: New main.py with st.navigation | 15 min | Write from template above |
| Phase 3: Rewrite all imports | 60 min | ~30 files, mostly search-replace |
| Phase 4: Merge config files | 10 min | Merge .env, requirements, .gitignore |
| Phase 5: Merge ui.py | 10 min | Combine and rename functions |
| Phase 6: Merge database.py | 10 min | Combine table constants |
| Phase 7: Test and fix | 45 min | Run, find broken imports, fix |
| Phase 8: Deploy | 15 min | Update Cloud settings, push |
| **Total** | **~3 hours** | Conservative estimate |

The bulk of the work is the import rewriting (Phase 3) and testing (Phase 7). The rest is mechanical.

---

## 9. Import Rewrite Cheat Sheet

### Quick Reference: Old -> New Import Paths

**Database (both apps):**
```
from database import get_supabase      -> from src.shared.database import get_supabase
from src.database import get_supabase   -> from src.shared.database import get_supabase
```

**P&L Services:**
```
from services.X import Y               -> from src.pnl.services.X import Y
from utils import Z                     -> from src.pnl.utils import Z
from models import M                    -> from src.pnl.models import M
```

**InstaHotel Services:**
```
from src.services.X import Y           -> from src.insta.services.X import Y
from src.utils import Z                -> from src.insta.utils import Z
from src.models import M               -> from src.insta.models import M
from src.prompts.X import Y            -> from src.insta.prompts.X import Y
```

**Components:**
```
from components.ui import page_title    -> from app.components.ui import pnl_page_title
from app.components.ui import page_title -> from app.components.ui import insta_page_title
from components.invoice_page import Y   -> from app.components.invoice_page import Y
from app.components.media_grid import Y -> from app.components.media_grid import Y  (unchanged)
```

---

## 10. Post-Merge Cleanup

After the merge is stable:

1. **Archive hotelPandL repo** — mark as read-only on GitHub
2. **Update MEMORY.md** — point to new unified structure
3. **Update tasks/todo.md** — reflect new file paths
4. **Rename GitHub repo** if desired: `instaHotel` -> `hotelNoucentista`
5. **Consider** adding a simple home/hub page at the default navigation entry showing both sections with summary metrics (e.g., P&L YTD EBITDA + Instagram media count + upcoming calendar posts)
