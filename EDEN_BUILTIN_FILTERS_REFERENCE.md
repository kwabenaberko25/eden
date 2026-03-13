# Eden Templating Engine - Built-in Filters Reference

**Total Built-in Filters:** 38+  
**Status:** ✅ Complete specification  
**Test Coverage:** 110+ filter test cases

---

## Quick Index

- [String Filters](#string-filters) — 10 filters
- [List/Array Filters](#listarray-filters) — 11 filters
- [Numeric Filters](#numeric-filters) — 6 filters
- [Conversion Filters](#conversion-filters) — 2 filters
- [Formatting Filters](#formatting-filters) — 3 filters (NEW: phone, currency)
- [Special Filters](#special-filters) — 7 filters

---

## String Filters

### `uppercase`
Converts string to uppercase.

```
{{ "hello world" | uppercase }}
→ "HELLO WORLD"
```

### `lowercase`
Converts string to lowercase.

```
{{ "HELLO WORLD" | lowercase }}
→ "hello world"
```

### `capitalize`
Capitalizes the first letter (rest lowercase).

```
{{ "hello world" | capitalize }}
→ "Hello world"
```

### `title`
Converts to title case (capitalize each word).

```
{{ "hello world" | title }}
→ "Hello World"
```

### `reverse`
Reverses string or list.

```
{{ "hello" | reverse }}
→ "olleh"

{{ [1, 2, 3] | reverse }}
→ [3, 2, 1]
```

### `trim`
Removes leading and trailing whitespace.

```
{{ "  hello  " | trim }}
→ "hello"
```

### `ltrim`
Removes leading whitespace only.

```
{{ "  hello" | ltrim }}
→ "hello"
```

### `rtrim`
Removes trailing whitespace only.

```
{{ "hello  " | rtrim }}
→ "hello"
```

### `slugify`
Converts to URL-friendly slug (lowercase, hyphens).

```
{{ "Hello World!" | slugify }}
→ "hello-world"

{{ "User's Profile" | slugify }}
→ "users-profile"
```

### `truncate(length, suffix?)`
Truncates string to specified length with optional suffix.

```
{{ "Hello World" | truncate(5) }}
→ "Hello"

{{ "Hello World" | truncate(8, "...") }}
→ "Hello..."
```

---

## List/Array Filters

### `length`
Returns count of items in list or characters in string.

```
{{ [1, 2, 3, 4, 5] | length }}
→ 5

{{ "hello" | length }}
→ 5
```

### `join(separator)`
Joins array elements with separator into string.

```
{{ ["apple", "banana", "cherry"] | join(", ") }}
→ "apple, banana, cherry"

{{ [1, 2, 3] | join("-") }}
→ "1-2-3"
```

### `split(separator)`
Splits string into array using separator.

```
{{ "a,b,c" | split(",") }}
→ ["a", "b", "c"]

{{ "hello world" | split(" ") }}
→ ["hello", "world"]
```

### `first`
Gets first element of array or string.

```
{{ ["apple", "banana", "cherry"] | first }}
→ "apple"

{{ "hello" | first }}
→ "h"
```

### `last`
Gets last element of array or string.

```
{{ ["apple", "banana", "cherry"] | last }}
→ "cherry"

{{ "hello" | last }}
→ "o"
```

### `nth(index)`
Gets element at specific index (0-based).

```
{{ ["a", "b", "c", "d"] | nth(2) }}
→ "c"

{{ "hello" | nth(1) }}
→ "e"
```

### `sort`
Sorts array in ascending order.

```
{{ [3, 1, 4, 1, 5, 9] | sort }}
→ [1, 1, 3, 4, 5, 9]

{{ ["cherry", "apple", "banana"] | sort }}
→ ["apple", "banana", "cherry"]
```

### `reverse_sort`
Sorts array in descending order.

```
{{ [3, 1, 4, 1, 5] | reverse_sort }}
→ [5, 4, 3, 1, 1]

{{ ["cherry", "apple", "banana"] | reverse_sort }}
→ ["cherry", "banana", "apple"]
```

### `unique`
Removes duplicate values from array.

```
{{ [1, 2, 2, 3, 3, 3, 4] | unique }}
→ [1, 2, 3, 4]

{{ ["a", "b", "b", "c"] | unique }}
→ ["a", "b", "c"]
```

### `slice(start, end?)`
Extracts portion of array or string.

```
{{ [1, 2, 3, 4, 5] | slice(1, 4) }}
→ [2, 3, 4]

{{ "hello" | slice(1, 4) }}
→ "ell"
```

### `map(attribute)`
Extracts specified attribute/key from each item.

```
{{ [{"name": "Alice"}, {"name": "Bob"}] | map("name") }}
→ ["Alice", "Bob"]

{{ users | map("name") | join(", ") }}
→ "Alice, Bob, Charlie"
```

---

## Numeric Filters

### `round(decimals?)`
Rounds number to specified decimal places.

```
{{ 3.14159 | round }}
→ 3

{{ 3.14159 | round(2) }}
→ 3.14

{{ 3.14159 | round(4) }}
→ 3.1416
```

### `abs`
Returns absolute value (removes negative sign).

```
{{ -42 | abs }}
→ 42

{{ 38 | abs }}
→ 38
```

### `min`
Returns minimum value from array.

```
{{ [5, 2, 9, 1, 7] | min }}
→ 1

{{ [3.14, 2.71, 1.41] | min }}
→ 1.41
```

### `max`
Returns maximum value from array.

```
{{ [5, 2, 9, 1, 7] | max }}
→ 9

{{ [3.14, 2.71, 1.41] | max }}
→ 3.14
```

### `sum`
Returns sum of all values in array.

```
{{ [1, 2, 3, 4, 5] | sum }}
→ 15

{{ [1.5, 2.5, 3.5] | sum }}
→ 7.5
```

### `avg`
Returns average (mean) of values in array.

```
{{ [2, 4, 6, 8] | avg }}
→ 5

{{ [10, 20, 30] | avg }}
→ 20
```

---

## Conversion Filters

### `json`
Converts value to JSON string.

```
{{ {"name": "Alice", "age": 30} | json }}
→ '{"name": "Alice", "age": 30}'

{{ [1, 2, 3] | json }}
→ '[1, 2, 3]'
```

### `escape`
HTML-escapes special characters (for safe output).

```
{{ "<script>alert('xss')</script>" | escape }}
→ "&lt;script&gt;alert('xss')&lt;/script&gt;"

{{ "Hello & Goodbye" | escape }}
→ "Hello &amp; Goodbye"
```

---

## Formatting Filters

### `format(pattern?)`
Formats value according to pattern.

```
{{ 1234.56 | format("${:,.2f}") }}
→ "$1,234.56"

{{ 0.75 | format("{:.0%}") }}
→ "75%"

{{ 42 | format("{:05d}") }}
→ "00042"
```

### `currency(symbol?, decimals?, locale?)`
Formats number as currency with symbol and decimal places.

```
{{ 1234.56 | currency("$") }}
→ "$1,234.56"

{{ 1234.567 | currency("¢", 2) }}
→ "¢1,234.57" (rounded to 2 decimals)

{{ 1234.56 | currency("€", 2, "de_DE") }}
→ "1.234,56 €" (German format)

{{ 99.99 | currency("₱", 2) }}
→ "₱99.99" (Philippine Peso)

{{ 500 | currency("GHS", 2) }}
→ "GHS 500.00" (Ghana Cedis)
```

**Common Currency Symbols:**
- `$` — US Dollar
- `€` — Euro
- `£` — British Pound
- `¥` — Japanese Yen / Chinese Yuan
- `₹` — Indian Rupee
- `₽` — Russian Ruble
- `₩` — South Korean Won
- `¢` — Cent / Ghana Cedi
- `₱` — Philippine Peso
- `₿` — Bitcoin
- `GHS` — Ghana Cedis (text code)
- `USD`, `EUR`, `PHP`, `INR` — ISO codes

### `phone(format?, country?)`
Formats phone number with optional formatting and country code.

```
{{ "0248160391" | phone }}
→ "024 816 0391" (default)

{{ "0248160391" | phone("GH") }}
→ "+233 248 160 391" (Ghana international)

{{ "0248160391" | phone("GH-standard") }}
→ "024 816 0391" (Ghana standard)

{{ "2348160391" | phone("NG") }}
→ "+234 816 0391" (Nigeria international)

{{ "5551234567" | phone("US") }}
→ "+1 (555) 123-4567" (USA)

{{ "33145678901" | phone("FR") }}
→ "+33 1 45 67 89 01" (France)

{{ "441632960000" | phone("UK") }}
→ "+44 163 296 0000" (UK)

{{ "491234567890" | phone("DE") }}
→ "+49 30 1234 567890" (Germany)

{{ "81312345678" | phone("JP") }}
→ "+81 3 1234 5678" (Japan)
```

**Supported Countries (with automatic formatting):**

| Country | Code | Example | Output |
|---------|------|---------|--------|
| Ghana | GH | 0248160391 | +233 248 160 391 |
| Nigeria | NG | 2348160391 | +234 816 0391 |
| USA | US | 5551234567 | +1 (555) 123-4567 |
| UK | UK | 441632960000 | +44 163 296 0000 |
| France | FR | 33145678901 | +33 1 4567 8901 |
| Germany | DE | 491234567890 | +49 12 3456 7890 |
| Japan | JP | 81312345678 | +81 3 1234 5678 |
| China | CN | 8610123456789 | +86 10 1234 5678 |

**Format Options:**
- `international` or `+` — International format: +233 24 8160391
- `standard` or `dash` — Dashed format: 024-816-0391
- `space` — Space-separated: 024 816 0391 (default)
- `dots` — Dot-separated: 024.816.0391
- `raw` — No formatting: 0248160391

---

## Special Filters

### `default(fallback_value)`
Provides default value if variable is undefined or empty.

```
{{ missing_var | default("N/A") }}
→ "N/A"

{{ empty_string | default("empty") }}
→ "empty"

{{ actual_value | default("fallback") }}
→ "actual_value"
```

### `safe`
Marks value as safe HTML (prevents escaping).

```
<!-- In template -->
{{ rendered_html | safe }}

<!-- Without safe filter: -->
{{ rendered_html }}
<!-- → "&lt;p&gt;Hello&lt;/p&gt;" (escaped) -->

<!-- With safe filter: -->
{{ rendered_html | safe }}
<!-- → "<p>Hello</p>" (not escaped) -->
```

### `conditional(true_value, false_value)`
Returns one of two values based on truthiness (ternary-like).

```
{{ user.is_active | conditional("Active", "Inactive") }}
→ "Active" or "Inactive"

{{ item_count | conditional("1 item", "0 items") }}
→ "1 item" (if count > 0) or "0 items" (if count == 0)
```

### `pluralize(singular, plural)`
Returns singular or plural form based on count.

```
{{ item_count | pluralize("item", "items") }}
→ "1 item" (if count == 1)
→ "5 items" (if count == 5)
→ "0 items" (if count == 0)

{{ user.post_count | pluralize("post", "posts") }}
```

### `format(pattern?)`
Formats value according to pattern.

```
{{ 1234.56 | format("${:,.2f}") }}
→ "$1,234.56"

{{ 0.75 | format("{:.0%}") }}
→ "75%"

{{ 42 | format("{:05d}") }}
→ "00042"
```

### `currency(symbol?, decimals?, locale?)`
Formats number as currency with symbol and decimal places.

```
{{ 1234.56 | currency("$") }}
→ "$1,234.56"

{{ 1234.567 | currency("¢", 2) }}
→ "¢1,234.57" (rounded to 2 decimals)

{{ 1234.56 | currency("€", 2, "de_DE") }}
→ "1.234,56 €" (German format)

{{ 99.99 | currency("₱", 2) }}
→ "₱99.99" (Philippine Peso)

{{ 500 | currency("GHS", 2) }}
→ "GHS 500.00" (Ghana Cedis)
```

**Common Currency Symbols:**
- `$` — US Dollar
- `€` — Euro
- `£` — British Pound
- `¥` — Japanese Yen / Chinese Yuan
- `₹` — Indian Rupee
- `₽` — Russian Ruble
- `₩` — South Korean Won
- `¢` — Cent / Ghana Cedi
- `₱` — Philippine Peso
- `₿` — Bitcoin
- `GHS` — Ghana Cedis (text code)
- `USD`, `EUR`, `PHP`, `INR` — ISO codes

### `phone(format?, country?)`
Formats phone number with optional formatting and country code.

```
{{ "0248160391" | phone }}
→ "024 816 0391" (default)

{{ "0248160391" | phone("GH") }}
→ "+233 248 160 391" (Ghana international)

{{ "0248160391" | phone("GH-standard") }}
→ "024 816 0391" (Ghana standard)

{{ "2348160391" | phone("NG") }}
→ "+234 816 0391" (Nigeria international)

{{ "5551234567" | phone("US") }}
→ "+1 (555) 123-4567" (USA)

{{ "33145678901" | phone("FR") }}
→ "+33 1 45 67 89 01" (France)

{{ "441632960000" | phone("UK") }}
→ "+44 163 296 0000" (UK)

{{ "491234567890" | phone("DE") }}
→ "+49 30 1234 567890" (Germany)

{{ "81312345678" | phone("JP") }}
→ "+81 3 1234 5678" (Japan)
```

**Supported Countries (with automatic formatting):**

| Country | Code | Example | Output |
|---------|------|---------|--------|
| Ghana | GH | 0248160391 | +233 248 160 391 |
| Nigeria | NG | 2348160391 | +234 816 0391 |
| USA | US | 5551234567 | +1 (555) 123-4567 |
| UK | UK | 441632960000 | +44 163 296 0000 |
| France | FR | 33145678901 | +33 1 4567 8901 |
| Germany | DE | 491234567890 | +49 12 3456 7890 |
| Japan | JP | 81312345678 | +81 3 1234 5678 |
| China | CN | 8610123456789 | +86 10 1234 5678 |

**Format Options:**
- `international` or `+` — International format: +233 24 8160391
- `standard` or `dash` — Dashed format: 024-816-0391
- `space` — Space-separated: 024 816 0391 (default)
- `dots` — Dot-separated: 024.816.0391
- `raw` — No formatting: 0248160391

### `select(attribute, value?)`
Filters array to keep items where attribute is truthy/matches value.

```
{{ users | select("is_active") }}
→ Only returns active users

{{ posts | select("status", "published") }}
→ Only returns published posts
```

### `reject(attribute, value?)`
Filters array to remove items where attribute is truthy/matches value.

```
{{ users | reject("is_banned") }}
→ Removes banned users

{{ posts | reject("status", "draft") }}
→ Removes draft posts
```

---

## Filter Chaining

Filters can be chained together—output of one becomes input to next.

```html
<!-- Single filter -->
{{ message | uppercase }}

<!-- Multiple filters -->
{{ long_description 
    | truncate(100, "...")
    | uppercase
}}

<!-- Complex chain -->
{{ users 
    | select("is_active")
    | map("name")
    | join(", ")
    | uppercase
}}
→ "ALICE, BOB, CHARLIE"

<!-- With parameters -->
{{ numbers 
    | sort
    | reverse_sort
    | slice(0, 3)
    | sum
}}
```

---

## Custom Filters

Register custom filters from Python code:

```python
# In your engine setup
def my_custom_filter(value, arg1, arg2):
    """My custom filter implementation"""
    return processed_value

engine.register_filter("my_filter", my_custom_filter)
```

Then use in templates:

```html
{{ value | my_filter("arg1", "arg2") }}
```

**Custom Filter Rules:**
- Must be pure functions (no side effects)
- Should handle `None` gracefully
- Return string or template-safe type
- Arguments optional but supported
- Name must be valid Python identifier

---

## Filter Usage Patterns

### Safe HTML Output
```html
{{ user_provided_content | escape }}
{{ trusted_html | safe }}
```

### Default Values
```html
{{ product.description | default("No description available") }}
```

### List Processing
```html
{{ tags | unique | sort | join(", ") }}
```

### Conditional Display
```html
{{ status | conditional("✓ Active", "✗ Inactive") }}
```

### Formatting for Display
```html
{{ price | format("${:,.2f}") }}
{{ percentage | format("{:.1%}") }}
```

### Pagination
```html
{{ all_items | slice(start, start + per_page) | map("name") }}
```

---

## Performance Notes

- **String filters** — O(n) where n = string length
- **List filters** (sort, unique) — O(n log n)
- **List operations** (map, select) — O(n)
- **Chaining** — Each filter processes full output of previous
- **Caching** — Filter expressions can be pre-compiled for repeats

---

## Implementation Status

| Category | Count | Status | Tests |
|----------|-------|--------|-------|
| String Filters | 10 | ✅ Complete | 20+ |
| List Filters | 11 | ✅ Complete | 25+ |
| Numeric Filters | 6 | ✅ Complete | 15+ |
| Conversion | 2 | ✅ Complete | 10+ |
| Formatting | 3 | ✅ Complete (NEW) | 25+ |
| Special | 7 | ✅ Complete | 20+ |
| **Total** | **38+** | **✅ Complete** | **110+** |

---

## See Also

- [EDEN_SYNTAX_STANDARD_FINAL.md](EDEN_SYNTAX_STANDARD_FINAL.md) — Full syntax reference
- [EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md](EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md) — Implementation details
- Phase 2: `runtime/filters.py` — Filter implementations
