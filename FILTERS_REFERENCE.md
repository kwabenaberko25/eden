"""
Filter System Reference - Eden Templating Engine

The filter system enables flexible formatting of template expressions with
support for multiple international locales and standards.

This document outlines all 38+ available filters with examples from
different countries and locales.
"""

# ============================================================================
# PHONE FILTER
# ============================================================================

PHONE_FILTER = """
{{ phone | phone(format, country_code) }}

Formats phone numbers according to international standards for the specified country.

Formats:
  - 'national':       National format (e.g., "(024) 816-0391")
  - 'international':  International format (e.g., "+233 24 816 0391")
  - 'e164':           E.164 format (e.g., "+233248160391")
  - 'rfc3966':        RFC 3966 format (e.g., "tel:+233-24-816-0391")
  - 'ms':             MS format for specific country

Supported Countries (ISO 3166-1 alpha-2 codes):
  - Ghana (gh):           +233 | National: (024) 816-0391
  - United States (us):   +1   | National: (201) 555-0123
  - United Kingdom (gb):  +44  | National: 020 7946 0958
  - Nigeria (ng):         +234 | National: 803 555 0123
  - Kenya (ke):           +254 | National: 20 2622 2622
  - South Africa (za):    +27  | National: (021) 555-0123
  - Canada (ca):          +1   | National: (201) 555-0123
  - Australia (au):       +61  | National: 02 9555 0123
  - India (in):           +91  | National: 9876 543210
  - Germany (de):         +49  | National: 030 123456
  - France (fr):          +33  | National: 01 42 68 53 00
  - Japan (jp):           +81  | National: 03-1234-5678
  - China (cn):           +86  | National: 10 1234 5678
  - Brazil (br):          +55  | National: (11) 2648-0254
  - Mexico (mx):          +52  | National: 55 1234 5678

Examples:
  {{ user.phone | phone('national', 'gh') }}
    → (024) 816-0391

  {{ user.phone | phone('international', 'us') }}
    → +1 201-555-0123

  {{ user.phone | phone('e164', 'ng') }}
    → +2348035550123

  {{ customer.contact | phone('national', 'au') }}
    → 02 9555 0123

  {{ colleague.number | phone('international', 'de') }}
    → +49 30 123456
"""


# ============================================================================
# CURRENCY FILTER
# ============================================================================

CURRENCY_FILTER = """
{{ amount | currency(symbol, decimals, locale) }}

Formats numbers as currency values with locale-specific formatting.

Parameters:
  - symbol:    Currency symbol (e.g., "$", "€", "£", "¢")
  - decimals:  Number of decimal places (typically 2)
  - locale:    BCP 47 language tag with region (e.g., "en_US", "en_GB", "de_DE")

Supported Locales with Examples:

  Ghana (Cedi):
    {{ amount | currency('¢', 2, 'en_GH') }}
      → ¢1,500.00

  United States (USD):
    {{ price | currency('$', 2, 'en_US') }}
      → $1,234.56

  United Kingdom (GBP):
    {{ amount | currency('£', 2, 'en_GB') }}
      → £1,234.56

  Nigeria (Naira):
    {{ amount | currency('₦', 2, 'en_NG') }}
      → ₦1,234.56

  Kenya (Kenyan Shilling):
    {{ amount | currency('KSh', 2, 'en_KE') }}
      → KSh 1,234.56

  South Africa (Rand):
    {{ amount | currency('R', 2, 'en_ZA') }}
      → R1,234.56

  Canada (CAD):
    {{ price | currency('$', 2, 'en_CA') }}
      → $1,234.56

  Australia (AUD):
    {{ amount | currency('$', 2, 'en_AU') }}
      → $1,234.56

  India (Rupee):
    {{ amount | currency('₹', 2, 'en_IN') }}
      → ₹1,234.56

  Germany (EUR):
    {{ price | currency('€', 2, 'de_DE') }}
      → 1.234,56 €

  France (EUR):
    {{ amount | currency('€', 2, 'fr_FR') }}
      → 1 234,56 €

  Japan (JPY):
    {{ price | currency('¥', 0, 'ja_JP') }}
      → ¥1,235

  China (Yuan):
    {{ amount | currency('¥', 2, 'zh_CN') }}
      → ¥1,234.56

  Brazil (BRL):
    {{ price | currency('R$', 2, 'pt_BR') }}
      → R$ 1.234,56

  Mexico (MXN):
    {{ amount | currency('$', 2, 'es_MX') }}
      → $1,234.56

  Note: Locale determines thousands separator, decimal separator,
        and symbol placement according to regional conventions.
"""


# ============================================================================
# OTHER STRING FILTERS (20+)
# ============================================================================

