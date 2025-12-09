#!/usr/bin/env python3
"""
Debug script to check if patches are actually being called at runtime
"""

def test_patches():
    import frappe

    print("\n" + "=" * 70)
    print("Debugging Runtime Patch Application")
    print("=" * 70 + "\n")

    # Check the PostgresDatabase.sql method identity
    from frappe.database.postgres.database import PostgresDatabase

    print(f"PostgresDatabase.sql: {PostgresDatabase.sql}")
    print(f"Method module: {PostgresDatabase.sql.__module__}")
    print(f"Method name: {PostgresDatabase.sql.__name__}")

    # Check if it's our patched version
    import inspect
    try:
        source = inspect.getsource(PostgresDatabase.sql)
        if "apply_all_query_transformations" in source:
            print("\n✓ PostgresDatabase.sql IS our patched version")
            print(f"  First few lines:")
            for line in source.split('\n')[:10]:
                print(f"    {line}")
        else:
            print("\n✗ PostgresDatabase.sql is NOT our patched version")
            print(f"  First few lines:")
            for line in source.split('\n')[:10]:
                print(f"    {line}")
    except:
        print("\n⚠ Could not get source")

    # Check the actual instance
    print(f"\nfrappe.db type: {type(frappe.db)}")
    print(f"frappe.db.sql: {frappe.db.sql}")

    # Try to call a query with IF() and see what happens
    print("\n" + "=" * 70)
    print("Testing actual query execution with IF()")
    print("=" * 70)

    # Add a debug wrapper
    original_execute = frappe.db._cursor.execute
    executed_queries = []

    def debug_execute(query, *args, **kwargs):
        executed_queries.append(str(query))
        return original_execute(query, *args, **kwargs)

    frappe.db._cursor.execute = debug_execute

    try:
        # Try a query with IF() - it should fail if not converted
        test_query = """
            SELECT
                name,
                CASE WHEN 1=1 THEN 'converted' ELSE 'failed' END as status
            FROM "tabDocType"
            LIMIT 1
        """
        result = frappe.db.sql(test_query)
        print(f"✓ Query executed successfully")
        print(f"  Result: {result}")

        if executed_queries:
            print(f"\n  Last executed SQL:")
            print(f"  {executed_queries[-1][:200]}...")
    except Exception as e:
        print(f"✗ Query failed: {e}")
        if executed_queries:
            print(f"\n  Last attempted SQL:")
            print(f"  {executed_queries[-1][:200]}...")
    finally:
        frappe.db._cursor.execute = original_execute

    print("\n" + "=" * 70)

if __name__ == "__main__":
    import frappe
    frappe.init(site='development.localhost')
    frappe.connect()
    test_patches()
