# Frappe PostgreSQL - File Structure

## Directory Organization

```
frappe_pg/
├── frappe_pg/                     # Main application package
│   ├── __init__.py                # App initialization, auto-applies patches
│   ├── hooks.py                   # Frappe hooks configuration
│   │
│   ├── postgres/                  # Core PostgreSQL compatibility
│   │   ├── __init__.py
│   │   ├── database_patches.py    # Monkey patches for PostgresDatabase class
│   │   ├── query_transformers.py  # SQL transformation functions
│   │   └── db_functions.py        # PostgreSQL function creation/management
│   │
│   ├── utils/                     # Utility modules
│   │   ├── __init__.py
│   │   └── regex_patterns.py      # SQL pattern matching (IF, FORCE INDEX, etc.)
│   │
│   ├── patches/                   # Versioned patches
│   │   ├── __init__.py
│   │   ├── v1/                    # Version 1 patches
│   │   │   ├── __init__.py
│   │   │   ├── apply_postgres_compatibility.py  # Main compatibility patch
│   │   │   └── fix_erpnext_trends.py           # ERPNext GROUP BY fixes
│   │   ├── erpnext_trends_fix.py  # Legacy (kept for backwards compat)
│   │   └── postgres_fix.py        # Legacy (kept for backwards compat)
│   │
│   ├── api/                       # API endpoints
│   │   ├── __init__.py
│   │   └── patches.py             # Patch management API
│   │
│   ├── config/                    # Frappe configuration
│   │   └── __init__.py
│   │
│   ├── docs/                      # Documentation
│   │   ├── README.md
│   │   ├── installation.md
│   │   ├── architecture.md
│   │   └── troubleshooting.md
│   │
│   ├── templates/                 # Frappe templates
│   │   ├── __init__.py
│   │   └── pages/
│   │
│   └── public/                    # Static assets
│       ├── css/
│       └── js/
│
├── STRUCTURE.md                   # This file
├── README.md                      # Main README
├── license.txt                    # MIT License
└── pyproject.toml                 # Python project configuration
```

## Module Responsibilities

### Core Modules (`postgres/`)

#### `database_patches.py`
- Monkey-patches `PostgresDatabase.sql()` method
- Applies query transformations before execution
- Handles transaction errors with auto-rollback
- Provides retry mechanism (up to 3 attempts)
- Functions:
  - `patched_sql()`: Enhanced SQL execution
  - `apply_postgres_fixes()`: Apply all patches
  - `check_patches_status()`: Verify patch status

#### `query_transformers.py`
- Contains all SQL transformation logic
- Functions:
  - `convert_if_to_case()`: IF() → CASE WHEN (handles 100+ nested calls)
  - `remove_index_hints()`: Remove FORCE/USE/IGNORE INDEX
  - `convert_ifnull_to_coalesce()`: IFNULL() → COALESCE()
  - `convert_date_format()`: DATE_FORMAT() → TO_CHAR()
  - `apply_all_query_transformations()`: Main transformation pipeline
  - `split_by_comma()`: Helper for parsing function arguments

#### `db_functions.py`
- Creates PostgreSQL compatibility functions
- Functions:
  - `create_missing_functions()`: Install all functions
  - `verify_db_functions()`: Test function installation
  - `drop_all_functions()`: Clean uninstallation
- Database functions created:
  - `GROUP_CONCAT(text)`: String aggregation
  - `unix_timestamp()`: Unix timestamp conversion
  - `timestampdiff()`: Time difference calculation

### Utility Modules (`utils/`)

#### `regex_patterns.py`
- Compiled regex patterns for SQL matching
- Patterns:
  - `FORCE_INDEX_PATTERN`, `USE_INDEX_PATTERN`, `IGNORE_INDEX_PATTERN`
  - `IF_FUNCTION_PATTERN`, `IFNULL_PATTERN`
  - `DATE_FORMAT_PATTERN`, `NOW_PATTERN`
- Helper functions for pattern matching

### Patches (`patches/v1/`)

#### `apply_postgres_compatibility.py`
- Frappe patch: applies all PostgreSQL fixes
- Called during migration
- Functions:
  - `execute()`: Run the patch
  - `validate()`: Verify patch success

#### `fix_erpnext_trends.py`
- Frappe patch: fixes ERPNext trends.py GROUP BY issues
- Patches `based_wise_columns_query()` function
- Fixes:
  - Item reports: adds `item_name`
  - Customer reports: adds `customer_name`, `territory`
  - Supplier reports: adds `supplier_name`
  - Project reports: adds `project_name`
  - Universal: adds `default_currency` to all reports

### API Module (`api/`)

#### `patches.py`
- Whitelisted API endpoints for patch management
- Endpoints:
  - `check_patches_status()`: Get patch status
  - `verify_patches()`: Run verification tests
  - `reinstall_patches()`: Reinstall all patches
  - `get_patch_info()`: Get patch documentation

## Hooks Configuration

**File**: `hooks.py`

```python
after_install = "frappe_pg.postgres.database_patches.apply_postgres_fixes"
after_migrate = "frappe_pg.postgres.database_patches.after_migrate"
on_session_creation = "frappe_pg.postgres.database_patches.on_session_creation"
```

These hooks ensure patches are applied:
1. **After installation**: Initial patch application
2. **After migration**: Reapply patches + create DB functions
3. **On session creation**: Keep patches active after restarts

## Initialization Flow

1. **App Import** (`__init__.py`):
   ```python
   from frappe_pg.postgres.database_patches import apply_postgres_fixes
   from frappe_pg.patches.v1.fix_erpnext_trends import apply_trends_patch

   apply_postgres_fixes()  # Apply database patches
   apply_trends_patch()    # Apply ERPNext trends fix
   ```

2. **Database Patches Applied**:
   - `PostgresDatabase.sql` → `patched_sql`
   - `PostgresDatabase.commit` → `patched_commit`
   - `PostgresDatabase.rollback` → `patched_rollback`

3. **Query Execution Flow**:
   ```
   User Query
       ↓
   patched_sql()
       ↓
   apply_all_query_transformations()
       ├→ remove_index_hints()
       ├→ convert_if_to_case()
       ├→ convert_ifnull_to_coalesce()
       └→ convert_date_format()
       ↓
   Frappe's modify_query()
       ↓
   PostgreSQL Database
   ```

## Legacy Files

These files are kept for backwards compatibility but not used in new structure:

- `patches/postgres_fix.py` - Original monolithic patch file
- `patches/erpnext_trends_fix.py` - Original trends fix

**Migration**: Old imports still work but point to new modules internally.

## Testing

Run verification tests:
```bash
bench --site site1.local console

# Check patch status
>>> from frappe_pg.api import check_patches_status, verify_patches
>>> check_patches_status()
>>> verify_patches()

# Test individual components
>>> from frappe_pg.postgres.db_functions import verify_db_functions
>>> verify_db_functions()
```

## Version Information

- **Current Version**: 1.0.0
- **Patch Version**: v1
- **License**: MIT
