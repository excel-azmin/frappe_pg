"""
Patch: Apply PostgreSQL Compatibility Fixes
===========================================

This patch applies all PostgreSQL compatibility transformations:
- Query transformations (IF, FORCE INDEX, etc.)
- Database method patches
- PostgreSQL function creation

Date: 2025-12-09
Version: 1.0.0
"""

import frappe
from frappe_pg.postgres.database_patches import apply_postgres_fixes
from frappe_pg.postgres.db_functions import create_missing_functions


def execute():
    """
    Execute the PostgreSQL compatibility patch.

    This function is called by Frappe's patch system during migration.

    Steps:
    1. Apply monkey patches to PostgresDatabase class
    2. Create PostgreSQL compatibility functions
    3. Verify installation

    Returns:
        None
    """
    print("\n" + "=" * 70)
    print("PATCH: Applying PostgreSQL Compatibility for ERPNext")
    print("=" * 70)

    # Step 1: Apply database patches
    print("\n[1/2] Applying database method patches...")
    try:
        apply_postgres_fixes()
        print(" Database patches applied successfully")
    except Exception as e:
        print(f" Error applying database patches: {e}")
        raise

    # Step 2: Create database functions
    print("\n[2/2] Creating PostgreSQL compatibility functions...")
    try:
        create_missing_functions()
        print(" Database functions created successfully")
    except Exception as e:
        print(f" Error creating database functions: {e}")
        raise

    print("\n" + "=" * 70)
    print(" PostgreSQL Compatibility Patch Completed Successfully")
    print("=" * 70)
    print("\nThe following features are now active:")
    print("  • Automatic query transformation (IF, FORCE INDEX, etc.)")
    print("  • Transaction error handling with auto-rollback")
    print("  • PostgreSQL functions (GROUP_CONCAT, unix_timestamp, etc.)")
    print("\n")


def validate():
    """
    Validate that the patch was applied successfully.

    This function can be called to verify the patch installation.

    Returns:
        bool: True if patch is working, False otherwise
    """
    from frappe_pg.postgres.database_patches import check_patches_status
    from frappe_pg.postgres.db_functions import verify_db_functions

    status = check_patches_status()
    if not status['patches_applied']:
        return False

    return verify_db_functions()
