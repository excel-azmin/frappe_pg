# Frappe PostgreSQL Compatibility App

This Frappe app provides comprehensive PostgreSQL compatibility patches for running ERPNext with PostgreSQL database instead of MariaDB/MySQL.

## Problem Statement

ERPNext and Frappe were originally designed for MariaDB/MySQL and use several MySQL-specific SQL features that are not compatible with PostgreSQL:

1. **FORCE INDEX / USE INDEX / IGNORE INDEX** - PostgreSQL doesn't support index hints
2. **IF() function** - PostgreSQL uses CASE WHEN instead
3. **IFNULL() function** - PostgreSQL uses COALESCE()
4. **DATE_FORMAT()** - PostgreSQL uses TO_CHAR()
5. **GROUP_CONCAT()** - PostgreSQL uses STRING_AGG() or custom aggregates
6. **Transaction abort cascading** - PostgreSQL requires explicit rollback after errors

## Features

This app provides:

### 1. Automatic Query Transformation
- Removes `FORCE INDEX`, `USE INDEX`, `IGNORE INDEX` clauses
- Converts `IF(condition, true, false)` to `CASE WHEN condition THEN true ELSE false END`
- Converts `IFNULL(expr, default)` to `COALESCE(expr, default)`
- Converts `DATE_FORMAT(date, '%Y-%m-%d')` to `TO_CHAR(date, 'YYYY-MM-DD')`
- Handles nested expressions correctly

### 2. Transaction Error Handling
- Automatic rollback on transaction abort errors
- Retry mechanism for transient failures
- Detailed error logging for debugging

### 3. Database Function Emulation
- `GROUP_CONCAT(text)` aggregate function
- `unix_timestamp()` function for epoch conversion
- `timestampdiff()` function for time calculations

### 4. Enhanced Error Logging
- Logs syntax errors with original and transformed queries
- Tracks function not found errors
- Detailed transaction rollback logging

## Configuration

### PostgreSQL Database Setup

Before installing the app, ensure your Frappe bench is configured for PostgreSQL.

#### common_site_config.json

Add the following configuration to `~/frappe-bench/sites/common_site_config.json`:

```json
{
  "background_workers": 1,
  "db_host": "postgresql",
  "db_type": "postgres",
  "db_port": 5432,
  "postgres": {
    "isolation_level": "READ COMMITTED",
    "auto_commit": true
  },
  "developer_mode": 1,
  "file_watcher_port": 6787,
  "frappe_user": "frappe",
  "gunicorn_workers": 41,
  "live_reload": true,
  "rebase_on_pull": false,
  "redis_cache": "redis://redis-cache:6379",
  "redis_queue": "redis://redis-queue:6379",
  "redis_socketio": "redis://redis-queue:6379",
  "auto_commit_on_many_writes": 1,
  "restart_supervisor_on_update": false,
  "restart_systemd_on_update": false,
  "serve_default_site": true,
  "shallow_clone": true,
  "socketio_port": 9000,
  "use_redis_auth": false,
  "webserver_port": 8000,
  "root_login": "postgres",
  "root_password": "your_postgres_password"
}
```

**Key PostgreSQL-specific fields:**
- `db_type`: Must be set to `"postgres"`
- `db_host`: PostgreSQL server hostname
- `db_port`: PostgreSQL port (default: 5432)
- `postgres.isolation_level`: Transaction isolation level (recommended: `"READ COMMITTED"`)
- `postgres.auto_commit`: Enable auto-commit for PostgreSQL
- `auto_commit_on_many_writes`: Required for bulk operations
- `root_login`: PostgreSQL superuser username (default: `"postgres"`)
- `root_password`: PostgreSQL superuser password

#### site_config.json

For each site, configure `~/frappe-bench/sites/your-site-name/site_config.json`:

```json
{
  "db_name": "_54cc49b9a1aab38b",
  "db_password": "c6aU3eSCuH483KmZ",
  "db_type": "postgres",
  "db_port": 5432,
  "auto_commit_on_many_writes": 1,
  "limits": {
    "max_database_connections": 5
  },
  "developer_mode": 1,
  "postgres_compatibility_mode": 1,
  "ignore_mandatory_on_cancel": 1,
  "disable_website_cache": 1,
  "log_level": "DEBUG"
}
```

**Key site-level PostgreSQL fields:**
- `db_type`: Must be set to `"postgres"`
- `db_name`: PostgreSQL database name for this site
- `db_password`: Database user password
- `db_port`: PostgreSQL port (should match common_site_config)
- `auto_commit_on_many_writes`: Required for bulk operations
- `limits.max_database_connections`: Connection pool limit (adjust based on your needs)
- `postgres_compatibility_mode`: Enable PostgreSQL compatibility features
- `log_level`: Set to `"DEBUG"` for detailed error logging during setup

## Installation

### 1. Install the app

```bash
cd ~/frappe-bench/apps
bench get-app https://github.com/excel-azmin/frappe_pg.git
```

Or if you already have it locally:

```bash
cd ~/frappe-bench
bench --site your-site-name install-app frappe_pg
```

### 2. Create database functions

```bash
bench --site your-site-name execute frappe_pg.install_db_functions.install
```

### 3. Verify installation

```bash
bench --site your-site-name execute frappe_pg.install_db_functions.verify
```

### 4. Restart bench

```bash
bench restart
```

## Usage

Once installed, the app works automatically in the background. No configuration is needed.

### Checking if patches are active

