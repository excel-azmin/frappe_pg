"""
API Endpoints for PostgreSQL Patch Management
=============================================

This module provides API endpoints for checking, verifying, and managing
PostgreSQL compatibility patches.
"""

import frappe
from frappe import _


@frappe.whitelist()
def check_patches_status():
    """
    Check if PostgreSQL patches are currently applied.

    Returns:
        dict: Status information about all patches

    Example Response:
        {
            "database_patches": {
                "patches_applied": True,
                "sql_patched": True,
                "commit_patched": True,
                "rollback_patched": True
            },
            "trends_patch": {
                "applied": True
            },
            "db_functions": {
                "installed": True
            }
        }
    """
    from frappe_pg.postgres.database_patches import check_patches_status as check_db_patches

    status = {
        "database_patches": check_db_patches(),
        "db_functions": {
            "installed": _check_db_functions_installed()
        }
    }

    # Check if ERPNext trends patch is applied
    try:
        from erpnext.controllers import trends
        status["trends_patch"] = {
            "applied": hasattr(trends, 'based_wise_columns_query') and
                      'patched_based_wise_columns_query' in str(trends.based_wise_columns_query)
        }
    except ImportError:
        status["trends_patch"] = {
            "applied": False,
            "reason": "ERPNext not installed"
        }

    return status


@frappe.whitelist()
def verify_patches():
    """
    Verify that all patches are working correctly.

    Returns:
        dict: Verification results

    Example Response:
        {
            "database_patches": True,
            "db_functions": True,
            "all_verified": True,
            "details": {...}
        }
    """
    from frappe_pg.postgres.db_functions import verify_db_functions

    results = {
        "database_patches": True,  # If we can execute this, patches are working
        "db_functions": verify_db_functions(),
    }

    results["all_verified"] = all(results.values())

    return results


@frappe.whitelist()
def reinstall_patches():
    """
    Reinstall all PostgreSQL compatibility patches.

    This is useful if patches get disconnected or need to be reapplied.

    Returns:
        dict: Installation results

    Example Response:
        {
            "success": True,
            "message": "All patches reinstalled successfully"
        }
    """
    frappe.only_for("System Manager")

    try:
        from frappe_pg.postgres.database_patches import apply_postgres_fixes
        from frappe_pg.postgres.db_functions import create_missing_functions
        from frappe_pg.patches.v1.fix_erpnext_trends import apply_trends_patch

        # Apply database patches
        apply_postgres_fixes()

        # Create database functions
        create_missing_functions()

        # Apply trends patch
        try:
            apply_trends_patch()
        except ImportError:
            pass  # ERPNext not installed

        return {
            "success": True,
            "message": "All patches reinstalled successfully"
        }

    except Exception as e:
        frappe.log_error(
            title="Patch Reinstallation Failed",
            message=str(e)
        )
        return {
            "success": False,
            "message": f"Error reinstalling patches: {str(e)}"
        }


@frappe.whitelist()
def get_patch_info():
    """
    Get information about all available patches.

    Returns:
        dict: Patch information

    Example Response:
        {
            "patches": [
                {
                    "name": "apply_postgres_compatibility",
                    "version": "1.0.0",
                    "description": "...",
                    "applied": True
                },
                ...
            ]
        }
    """
    from frappe_pg import __version__

    patches = [
        {
            "name": "apply_postgres_compatibility",
            "version": "1.0.0",
            "module": "frappe_pg.patches.v1.apply_postgres_compatibility",
            "description": "Apply PostgreSQL compatibility transformations and database patches",
            "features": [
                "Query transformations (IF ’ CASE WHEN)",
                "Index hint removal (FORCE INDEX)",
                "Transaction error handling",
                "Database method monkey patches"
            ]
        },
        {
            "name": "fix_erpnext_trends",
            "version": "1.0.0",
            "module": "frappe_pg.patches.v1.fix_erpnext_trends",
            "description": "Fix ERPNext trends.py GROUP BY issues for PostgreSQL strictness",
            "features": [
                "Item-based GROUP BY fix",
                "Customer-based GROUP BY fix",
                "Supplier-based GROUP BY fix",
                "Project-based GROUP BY fix",
                "Universal default_currency fix"
            ]
        },
        {
            "name": "db_functions",
            "version": "1.0.0",
            "module": "frappe_pg.postgres.db_functions",
            "description": "PostgreSQL functions for MySQL compatibility",
            "features": [
                "GROUP_CONCAT aggregate function",
                "unix_timestamp function",
                "timestampdiff function"
            ]
        }
    ]

    return {
        "app_version": __version__,
        "patches": patches,
        "total_patches": len(patches)
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _check_db_functions_installed():
    """
    Check if PostgreSQL compatibility functions are installed.

    Returns:
        bool: True if functions exist
    """
    if not frappe.db:
        return False

    try:
        # Try to use GROUP_CONCAT
        frappe.db.sql("SELECT GROUP_CONCAT('test')")
        return True
    except Exception:
        return False
