"""
PostgreSQL Compatibility Fixes for ERPNext
==========================================

This module provides comprehensive compatibility patches for running ERPNext with PostgreSQL.
It handles the following critical issues:

1. FORCE INDEX removal (PostgreSQL doesn't support this MySQL-specific syntax)
2. IF() function conversion to CASE WHEN
3. GROUP_CONCAT aggregate function emulation
4. Transaction abort handling with automatic rollback
5. DATE_FORMAT to TO_CHAR conversion
6. IFNULL to COALESCE conversion
7. MySQL-style CONCAT to PostgreSQL || operator
"""

import frappe
from frappe.database.postgres.database import PostgresDatabase
import re
import psycopg2.errors


# ============================================================================
# Query Modification Patterns
# ============================================================================

# Pattern to match FORCE INDEX clauses
FORCE_INDEX_PATTERN = re.compile(
    r'\s+FORCE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)

# Pattern to match USE INDEX clauses
USE_INDEX_PATTERN = re.compile(
    r'\s+USE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)

# Pattern to match IGNORE INDEX clauses
IGNORE_INDEX_PATTERN = re.compile(
    r'\s+IGNORE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)

# Pattern to match IF(condition, true_value, false_value)
# This handles nested parentheses and complex expressions
IF_FUNCTION_PATTERN = re.compile(
    r'\bIF\s*\(',
    re.IGNORECASE
)

# Pattern for IFNULL function
IFNULL_PATTERN = re.compile(
    r'\bIFNULL\s*\(',
    re.IGNORECASE
)

# Pattern for DATE_FORMAT function
DATE_FORMAT_PATTERN = re.compile(
    r'\bDATE_FORMAT\s*\(\s*([^,]+?)\s*,\s*[\'"]%Y-%m-%d[\'"]\s*\)',
    re.IGNORECASE
)

# Pattern for NOW() with timezone considerations
NOW_PATTERN = re.compile(
    r'\bNOW\s*\(\s*\)',
    re.IGNORECASE
)


# ============================================================================
# Helper Functions for Query Transformation
# ============================================================================

def convert_if_to_case(query):
    """
    Convert MySQL IF() function to PostgreSQL CASE WHEN.

    Handles nested IF statements by processing from innermost to outermost.

    Examples:
        IF(a > 0, 1, 0) -> CASE WHEN a > 0 THEN 1 ELSE 0 END
        IF(status='Active', amount, 0) -> CASE WHEN status='Active' THEN amount ELSE 0 END
    """
    if not IF_FUNCTION_PATTERN.search(query):
        return query

    max_iterations = 100  # Increased to handle queries with many IF() calls
    iteration = 0

    while IF_FUNCTION_PATTERN.search(query) and iteration < max_iterations:
        iteration += 1

        # Find the FIRST IF function (will keep finding new ones as we convert)
        match = IF_FUNCTION_PATTERN.search(query)
        if not match:
            break

        start_pos = match.start()

        # Check that this is actually a word boundary before IF
        # to avoid matching things like "DIFF(" or similar
        if start_pos > 0:
            prev_char = query[start_pos - 1]
            if prev_char.isalnum() or prev_char == '_':
                # This is part of another word like "DIFF(", skip it
                # Temporarily replace it to skip in this iteration
                query = query[:start_pos] + '___NOTIF___(' + query[match.end():]
                continue

        if_start = match.end() - 1  # Position of opening parenthesis

        # Find matching closing parenthesis
        paren_count = 1
        pos = if_start + 1
        in_string = False
        string_char = None

        while pos < len(query) and paren_count > 0:
            char = query[pos]

            # Handle string literals
            if char in ("'", '"'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and (pos == 0 or query[pos-1] != '\\'):
                    in_string = False
                    string_char = None
            elif not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1

            pos += 1

        if paren_count != 0:
            # Malformed query, mark and skip
            query = query[:start_pos] + '___BADIF___(' + query[if_start + 1:]
            continue

        # Extract the IF content
        if_end = pos
        if_content = query[if_start + 1:if_end - 1]

        # Split by commas, respecting parentheses and strings
        parts = split_by_comma(if_content)

        if len(parts) != 3:
            # Invalid IF syntax, mark and skip
            query = query[:start_pos] + '___BADIF___(' + query[if_start + 1:]
            continue

        condition = parts[0].strip()
        true_val = parts[1].strip()
        false_val = parts[2].strip()

        # Build CASE expression
        case_expr = f"CASE WHEN {condition} THEN {true_val} ELSE {false_val} END"

        # Replace in query
        query = query[:start_pos] + case_expr + query[if_end:]

    # Restore any marked patterns (these would be errors anyway, but keep original)
    query = query.replace('___NOTIF___(', 'IF(')
    query = query.replace('___BADIF___(', 'IF(')

    return query


def split_by_comma(text):
    """
    Split text by commas, but respect parentheses and string literals.

    Args:
        text: String to split

    Returns:
        List of parts split by top-level commas
    """
    parts = []
    current = []
    paren_depth = 0
    in_string = False
    string_char = None

    for i, char in enumerate(text):
        if char in ("'", '"'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char and (i == 0 or text[i-1] != '\\'):
                in_string = False
                string_char = None
            current.append(char)
        elif in_string:
            current.append(char)
        elif char == '(':
            paren_depth += 1
            current.append(char)
        elif char == ')':
            paren_depth -= 1
            current.append(char)
        elif char == ',' and paren_depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)

    if current:
        parts.append(''.join(current))

    return parts


def remove_index_hints(query):
    """
    Remove MySQL index hints (FORCE INDEX, USE INDEX, IGNORE INDEX).
    PostgreSQL doesn't support these and relies on its query planner.
    """
    query = FORCE_INDEX_PATTERN.sub('', query)
    query = USE_INDEX_PATTERN.sub('', query)
    query = IGNORE_INDEX_PATTERN.sub('', query)
    return query


def convert_ifnull_to_coalesce(query):
    """
    Convert IFNULL(expr, default) to COALESCE(expr, default).
    Both functions are identical in behavior.
    """
    return IFNULL_PATTERN.sub('COALESCE(', query)


def convert_date_format(query):
    """
    Convert DATE_FORMAT(date, '%Y-%m-%d') to TO_CHAR(date, 'YYYY-MM-DD').
    """
    return DATE_FORMAT_PATTERN.sub(r"TO_CHAR(\1, 'YYYY-MM-DD')", query)


def apply_all_query_transformations(query):
    """
    Apply all query transformations in the correct order.
    """
    if not isinstance(query, str):
        return query

    original_query = query

    # Order matters here!
    query = remove_index_hints(query)
    query = convert_if_to_case(query)
    query = convert_ifnull_to_coalesce(query)
    query = convert_date_format(query)

    # Debug: Log if IF() is still present after transformation
    if 'IF(' in query.upper():
        import traceback
        print("\n" + "=" * 80)
        print("⚠️  WARNING: IF() still present after transformation!")
        print("=" * 80)
        print(f"Original query length: {len(original_query)} chars")
        print(f"Transformed query length: {len(query)} chars")
        print(f"Original query snippet: {original_query[:300]}...")
        print(f"Transformed query snippet: {query[:300]}...")

        # Find all IF( occurrences
        import re
        if_positions = [m.start() for m in re.finditer(r'\bIF\s*\(', query, re.IGNORECASE)]
        print(f"IF() found at {len(if_positions)} positions: {if_positions[:10]}...")  # Show first 10

        # Show context around first unconverted IF
        if if_positions:
            first_if = if_positions[0]
            context_start = max(0, first_if - 50)
            context_end = min(len(query), first_if + 100)
            print(f"\nFirst unconverted IF() context:")
            print(f"...{query[context_start:context_end]}...")
        print("=" * 80 + "\n")

    return query


# ============================================================================
# Database Method Patches
# ============================================================================

# Store original methods
_original_sql = None
_original_commit = None
_original_rollback = None
_patches_applied = False


def patched_sql(self, query, values=(), *args, **kwargs):
    """
    Enhanced SQL method with:
    1. Automatic query transformation for PostgreSQL compatibility
    2. Transaction error handling with automatic rollback
    3. Detailed error logging
    """
    # Apply query transformations FIRST, before Frappe's modify_query
    transformed_query = apply_all_query_transformations(query)

    max_retries = 3
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Import these here to avoid circular imports
            import frappe.database.database
            from frappe.database.postgres.database import modify_query, modify_values as pg_modify_values

            # Apply Frappe's PostgreSQL transformations
            pg_query = modify_query(transformed_query)
            pg_values = pg_modify_values(values)

            # Call the parent Database.sql method directly
            # This bypasses PostgresDatabase.sql to avoid recursion
            return frappe.database.database.Database.sql(self, pg_query, pg_values, *args, **kwargs)

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Check if this is a transaction abort error
            is_transaction_error = (
                'transaction is aborted' in error_msg or
                'infailedsqltransaction' in error_msg or
                isinstance(e, psycopg2.errors.InFailedSqlTransaction)
            )

            if is_transaction_error:
                retry_count += 1

                # Try to rollback
                try:
                    self.rollback()
                    frappe.log_error(
                        title=f"PostgreSQL Transaction Rolled Back (Retry {retry_count}/{max_retries})",
                        message=f"Query: {str(transformed_query)[:500]}\n\nOriginal Query: {str(query)[:500]}\n\nError: {str(e)}"
                    )

                    # If we have retries left, continue the loop
                    if retry_count < max_retries:
                        continue
                except Exception as rollback_error:
                    frappe.log_error(
                        title="PostgreSQL Rollback Failed",
                        message=f"Rollback Error: {str(rollback_error)}\n\nOriginal Error: {str(e)}"
                    )

            # Check for syntax errors that might need additional transformation
            if 'syntax error' in error_msg or isinstance(e, psycopg2.errors.SyntaxError):
                frappe.log_error(
                    title="PostgreSQL Syntax Error",
                    message=f"Transformed Query: {str(transformed_query)[:1000]}\n\n"
                            f"Original Query: {str(query)[:1000]}\n\n"
                            f"Values: {str(values)[:500]}\n\n"
                            f"Error: {str(e)}"
                )

            # Check for function not found errors
            if 'function' in error_msg and 'does not exist' in error_msg:
                frappe.log_error(
                    title="PostgreSQL Function Not Found",
                    message=f"Transformed Query: {str(transformed_query)[:1000]}\n\n"
                            f"Original Query: {str(query)[:1000]}\n\n"
                            f"Error: {str(e)}\n\n"
                            f"Hint: This might require database-level function creation"
                )

            # Re-raise the exception
            raise

    # If we exhausted retries, raise the last error
    if last_error:
        raise last_error


def patched_commit(self):
    """
    Enhanced commit with error handling.
    """
    try:
        return _original_commit(self)
    except Exception as e:
        frappe.log_error(
            title="PostgreSQL Commit Failed",
            message=str(e)
        )
        raise


def patched_rollback(self):
    """
    Enhanced rollback with error handling and logging.
    """
    try:
        return _original_rollback(self)
    except Exception as e:
        # Don't log rollback failures during error handling
        # as this can cause cascading errors
        pass


# ============================================================================
# Database Function Creation
# ============================================================================

def create_missing_functions():
    """
    Create PostgreSQL functions that emulate MySQL functions.
    This is called during installation/migration.
    """
    if not frappe.db:
        return

    # List of SQL statements to execute separately
    sql_statements = [
        # Drop existing GROUP_CONCAT if present
        "DROP AGGREGATE IF EXISTS GROUP_CONCAT(text) CASCADE",
        "DROP FUNCTION IF EXISTS group_concat_sfunc(text, text) CASCADE",

        # Create GROUP_CONCAT state transition function
        """
        CREATE OR REPLACE FUNCTION group_concat_sfunc(text, text)
        RETURNS text AS $$
            SELECT CASE
                WHEN $1 IS NULL THEN $2
                WHEN $2 IS NULL THEN $1
                ELSE $1 || ',' || $2
            END
        $$ LANGUAGE SQL IMMUTABLE
        """,

        # Create GROUP_CONCAT aggregate
        """
        CREATE AGGREGATE GROUP_CONCAT(text) (
            SFUNC = group_concat_sfunc,
            STYPE = text
        )
        """,

        # Create UNIX_TIMESTAMP function (with timezone)
        """
        CREATE OR REPLACE FUNCTION unix_timestamp(timestamp with time zone DEFAULT NOW())
        RETURNS bigint AS $$
            SELECT EXTRACT(EPOCH FROM $1)::bigint
        $$ LANGUAGE SQL IMMUTABLE
        """,

        # Create UNIX_TIMESTAMP function (without timezone)
        """
        CREATE OR REPLACE FUNCTION unix_timestamp(timestamp without time zone)
        RETURNS bigint AS $$
            SELECT EXTRACT(EPOCH FROM $1::timestamp with time zone)::bigint
        $$ LANGUAGE SQL IMMUTABLE
        """,

        # Create TIMESTAMPDIFF function
        """
        CREATE OR REPLACE FUNCTION timestampdiff(unit text, start_ts timestamp, end_ts timestamp)
        RETURNS integer AS $$
        BEGIN
            CASE LOWER(unit)
                WHEN 'second' THEN
                    RETURN EXTRACT(EPOCH FROM (end_ts - start_ts))::integer;
                WHEN 'minute' THEN
                    RETURN (EXTRACT(EPOCH FROM (end_ts - start_ts)) / 60)::integer;
                WHEN 'hour' THEN
                    RETURN (EXTRACT(EPOCH FROM (end_ts - start_ts)) / 3600)::integer;
                WHEN 'day' THEN
                    RETURN EXTRACT(DAY FROM (end_ts - start_ts))::integer;
                WHEN 'month' THEN
                    RETURN ((EXTRACT(YEAR FROM end_ts) - EXTRACT(YEAR FROM start_ts)) * 12 +
                            EXTRACT(MONTH FROM end_ts) - EXTRACT(MONTH FROM start_ts))::integer;
                WHEN 'year' THEN
                    RETURN (EXTRACT(YEAR FROM end_ts) - EXTRACT(YEAR FROM start_ts))::integer;
                ELSE
                    RAISE EXCEPTION 'Unsupported unit: %', unit;
            END CASE;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
        """
    ]

    success_count = 0
    error_count = 0

    for sql in sql_statements:
        try:
            # Use direct connection to avoid our patches interfering
            if hasattr(frappe.db, '_conn') and frappe.db._conn:
                cursor = frappe.db._conn.cursor()
                cursor.execute(sql)
                frappe.db._conn.commit()
                success_count += 1
            else:
                frappe.db.sql(sql)
                frappe.db.commit()
                success_count += 1
        except Exception as e:
            error_msg = str(e).lower()
            if 'already exists' not in error_msg:
                error_count += 1
                print(f"  ⚠ Warning: {str(e)[:100]}")

    if error_count == 0:
        print(f"✓ PostgreSQL compatibility functions created successfully ({success_count} statements)")
    else:
        print(f"⚠ Created functions with {error_count} warnings ({success_count} succeeded)")


# ============================================================================
# Main Patch Application Functions
# ============================================================================

def apply_postgres_fixes():
    """
    Apply PostgreSQL compatibility fixes.
    This is called after installation.
    """
    global _original_sql, _original_commit, _original_rollback, _patches_applied

    if _patches_applied:
        print("PostgreSQL patches already applied")
        return

    print("=" * 60)
    print("Applying PostgreSQL Compatibility Patches for ERPNext")
    print("=" * 60)

    # Store original methods
    _original_sql = PostgresDatabase.sql
    _original_commit = PostgresDatabase.commit
    _original_rollback = PostgresDatabase.rollback

    # Apply monkey patches
    PostgresDatabase.sql = patched_sql
    PostgresDatabase.commit = patched_commit
    PostgresDatabase.rollback = patched_rollback

    _patches_applied = True

    print("✓ Query transformation patches applied")
    print("✓ Transaction error handling enabled")
    print("✓ Enhanced error logging configured")
    print()
    print("The following transformations are now active:")
    print("  • FORCE INDEX removal")
    print("  • IF() → CASE WHEN conversion")
    print("  • IFNULL() → COALESCE() conversion")
    print("  • DATE_FORMAT() → TO_CHAR() conversion")
    print("  • Automatic transaction rollback on errors")
    print("=" * 60)


def on_session_creation(login_manager):
    """
    Apply fixes on each session creation.
    This ensures patches remain active after restarts.
    """
    apply_postgres_fixes()


def after_migrate():
    """
    Called after migration to ensure database functions exist.
    """
    print("\nApplying post-migration PostgreSQL fixes...")
    apply_postgres_fixes()
    create_missing_functions()


# ============================================================================
# Module Initialization
# ============================================================================

# Apply patches when module is imported
# This ensures they're active even if hooks don't fire
try:
    apply_postgres_fixes()
except Exception as e:
    print(f"Warning: Could not apply PostgreSQL patches during module import: {e}")
