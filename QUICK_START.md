# Quick Start Guide - Frappe PostgreSQL Compatibility

## What Was Fixed

Your ERPNext installation with PostgreSQL was failing due to MySQL-specific SQL syntax. This app fixes:

### 1. **FORCE INDEX Error** ✓ FIXED
```
Error: syntax error at or near "INDEX"
LINE: ...FROM "tabGL Entry" FORCE INDEX ("posting_date")...
```
**Solution**: Automatically removes all `FORCE INDEX`, `USE INDEX`, and `IGNORE INDEX` clauses.

### 2. **IF() Function Error** ✓ FIXED
```
Error: function if(boolean, numeric, unknown) does not exist
HINT: No function matches the given name and argument types.
```
**Solution**: Automatically converts `IF(condition, true, false)` to `CASE WHEN condition THEN true ELSE false END`.

### 3. **Transaction Abort Error** ✓ FIXED
```
Error: current transaction is aborted, commands ignored until end of transaction block
```
**Solution**: Automatic transaction rollback and retry (up to 3 attempts).

### 4. **Missing Functions** ✓ FIXED
- Created `GROUP_CONCAT(text)` aggregate function
- Created `unix_timestamp()` function
- Created `timestampdiff()` function

## Verification

All functions are working correctly:

```bash
bench --site development.localhost execute frappe_pg.install_db_functions.verify
```

Result:
```
✓ All 3 tests passed!
  • GROUP_CONCAT: PASS
  • unix_timestamp: PASS
  • timestampdiff: PASS
```

## How It Works

The app intercepts SQL queries at the database layer and transforms them before execution:

```
Original Query (MySQL syntax):
  SELECT * FROM "tabGL Entry" FORCE INDEX ("posting_date")
  WHERE IF(amount > 0, amount, 0) > 100

Transformed Query (PostgreSQL syntax):
  SELECT * FROM "tabGL Entry"
  WHERE CASE WHEN amount > 0 THEN amount ELSE 0 END > 100
```

## Active Transformations

✓ **FORCE INDEX** → Removed (PostgreSQL doesn't need index hints)
✓ **IF(a, b, c)** → `CASE WHEN a THEN b ELSE c END`
✓ **IFNULL(a, b)** → `COALESCE(a, b)`
✓ **DATE_FORMAT(date, '%Y-%m-%d')** → `TO_CHAR(date, 'YYYY-MM-DD')`
✓ **Automatic rollback** on transaction errors

## Testing Your Modules

### Accounting Module

The Profit and Loss Statement and other reports should now work without the `FORCE INDEX` error.

### Buying Module

Reports like Sales Order Trends should work without the `IF()` function error.

## Monitoring

Check if patches are active:
```bash
tail -f ~/frappe-bench/sites/development.localhost/logs/frappe.log | grep "PostgreSQL"
```

You should see:
```
============================================================
Applying PostgreSQL Compatibility Patches for ERPNext
============================================================
✓ Query transformation patches applied
✓ Transaction error handling enabled
```

## Troubleshooting

If you still encounter errors:

1. **Clear cache and restart**:
   ```bash
   bench --site development.localhost clear-cache
   bench restart
   ```

2. **Check error logs**:
   ```bash
   grep "PostgreSQL" ~/frappe-bench/sites/development.localhost/logs/frappe.log | tail -20
   ```

3. **Reinstall functions**:
   ```bash
   bench --site development.localhost execute frappe_pg.install_db_functions.install
   ```

4. **View detailed errors**:
   ```bash
   tail -100 ~/frappe-bench/sites/development.localhost/logs/frappe.log
   ```

## What To Test

Try accessing these modules that were previously failing:

1. **Accounting**:
   - Navigate to: Accounting → Reports → Profit and Loss Statement
   - Should load without errors

2. **Buying**:
   - Navigate to: Buying → Reports → Sales Order Trends
   - Should work without `IF()` function errors

3. **Any Financial Reports**:
   - All reports using `FORCE INDEX` should now work
   - Reports using `IF()` conditions should work

## Expected Behavior

✓ No more "syntax error at or near INDEX"
✓ No more "function if() does not exist"
✓ No more "current transaction is aborted"
✓ All ERPNext modules should work normally

## Performance Notes

- PostgreSQL has its own query planner and doesn't need index hints
- Some queries may have different execution plans than MySQL
- If a query is slow, use PostgreSQL's `EXPLAIN ANALYZE` to optimize

## Getting Help

If you encounter new errors:

1. Check the error in the log files
2. The error log will show both:
   - Original query (MySQL syntax)
   - Transformed query (PostgreSQL syntax)
3. This helps identify what transformations might be missing

## Next Steps

Your ERPNext installation should now work correctly with PostgreSQL!

- All automatic transformations are active
- Database functions are installed and verified
- Transaction error handling is enabled
- Enhanced error logging is configured

You can now use ERPNext normally. The patches will automatically apply to all SQL queries in the background.