STRING_FILTERS = """
String Manipulation Filters:

  - upper:        Convert to uppercase: "hello" → "HELLO"
  - lower:        Convert to lowercase: "HELLO" → "hello"
  - title:        Title case: "hello world" → "Hello World"
  - capitalize:   Capitalize first letter: "hello" → "Hello"
  - reverse:      Reverse string: "hello" → "olleh"
  - trim:         Remove leading/trailing whitespace
  - ltrim:        Remove leading whitespace
  - rtrim:        Remove trailing whitespace
  - replace:      Replace substrings: text | replace('old', 'new')
  - slice:        Extract substring: text | slice(0, 5)
  - length:       Get string length: "hello" | length → 5
  - split:        Split into array: text | split(',')
  - join:         Join array elements: items | join(', ')
  - contains:     Check if contains substring
  - startswith:   Check if starts with string
  - endswith:     Check if ends with string
  - repeat:       Repeat string: "ab" | repeat(3) → "ababab"
  - pad:          Pad string to length
  - truncate:     Truncate to length with ellipsis
  - slug:         Convert to URL-friendly slug
"""


# ============================================================================
# NUMERIC FILTERS (10+)
# ============================================================================

NUMERIC_FILTERS = """
Numeric Formatting Filters:

  - abs:          Absolute value: -42 | abs → 42
  - round:        Round to decimals: 3.14159 | round(2) → 3.14
  - ceil:         Round up: 3.14 | ceil → 4
  - floor:        Round down: 3.99 | floor → 3
  - min:          Get minimum: items | min
  - max:          Get maximum: items | max
  - sum:          Sum array: prices | sum
  - avg:          Average: prices | avg
  - percentage:   Format as percentage: 0.75 | percentage → 75%
  - format:       Format with pattern: num | format('0,000.00')
"""


# ============================================================================
# ARRAY/LIST FILTERS (8+)
# ============================================================================

ARRAY_FILTERS = """
Array/List Filters:

  - length:       Get array length: items | length
  - first:        Get first element: items | first
  - last:         Get last element: items | last
  - reverse:      Reverse array order
  - sort:         Sort array elements
  - unique:       Get unique elements: items | unique
  - flatten:      Flatten nested arrays
  - compact:      Remove null/empty values
"""


# ============================================================================
# CONDITIONAL/TEST FILTERS
# ============================================================================

TEST_FILTERS = """
Test Functions (used with 'is' keyword):

  - empty:        Check if empty: x is empty
  - filled:       Check if not empty: x is filled
  - null:         Check if null: x is null
  - defined:      Check if defined: x is defined
  - divisible_by: Check divisibility: n is divisible_by(3)
  - even:         Check if even number: n is even
  - odd:          Check if odd number: n is odd
  - sameas:       Check if same value: x is sameas(y)
  - starts:       Check string prefix: s is starts('prefix')
  - ends:         Check string suffix: s is ends('suffix')
"""


# ============================================================================
# FILTER CHAINING (INTERNATIONAL EXAMPLE)
# ============================================================================

FILTER_CHAINING_EXAMPLE = """
Filters can be chained together. Example:

  Multi-country invoice system:

    <!-- Ghana -->
    {{ invoice.total | currency('¢', 2, 'en_GH') | truncate(20) }}

    <!-- US -->
    {{ invoice.total | currency('$', 2, 'en_US') | truncate(20) }}

    <!-- Germany -->
    {{ invoice.total | currency('€', 2, 'de_DE') | truncate(20) }}

    <!-- Format phone for country -->
    {{ contact | phone('national', country_code.lower) }}
    
    <!-- Format and display -->
    {{ user.name | upper | truncate(30) }}
    {{ price | currency('$', 2, 'en_US') | upper }}
"""


# ============================================================================
# FILTER IMPLEMENTATION CHECKLIST (38+ filters)
# ============================================================================

FILTER_IMPLEMENTATION_CHECKLIST = """
String Filters (14):
  ✓ upper, lower, title, capitalize - case operations
  ✓ reverse - string reversal
  ✓ trim, ltrim, rtrim - whitespace removal
  ✓ replace, slice - substring operations
  ✓ length - string length
  ✓ truncate - length limiting
  ✓ slug - URL-friendly conversion
  ✓ repeat - repetition

Numeric Filters (10):
  ✓ abs, round, ceil, floor - numeric operations
  ✓ min, max, sum, avg - array statistics
  ✓ percentage - percentage formatting
  ✓ format - custom numeric formatting

Array Filters (8):
  ✓ length, first, last - access
  ✓ reverse, sort - ordering
  ✓ unique, flatten, compact - transformation

Locale/Internationalization (6):
  ✓ currency - multi-locale currency formatting
  ✓ phone - multi-country phone formatting
  ✓ date - locale-aware date formatting
  ✓ time - locale-aware time formatting
  ✓ number - locale-aware number formatting
  ✓ translate - localization/i18n support

TOTAL: 38+ filters with full international support
"""


if __name__ == '__main__':
    print("Eden Templating Engine - Filter System Reference")
    print("=" * 60)
    print()
    print("This reference documents all filters with international support.")
    print()
    print(PHONE_FILTER)
    print()
    print(CURRENCY_FILTER)
    print()
    print(STRING_FILTERS)
    print()
    print(NUMERIC_FILTERS)
    print()
    print(ARRAY_FILTERS)
    print()
    print(TEST_FILTERS)
    print()
    print(FILTER_CHAINING_EXAMPLE)
    print()
    print(FILTER_IMPLEMENTATION_CHECKLIST)
