"""
Database Method Patches for PostgreSQL Compatibility
====================================================

This module contains monkey patches for Frappe's PostgresDatabase class
to add automatic query transformation and error handling.
"""

import frappe
from frappe.database.postgres.database import PostgresDatabase
import psycopg2.errors

from .query_transformers import apply_all_query_transformations
from .db_functions import create_missing_functions


# ============================================================================
# Module State
# ============================================================================

# Store original methods
_original_sql = None
_original_commit = None
_original_rollback = None
_patches_applied = False


# ============================================================================
# Patched Database Methods
# ============================================================================

def patched_sql(self, query, values=(), *args, **kwargs):
    """
    Enhanced SQL method with:
    1. Automatic query transformation for PostgreSQL compatibility
    2. Transaction error handling with automatic rollback
    3. Detailed error logging

    This method is monkey-patched onto PostgresDatabase.sql to intercept
    all SQL queries and transform them before execution.

    Args:
        self: PostgresDatabase instance
        query: SQL query string
        values: Query parameter values
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments

    Returns:
        Query results from the database

    Raises:
        Exception: Re-raises any database errors after logging
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

    Args:
        self: PostgresDatabase instance

    Returns:
        Result from original commit method

    Raises:
        Exception: Re-raises any commit errors after logging
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

    Args:
        self: PostgresDatabase instance

    Returns:
        Result from original rollback method

    Note:
        Errors during rollback are silently caught to prevent
        cascading errors during error handling.
    """
    try:
        return _original_rollback(self)
    except Exception as e:
        # Don't log rollback failures during error handling
        # as this can cause cascading errors
        pass


# ============================================================================
# Patch Application Functions
# ============================================================================

def apply_postgres_fixes():
    """
    Apply PostgreSQL compatibility fixes.

    This function monkey-patches the PostgresDatabase class to add:
    - Automatic query transformation
    - Transaction error handling
    - Enhanced error logging

    This is called:
    - On app import (__init__.py)
    - After installation (hooks.py)
    - On session creation (hooks.py)
    - After migration (hooks.py)

    Returns:
        None
    """
    global _original_sql, _original_commit, _original_rollback, _patches_applied

    if _patches_applied:
        # Already applied, skip
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
    Called by Frappe hooks system on each user login.

    Args:
        login_manager: Frappe LoginManager instance

    Returns:
        None
    """
    apply_postgres_fixes()


def after_migrate():
    """
    Called after migration to ensure database functions exist.

    This ensures that:
    1. All patches are applied
    2. All database functions are created

    Returns:
        None
    """
    print("\nApplying post-migration PostgreSQL fixes...")
    apply_postgres_fixes()
    create_missing_functions()


def check_patches_status():
    """
    Check if PostgreSQL patches are currently applied.

    This is useful for debugging and verification.

    Returns:
        dict: Status information about patches

    Example:
        >>> from frappe_pg.postgres.database_patches import check_patches_status
        >>> check_patches_status()
        {
            'patches_applied': True,
            'sql_patched': True,
            'commit_patched': True,
            'rollback_patched': True
        }
    """
    return {
        'patches_applied': _patches_applied,
        'sql_patched': PostgresDatabase.sql == patched_sql if _patches_applied else False,
        'commit_patched': PostgresDatabase.commit == patched_commit if _patches_applied else False,
        'rollback_patched': PostgresDatabase.rollback == patched_rollback if _patches_applied else False
    }


# ============================================================================
# Module Initialization
# ============================================================================

# Apply patches when module is imported
# This ensures they're active even if hooks don't fire
try:
    apply_postgres_fixes()
except Exception as e:
    print(f"Warning: Could not apply PostgreSQL patches during module import: {e}")
