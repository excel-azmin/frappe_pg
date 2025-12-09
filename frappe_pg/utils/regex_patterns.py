"""
Regular Expression Patterns for MySQL to PostgreSQL Query Transformation
========================================================================

This module contains all regex patterns used for identifying MySQL-specific
SQL syntax that needs to be transformed for PostgreSQL compatibility.
"""

import re


# ============================================================================
# Index Hint Patterns
# ============================================================================

# Pattern to match FORCE INDEX clauses
# Example: FORCE INDEX (posting_date)
FORCE_INDEX_PATTERN = re.compile(
    r'\s+FORCE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)

# Pattern to match USE INDEX clauses
# Example: USE INDEX (idx_name)
USE_INDEX_PATTERN = re.compile(
    r'\s+USE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)

# Pattern to match IGNORE INDEX clauses
# Example: IGNORE INDEX (idx_name)
IGNORE_INDEX_PATTERN = re.compile(
    r'\s+IGNORE\s+INDEX\s*\([^)]+\)',
    re.IGNORECASE
)


# ============================================================================
# Function Patterns
# ============================================================================

# Pattern to match IF(condition, true_value, false_value)
# This handles nested parentheses and complex expressions
# Example: IF(status='Active', amount, 0)
IF_FUNCTION_PATTERN = re.compile(
    r'\bIF\s*\(',
    re.IGNORECASE
)

# Pattern for IFNULL function
# Example: IFNULL(column, 0)
IFNULL_PATTERN = re.compile(
    r'\bIFNULL\s*\(',
    re.IGNORECASE
)

# Pattern for DATE_FORMAT function with %Y-%m-%d format
# Example: DATE_FORMAT(posting_date, '%Y-%m-%d')
DATE_FORMAT_PATTERN = re.compile(
    r'\bDATE_FORMAT\s*\(\s*([^,]+?)\s*,\s*[\'"]%Y-%m-%d[\'"]\s*\)',
    re.IGNORECASE
)

# Pattern for NOW() function with timezone considerations
# Example: NOW()
NOW_PATTERN = re.compile(
    r'\bNOW\s*\(\s*\)',
    re.IGNORECASE
)


# ============================================================================
# String and Operator Patterns
# ============================================================================

# Pattern for MySQL CONCAT function (to be converted to || operator)
# Example: CONCAT(first_name, ' ', last_name)
CONCAT_PATTERN = re.compile(
    r'\bCONCAT\s*\(',
    re.IGNORECASE
)

# Pattern for LIMIT with OFFSET syntax differences
# MySQL: LIMIT offset, count
# PostgreSQL: LIMIT count OFFSET offset
LIMIT_OFFSET_PATTERN = re.compile(
    r'\bLIMIT\s+(\d+)\s*,\s*(\d+)',
    re.IGNORECASE
)


# ============================================================================
# Helper Functions
# ============================================================================

def find_all_pattern_positions(pattern, text):
    """
    Find all positions where a pattern matches in text.

    Args:
        pattern: Compiled regex pattern
        text: String to search

    Returns:
        List of tuples (start_pos, end_pos, matched_text)
    """
    matches = []
    for match in pattern.finditer(text):
        matches.append((match.start(), match.end(), match.group()))
    return matches


def count_pattern_occurrences(pattern, text):
    """
    Count how many times a pattern occurs in text.

    Args:
        pattern: Compiled regex pattern
        text: String to search

    Returns:
        Integer count of matches
    """
    return len(pattern.findall(text))
