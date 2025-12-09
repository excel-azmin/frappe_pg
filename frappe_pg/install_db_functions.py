#!/usr/bin/env python3
"""
Manual script to install PostgreSQL compatibility functions.

This script can be run manually to install database-level functions that
emulate MySQL functions needed by ERPNext.

Usage:
    bench --site your-site-name execute frappe_pg.install_db_functions.install
"""

import frappe


def install():
    """
    Install all PostgreSQL compatibility functions.
    """
    print("\n" + "=" * 70)
    print("Installing PostgreSQL Compatibility Functions")
    print("=" * 70)

    try:
        # Import and apply the patches first
        from frappe_pg.patches.postgres_fix import apply_postgres_fixes, create_missing_functions

        print("\n1. Applying query transformation patches...")
        apply_postgres_fixes()

        print("\n2. Creating database functions...")
        create_missing_functions()

        print("\n" + "=" * 70)
        print("✓ Installation completed successfully!")
        print("=" * 70)
        print("\nThe following functions have been installed:")
        print("  • GROUP_CONCAT(text) - MySQL-style string aggregation")
        print("  • unix_timestamp() - Convert timestamps to Unix epoch")
        print("  • timestampdiff() - Calculate time differences")
        print("\nYou can now use ERPNext with PostgreSQL.")
        print("=" * 70 + "\n")

    except Exception as e:
        print("\n" + "=" * 70)
        print("✗ Installation failed!")
        print("=" * 70)
        print(f"\nError: {str(e)}")
        print("\nPlease check the error logs and try again.")
        print("=" * 70 + "\n")
        raise


def verify():
    """
    Verify that all compatibility functions are installed correctly.
    """
    print("\n" + "=" * 70)
    print("Verifying PostgreSQL Compatibility Functions")
    print("=" * 70 + "\n")

    tests = []

    # Test GROUP_CONCAT
    try:
        result = frappe.db.sql("""
            SELECT GROUP_CONCAT(name::text)
            FROM (VALUES ('a'), ('b'), ('c')) AS t(name)
        """)
        expected = "a,b,c"
        if result and result[0][0] == expected:
            tests.append(("GROUP_CONCAT", "✓ PASS", f"Result: {result[0][0]}"))
        else:
            tests.append(("GROUP_CONCAT", "✗ FAIL", f"Expected '{expected}', got '{result[0][0]}'"))
    except Exception as e:
        tests.append(("GROUP_CONCAT", "✗ FAIL", str(e)))

    # Test unix_timestamp
    try:
        result = frappe.db.sql("SELECT unix_timestamp('2024-01-01 00:00:00'::timestamp)")
        if result and isinstance(result[0][0], int):
            tests.append(("unix_timestamp", "✓ PASS", f"Result: {result[0][0]}"))
        else:
            tests.append(("unix_timestamp", "✗ FAIL", f"Invalid result: {result}"))
    except Exception as e:
        tests.append(("unix_timestamp", "✗ FAIL", str(e)))

    # Test timestampdiff
    try:
        result = frappe.db.sql("""
            SELECT timestampdiff('day', '2024-01-01'::timestamp, '2024-01-10'::timestamp)
        """)
        expected = 9
        if result and result[0][0] == expected:
            tests.append(("timestampdiff", "✓ PASS", f"Result: {result[0][0]} days"))
        else:
            tests.append(("timestampdiff", "✗ FAIL", f"Expected {expected}, got {result[0][0]}"))
    except Exception as e:
        tests.append(("timestampdiff", "✗ FAIL", str(e)))

    # Print results
    print(f"{'Function':<20} {'Status':<12} {'Details'}")
    print("-" * 70)
    for name, status, details in tests:
        print(f"{name:<20} {status:<12} {details}")

    print("\n" + "=" * 70)

    # Summary
    passed = sum(1 for _, status, _ in tests if "✓" in status)
    total = len(tests)

    if passed == total:
        print(f"✓ All {total} tests passed!")
    else:
        print(f"✗ {passed}/{total} tests passed")

    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    print("This script should be run via bench:")
    print("  bench --site your-site-name execute frappe_pg.install_db_functions.install")
    print("  bench --site your-site-name execute frappe_pg.install_db_functions.verify")
