"""
ERPNext Trends Report PostgreSQL Fix

This module patches ERPNext's trends.py to fix GROUP BY issues with PostgreSQL.
PostgreSQL is stricter than MySQL and requires all non-aggregated columns in SELECT
to also be in the GROUP BY clause.
"""

import frappe


def apply_trends_patch():
    """
    Patch ERPNext's trends.py to add missing columns to GROUP BY clauses.
    """
    try:
        # Import the function we need to patch
        from erpnext.controllers import trends

        # Store original function
        _original_based_wise_columns_query = trends.based_wise_columns_query

        def patched_based_wise_columns_query(based_on, trans):
            """
            Patched version that fixes GROUP BY clauses for PostgreSQL compatibility.

            PostgreSQL requires all non-aggregated columns in SELECT to be in GROUP BY.
            This patches ERPNext's trends.py which was written for MySQL's lenient behavior.
            """
            based_on_details = _original_based_wise_columns_query(based_on, trans)

            # Extract current GROUP BY clause
            current_group_by = based_on_details.get("based_on_group_by", "")

            # Fix GROUP BY for Item-based queries
            if based_on == "Item":
                # Original: GROUP BY t2.item_code
                # Fixed: GROUP BY t2.item_code, t2.item_name
                if current_group_by == "t2.item_code":
                    current_group_by = "t2.item_code, t2.item_name"

            # Fix GROUP BY for Customer-based queries
            elif based_on == "Customer":
                if trans == "Quotation":
                    # For quotations: add party_name and territory
                    if "party_name" in based_on_details.get("based_on_select", ""):
                        if "party_name" not in current_group_by:
                            current_group_by += ", t1.customer_name, t1.territory"
                else:
                    # For other customer trans: add customer_name and territory
                    if "customer_name" in based_on_details.get("based_on_select", ""):
                        if "customer_name" not in current_group_by:
                            current_group_by += ", t1.customer_name, t1.territory"

            # Fix GROUP BY for Supplier-based queries
            elif based_on == "Supplier":
                if "supplier_name" in based_on_details.get("based_on_select", ""):
                    if "supplier_name" not in current_group_by:
                        current_group_by += ", t1.supplier_name"

            # Fix GROUP BY for Project-based queries
            elif based_on == "Project":
                if "project_name" in based_on_details.get("based_on_select", ""):
                    if "project_name" not in current_group_by:
                        current_group_by += ", t2.project_name"

            # CRITICAL FIX: Add t4.default_currency to ALL GROUP BY clauses
            # Line 423 of trends.py adds "t4.default_currency as currency" to SELECT for ALL reports
            # but never adds it to GROUP BY - this is the universal bug
            if "default_currency" in based_on_details.get("based_on_select", ""):
                if "default_currency" not in current_group_by and "t4.default_currency" not in current_group_by:
                    current_group_by += ", t4.default_currency"

            # Update the GROUP BY clause
            based_on_details["based_on_group_by"] = current_group_by

            return based_on_details

        # Apply the patch
        trends.based_wise_columns_query = patched_based_wise_columns_query

        print("✓ ERPNext trends.py patched for PostgreSQL GROUP BY compatibility")
        return True

    except Exception as e:
        print(f"⚠ Warning: Could not patch ERPNext trends.py: {e}")
        return False


# Apply patch when module is imported
try:
    apply_trends_patch()
except Exception as e:
    print(f"Warning: Error applying trends patch: {e}")
