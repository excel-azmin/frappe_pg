"""
PostgreSQL Database Functions for MySQL Compatibility
=====================================================

This module creates PostgreSQL functions that emulate MySQL-specific functions
that don't exist in PostgreSQL.

Functions created:
- GROUP_CONCAT: Concatenate strings from multiple rows
- unix_timestamp: Get Unix timestamp from a datetime
- timestampdiff: Calculate difference between two timestamps
"""

import frappe


# ============================================================================
# Database Function Creation
# ============================================================================

def create_missing_functions():
    """
    Create PostgreSQL functions that emulate MySQL functions.

    This is called during installation/migration to ensure all required
    database-level functions exist.

    Functions created:
    1. group_concat_sfunc: State transition function for GROUP_CONCAT
    2. GROUP_CONCAT: Aggregate function to concatenate strings
    3. unix_timestamp(timestamp with time zone): Convert to Unix timestamp
    4. unix_timestamp(timestamp without time zone): Convert to Unix timestamp
    5. timestampdiff: Calculate time difference in various units

    Returns:
        None

    Raises:
        Exception: If database connection is not available
    """
    if not frappe.db:
        print("⚠ Database not available, skipping function creation")
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
                print(f"  ⚠ Warning creating function: {str(e)[:100]}")

    if error_count == 0:
        print(f"✓ PostgreSQL compatibility functions created ({success_count} statements)")
    else:
        print(f"⚠ Created functions with {error_count} warnings ({success_count} succeeded)")


def verify_db_functions():
    """
    Verify that all required PostgreSQL functions exist and work correctly.

    This function tests each created function to ensure it's working as expected.

    Tests:
    1. GROUP_CONCAT: Concatenates strings with comma separator
    2. unix_timestamp: Returns Unix timestamp
    3. timestampdiff: Calculates time differences

    Returns:
        bool: True if all functions work, False otherwise
    """
    if not frappe.db:
        print("⚠ Database not available for verification")
        return False

    tests = [
        {
            'name': 'GROUP_CONCAT',
            'query': "SELECT GROUP_CONCAT(val) FROM (VALUES ('a'), ('b'), ('c')) AS t(val)",
            'expected': 'a,b,c'
        },
        {
            'name': 'unix_timestamp (current time)',
            'query': "SELECT unix_timestamp() > 0",
            'expected': True
        },
        {
            'name': 'unix_timestamp (specific time)',
            'query': "SELECT unix_timestamp('2024-01-01 00:00:00'::timestamp)",
            'expected_type': int
        },
        {
            'name': 'timestampdiff (days)',
            'query': "SELECT timestampdiff('day', '2024-01-01'::timestamp, '2024-01-31'::timestamp)",
            'expected': 30
        },
        {
            'name': 'timestampdiff (hours)',
            'query': "SELECT timestampdiff('hour', '2024-01-01 00:00:00'::timestamp, '2024-01-01 12:00:00'::timestamp)",
            'expected': 12
        }
    ]

    all_passed = True

    print("\nVerifying PostgreSQL compatibility functions:")
    print("=" * 60)

    for test in tests:
        try:
            result = frappe.db.sql(test['query'], as_list=True)
            actual = result[0][0] if result else None

            # Check expected value or type
            if 'expected' in test:
                if actual == test['expected']:
                    print(f"✓ {test['name']}: PASSED")
                else:
                    print(f"✗ {test['name']}: FAILED (expected {test['expected']}, got {actual})")
                    all_passed = False
            elif 'expected_type' in test:
                if isinstance(actual, test['expected_type']):
                    print(f"✓ {test['name']}: PASSED (returned {test['expected_type'].__name__})")
                else:
                    print(f"✗ {test['name']}: FAILED (expected {test['expected_type'].__name__}, got {type(actual).__name__})")
                    all_passed = False

        except Exception as e:
            print(f"✗ {test['name']}: ERROR - {str(e)[:80]}")
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✓ All function verification tests passed!")
    else:
        print("⚠ Some function verification tests failed")

    return all_passed


def drop_all_functions():
    """
    Drop all PostgreSQL compatibility functions.

    This is useful for clean reinstallation or troubleshooting.

    WARNING: This will remove all compatibility functions. Only use this
    if you're reinstalling or removing the frappe_pg app.

    Returns:
        None
    """
    if not frappe.db:
        print("⚠ Database not available")
        return

    drop_statements = [
        "DROP AGGREGATE IF EXISTS GROUP_CONCAT(text) CASCADE",
        "DROP FUNCTION IF EXISTS group_concat_sfunc(text, text) CASCADE",
        "DROP FUNCTION IF EXISTS unix_timestamp(timestamp with time zone) CASCADE",
        "DROP FUNCTION IF EXISTS unix_timestamp(timestamp without time zone) CASCADE",
        "DROP FUNCTION IF EXISTS unix_timestamp() CASCADE",
        "DROP FUNCTION IF EXISTS timestampdiff(text, timestamp, timestamp) CASCADE"
    ]

    for sql in drop_statements:
        try:
            frappe.db.sql(sql)
            frappe.db.commit()
        except Exception as e:
            print(f"  Warning dropping function: {str(e)[:100]}")

    print("✓ All PostgreSQL compatibility functions dropped")