The patches are applied automatically when:
- The app is installed (`after_install` hook)
- After migration (`after_migrate` hook)
- On each user session creation (`on_session_creation` hook)
- When the module is imported (boot time)

You should see this message in your logs when the patches are applied:

```
============================================================
Applying PostgreSQL Compatibility Patches for ERPNext
============================================================
✓ Query transformation patches applied
✓ Transaction error handling enabled
✓ Enhanced error logging configured

The following transformations are now active:
  • FORCE INDEX removal
  • IF() → CASE WHEN conversion
  • IFNULL() → COALESCE() conversion
  • DATE_FORMAT() → TO_CHAR() conversion
  • Automatic transaction rollback on errors
============================================================
```

## Troubleshooting

### Error: "current transaction is aborted"

This error means PostgreSQL encountered an error and aborted the transaction. The app should automatically handle this, but if you still see it:

1. Clear your cache:
   ```bash
   bench --site your-site-name clear-cache
   ```

2. Restart bench:
   ```bash
   bench restart
   ```

3. Check if patches are active by looking at logs:
   ```bash
   tail -f ~/frappe-bench/sites/your-site-name/logs/frappe.log
   ```

### Error: "syntax error at or near INDEX"

This means a `FORCE INDEX` clause wasn't removed. Check:

1. Ensure the app is installed:
   ```bash
   bench --site your-site-name list-apps
   ```

2. Reinstall database functions:
   ```bash
   bench --site your-site-name execute frappe_pg.install_db_functions.install
   ```

3. Check error logs for the exact query:
   ```bash
   grep "PostgreSQL Syntax Error" ~/frappe-bench/sites/your-site-name/logs/frappe.log
   ```

### Error: "function does not exist" with IF()

This means an `IF()` function wasn't converted to `CASE WHEN`.

1. Verify the transformation is active (check logs for the banner above)

2. Look at the error log for details:
   ```bash
   bench --site your-site-name mariadb
   # In PostgreSQL console:
   SELECT creation, error FROM "tabError Log" ORDER BY creation DESC LIMIT 5;
   ```

3. Report the issue with the query that failed

### Error: "function group_concat does not exist"

The database functions weren't created. Install them:

```bash
bench --site your-site-name execute frappe_pg.install_db_functions.install
```

## Technical Details

### Architecture

The app uses monkey-patching to intercept SQL queries at the Frappe database layer:

```
User Request
    ↓
Frappe Controller
    ↓
Query Builder
    ↓
frappe_pg patches (our transformations)
    ↓
PostgresDatabase.sql (Frappe's PostgreSQL layer)
    ↓
PostgreSQL Database
```

### Query Transformation Pipeline

1. **Remove Index Hints**: Strip `FORCE INDEX`, `USE INDEX`, `IGNORE INDEX`
2. **Convert IF()**: Transform to `CASE WHEN`
3. **Convert IFNULL()**: Transform to `COALESCE()`
4. **Convert DATE_FORMAT()**: Transform to `TO_CHAR()`
5. **Apply Frappe's modify_query()**: Frappe's built-in transformations
6. **Execute Query**: Send to PostgreSQL

### Transaction Error Handling

```python
try:
    execute_query()
except InFailedSqlTransaction:
    rollback()
    retry_query()  # Up to 3 times
```

## Known Limitations

1. **Performance**: Some queries may be slower on PostgreSQL due to different query planning
2. **Index Hints**: Removed entirely - PostgreSQL uses its own planner
3. **Nested IF()**: Limited to 20 levels of nesting to prevent infinite loops
4. **DATE_FORMAT**: Only `%Y-%m-%d` format is currently transformed

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/frappe_pg
pre-commit install
```

To add support for additional MySQL functions:

1. Add a regex pattern in `postgres_fix.py`
2. Add a transformation function
3. Add it to `apply_all_query_transformations()`
4. Test thoroughly!

## Error Reporting

If you encounter errors:

1. Check `~/frappe-bench/sites/your-site-name/logs/frappe.log`
2. Look for "PostgreSQL Syntax Error" or "PostgreSQL Function Not Found"
3. The error will include both original and transformed queries
4. Report issues with the full error log

## Files Structure

```
frappe_pg/
├── frappe_pg/
│   ├── postgres/                  # Core PostgreSQL compatibility
│   │   ├── database_patches.py    # Database method monkey patches
│   │   ├── query_transformers.py  # SQL transformation functions
│   │   └── db_functions.py        # PostgreSQL function creation
│   ├── utils/                     # Utility modules
│   │   └── regex_patterns.py      # SQL pattern matching
│   ├── patches/                   # Versioned patches
│   │   ├── v1/
│   │   │   ├── apply_postgres_compatibility.py
│   │   │   └── fix_erpnext_trends.py
│   │   ├── erpnext_trends_fix.py  # Legacy (backwards compat)
│   │   └── postgres_fix.py        # Legacy (backwards compat)
│   ├── api/                       # API endpoints
│   │   └── patches.py             # Patch management API
│   ├── docs/                      # Documentation
│   ├── hooks.py                   # Frappe hooks configuration
│   └── __init__.py                # App initialization
├── STRUCTURE.md                   # Detailed structure documentation
└── README.md                      # This file
```

See [STRUCTURE.md](STRUCTURE.md) for detailed documentation of the codebase organization.

## License

MIT

## Credits

Developed by Shaid Azmin (azmin@excelbd.com) for Excel Technologies Ltd.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review error logs carefully
- Report bugs with full error details and query logs
