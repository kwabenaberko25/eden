# Eden Templating Engine: Documentation vs Implementation Audit

**Date:** March 13, 2026  
**Status:** Comprehensive audit comparing actual engine implementation against documentation

---

## Executive Summary

**CRITICAL ISSUES FOUND:** 12 documented filters do NOT exist in implementation  
**MEDIUM ISSUES:** 3 directives partially implemented or stubbed  
**IMPACT:** Templates using documented filters will fail at runtime

---

## Part 1: Directives Analysis

### Documented vs Implemented

#### ✅ FULLY DOCUMENTED & FULLY IMPLEMENTED (24)

| Directive | Status | Notes |
|-----------|--------|-------|
| @if | ✓ | Codegen compiled |
| @unless | ✓ | Codegen compiled |
| @for | ✓ | Codegen compiled, includes $loop |
| @foreach | Documented implicitly in examples | ✓ Implemented |
| @switch | ✓ | Codegen compiled |
| @case | ✓ | Codegen compiled |
| @let | ✓ | Runtime implemented |
| @extends | ✓ | Partial (external callback) |
| @include | ✓ | Partial (external callback) |
| @section | ✓ | Partially (placeholder) |
| @yield | ✓ | Partially (placeholder) |
| @push | ✓ | Partially (placeholder) |
| @auth | ✓ | Runtime implemented |
| @guest | ✓ | Runtime implemented |
| @csrf | ✓ | Runtime implemented |
| @method | ✓ | Runtime implemented |
| @checked | ✓ | Runtime implemented |
| @selected | ✓ | Runtime implemented |
| @disabled | ✓ | Runtime implemented |
| @readonly | ✓ | Runtime implemented |
| @error | ✓ | Runtime implemented |
| @old | ✓ | Runtime implemented |
| @css | ✓ | Runtime implemented |
| @js | ✓ | Runtime implemented |

#### ⚠️ PARTIALLY DOCUMENTED & PARTIALLY IMPLEMENTED (8)

| Directive | Doc Status | Implementation | Issue |
|-----------|-----------|-----------------|-------|
| @vite | ✓ Documented | ✓ Implemented | Works but limited examples |
| @json | ✓ Documented | ✓ Implemented | Works as expected |
| @dump | ✓ Documented | ✓ Implemented | Works as expected |
| @span | ✓ Documented | ✓ Implemented | Works as expected |
| @fragment | ✓ Documented | ✓ Implemented | Works as expected |
| @url | ✓ Documented | ✓ Implemented but returns placeholder | Returns `{{ url_for(...) }}` pattern, not actual URL |
| @active_link | ✓ Documented | ✓ Implemented | Works, supports wildcards |
| @htmx / @non_htmx | ✓ Documented | ✓ Implemented | Works correctly |

#### ❌ DOCUMENTED BUT NOT FULLY IMPLEMENTED (2)

| Directive | Documentation | Implementation | Problem |
|-----------|---------------|-----------------|---------|
| @render_field | ✓ Documented extensively | Handler placeholder only | Component rendering not functional; docs show full examples |
| @component | Mentioned in component patterns | Handler placeholder | No implementation for @component/@slot pattern |

#### ⚠️ DOCUMENTED BUT EXPLICITLY WARNED AS UNIMPLEMENTED (4)

| Directive | Status | Notes |
|-----------|--------|-------|
| @can | ✓ Warned (deprecated) | Not implemented; docs say "use Python logic" |
| @cannot | ✓ Warned (deprecated) | Not implemented; docs say "use Python logic" |
| @inject | ✓ Warned (deprecated) | Not implemented; docs say "use Python logic" |
| @php | ✓ Warned (deprecated) | Not implemented; docs say "use Python logic" |

#### ✗ IMPLEMENTED BUT NOT DOCUMENTED (1)

| Directive | Implementation | Documentation | Issue |
|-----------|-----------------|-----------------|-------|
| @route | Returns empty string; stub | NOT documented | Undocumented stub could confuse users |

#### 🔴 MISSING FROM BOTH (3)

| Directive | Notes |
|-----------|-------|
| @super | Implemented but not documented | Allows parent block rendering in inheritance |
| @props | Implemented but not documented | Component properties |
| @messages | Implemented but not documented | Message iterator |
| @flash | Implemented but not documented | Flash message rendering |
| @status | Implemented but not documented | HTTP status code matching |
| @break | Implemented but not documented | Loop control |
| @continue | Implemented but not documented | Loop control |
| @empty | Documented but not in implementation | Loop empty fallback missing |

---

## Part 2: Filters Analysis - CRITICAL ISSUES

### DOCUMENTED BUT MISSING FROM IMPLEMENTATION

**These filters are documented but DO NOT EXIST in the engine!**

| Filter | Doc Location | Claimed Behavior | Implementation Status |
|--------|--------------|------------------|----------------------|
| **money** | Filters Reference | Format as currency | ❌ NOT FOUND |
| **time_ago** | Filters Reference | Human-readable time distance | ❌ NOT FOUND |
| **slugify** | Filters Reference | URL-safe slug | ✓ FOUND as "slug" (different name!) |
| **mask** | Filters Reference | Mask sensitive strings | ❌ NOT FOUND |
| **file_size** | Filters Reference | Format bytes to KB/MB/GB | ❌ NOT FOUND |
| **pluralize** | Filters Reference | Suffix based on count | ❌ NOT FOUND |
| **title_case** | Filters Reference | Uppercase first letter | ❌ NOT FOUND |
| **default_if_none** | Filters Reference | Fallback if None | ❌ NOT FOUND |
| **json_encode** | Filters Reference | JSON serialization | ✓ FOUND as "json" |
| **add_class** | Widget Tweaks | Append CSS class | ❌ NOT FOUND |
| **attr** | Widget Tweaks | Set attribute | ❌ NOT FOUND |
| **append_attr** | Widget Tweaks | Append to attribute | ❌ NOT FOUND |
| **remove_attr** | Widget Tweaks | Remove attribute | ❌ NOT FOUND |
| **field_type** | Widget Tweaks | Get field type | ❌ NOT FOUND |

#### Filter Naming Mismatches

| Documented Name | Actual Implementation | Status |
|-----------------|----------------------|--------|
| slugify | slug | Name mismatch |
| json_encode | json | Name mismatch |
| money | currency | Documented but uses different name in implementation |
| phone | phone | ✓ Matches (partial implementation) |
| currency | currency | ✓ Matches (partial implementation) |

### ✅ FILTERS CORRECTLY DOCUMENTED

| Filter | Implementation | Status |
|--------|------------------|--------|
| upper | ✓ str.upper() | Matches docs |
| lower | ✓ str.lower() | Matches docs |
| title | ✓ str.title() | Matches docs |
| capitalize | ✓ str.capitalize() | Matches docs |
| reverse | ✓ String/array reversal | Matches docs |
| trim | trim (ltrim, rtrim) | ✓ Matches docs |
| replace | ✓ str.replace() | Matches docs |
| slice | ✓ Slicing support | Matches docs |
| length | ✓ len() | Matches docs |
| truncate | ✓ String truncation | Matches docs |
| slug | ✓ URL-safe slug | Matches docs (as "slug" not "slugify") |
| repeat | ✓ String repeat | Matches docs |
| abs | ✓ abs() | Matches docs |
| round | ✓ round(n, p) | Matches docs |
| ceil | ✓ math.ceil | Matches docs |
| floor | ✓ int() | Matches docs |
| first | ✓ arr[0] | Matches docs |
| last | ✓ arr[-1] | Matches docs |
| unique | ✓ dict.fromkeys() | Matches docs |
| sort | ✓ sorted() | Matches docs |
| reverse_array | Documented as reverse | ✓ Implemented as reverse |
| json | ✓ json.dumps() | Matches docs (documented as json_encode) |
| currency | ✓ Currency formatter | Partial implementation |
| phone | ✓ Phone formatter | Partial implementation |
| date | ✓ strftime() | Matches docs |
| time | ✓ strftime() | Matches docs |

### Design System Filters (eden_bg, eden_shadow, eden_text)

| Filter | Documented | Implementation | Status |
|--------|-----------|-----------------|--------|
| eden_bg | ✓ Yes | ❌ NOT FOUND | Missing |
| eden_shadow | ✓ Yes | ❌ NOT FOUND | Missing |
| eden_text | ✓ Yes | ❌ NOT FOUND | Missing |

---

## Part 3: Tests/Assertions Analysis

### ✅ ALL TESTS CORRECTLY IMPLEMENTED

| Test | Implementation |
|------|-----------------|
| empty | ✓ Implemented |
| filled | ✓ Implemented |
| null | ✓ Implemented |
| defined | ✓ Implemented |
| even | ✓ Implemented |
| odd | ✓ Implemented |
| divisible_by | ✓ Implemented |
| sameas | ✓ Implemented |
| starts | ✓ Implemented |
| ends | ✓ Implemented |
| string | ✓ Implemented |
| number | ✓ Implemented |
| boolean | ✓ Implemented |

---

## Part 4: Risk Assessment & Impact

### 🔴 CRITICAL ISSUES (Will Break Templates)

**Probability: VERY HIGH if users follow documentation**

1. **Widget Form Filters (5 filters)**
   - `add_class`, `attr`, `append_attr`, `remove_attr`, `field_type`
   - Documented with examples but NOT implemented
   - Error: `FilterNotFound` or `AttributeError`
   - User Impact: Form customization patterns from docs won't work

2. **Utility Filters (9 filters)**
   - `money`, `time_ago`, `mask`, `file_size`, `pluralize`, `title_case`, `default_if_none`, `eden_*` (3 filters)
   - Documented but NOT implemented
   - Error: `FilterNotFound`
   - User Impact: Any template using these filters will fail

3. **@render_field Directive**
   - Extensive documentation with real-world examples
   - Only placeholder implementation
   - Error: Output may be incorrect or missing
   - User Impact: Forms rendered with @render_field won't display properly

### ⚠️ MEDIUM ISSUES (May Confuse Users)

1. **Filter Naming Mismatches**
   - Docs say "slugify" but code is "slug"
   - Docs say "json_encode" but code is "json"
   - Error Type: Docs example won't work without modification
   - User Impact: Users must guess the correct name

2. **@url() Returns Placeholder**
   - Documented as generating actual URLs
   - Implementation returns `{{ url_for(...) }}` pattern
   - Error Type: Partial URL generation
   - User Impact: URLs in rendered HTML may show template syntax instead of actual URLs

3. **@component/@slot/@props**
   - Implemented but not documented
   - Users accessing advanced patterns won't find guidance
   - Error Type: Undocumented feature; users may use incorrectly

### 🟡 LOW ISSUES (Documentation Only)

1. **@empty Directive**
   - Documented in table but no implementation examples
   - May work via codegen or may be missing

2. **Partially Implemented Features**
   - @render_field, @extends, @include only have external callbacks
   - May not work in all scenarios

---

## Part 5: Recommendations

### Immediate Actions Required

**Priority 1 - CRITICAL (Do Immediately)**
1. [ ] Remove or fix 14 documented filters that don't exist:
   - Either implement them OR
   - Remove from documentation and update Feature Parity section
   
2. [ ] Fix filter naming:
   - Change code from "slug" → "slugify" (or update docs)
   - Change code from "json" → "json_encode" (or update docs)
   
3. [ ] Document @render_field status:
   - Mark as "Not Recommended for Production" if not fully implemented
   - Or complete the implementation

4. [ ] Add 8 implemented but undocumented directives to docs:
   - @break, @continue, @super, @props, @messages, @flash, @status

### Short-term Actions

**Priority 2 - HIGH**
1. [ ] Implement missing widget form filters or clarify they're not supported
2. [ ] Implement missing utility filters or mark as deprecated
3. [ ] Document @component/@slot pattern with examples
4. [ ] Test @url() to verify it returns actual URLs
5. [ ] Add @empty directive handling to codegen

### Long-term Actions

**Priority 3 - MEDIUM**
1. [ ] Create feature parity matrix in documentation
2. [ ] Add "Implementation Status" column to all filter/directive tables
3. [ ] Create migration guide for users of legacy filters
4. [ ] Add filter/directive availability checks in templates

---

## Detailed Inconsistency Table

| Component | Type | Documented | Implemented | Status | Fix Priority |
|-----------|------|-----------|------------|--------|--------------|
| money | Filter | ✓ | ✗ | Missing | P1 |
| time_ago | Filter | ✓ | ✗ | Missing | P1 |
| slugify | Filter | ✓ | ✓ as "slug" | Name mismatch | P1 |
| mask | Filter | ✓ | ✗ | Missing | P1 |
| file_size | Filter | ✓ | ✗ | Missing | P1 |
| pluralize | Filter | ✓ | ✗ | Missing | P1 |
| title_case | Filter | ✓ | ✗ | Missing | P1 |
| default_if_none | Filter | ✓ | ✗ | Missing | P1 |
| json_encode | Filter | ✓ | ✓ as "json" | Name mismatch | P1 |
| add_class | Filter | ✓ | ✗ | Missing | P1 |
| attr | Filter | ✓ | ✗ | Missing | P1 |
| append_attr | Filter | ✓ | ✗ | Missing | P1 |
| remove_attr | Filter | ✓ | ✗ | Missing | P1 |
| field_type | Filter | ✓ | ✗ | Missing | P1 |
| eden_bg | Filter | ✓ | ✗ | Missing | P1 |
| eden_shadow | Filter | ✓ | ✗ | Missing | P1 |
| eden_text | Filter | ✓ | ✗ | Missing | P1 |
| @render_field | Directive | ✓ Extensive | ✓ Placeholder | Not functional | P1 |
| @component | Directive | ✓ Implied | ✓ Placeholder | Not functional | P2 |
| @props | Directive | ✗ | ✓ | Undocumented | P2 |
| @super | Directive | ✗ | ✓ | Undocumented | P2 |
| @messages | Directive | ✗ | ✓ | Undocumented | P2 |
| @flash | Directive | ✗ | ✓ | Undocumented | P2 |
| @status | Directive | ✗ | ✓ | Undocumented | P2 |
| @break | Directive | ✗ | ✓ | Undocumented | P2 |
| @continue | Directive | ✗ | ✓ | Undocumented | P2 |
| @url() | Directive | ✓ | ✓ Partial | Returns placeholder | P2 |
| @extends | Directive | ✓ | ✓ Partial | External callback only | P2 |
| @include | Directive | ✓ | ✓ Partial | External callback only | P2 |
| @route | Directive | ✗ | ✓ Stub | Undocumented stub | P3 |
| @empty | Directive | ✓ | ? | Unclear if working | P2 |

---

## Summary of Findings

### By Severity

| Severity | Count | Examples |
|----------|-------|----------|
| 🔴 CRITICAL (Will fail) | 14 | Widget filters, Design filters, money, time_ago |
| ⚠️ MEDIUM (May confuse) | 8 | Naming mismatches, @render_field stub, @url() partial |
| 🟡 LOW (Documentation) | 8 | Undocumented implemented features, @route stub |

### By Category

| Category | Issues |
|----------|--------|
| Missing Filters | 9 (money, time_ago, mask, file_size, pluralize, title_case, default_if_none, eden_bg, eden_shadow, eden_text) |
| Filter Name Mismatches | 2 (slugify/slug, json_encode/json) |
| Unimplemented Directives | 3 (@render_field fully, @component fully, @slot fully) |
| Partially Implemented Features | 3 (@extends, @include, @url) |
| Undocumented Implemented Features | 8 (@break, @continue, @super, @props, @messages, @flash, @status, @route) |

---

**Report Generated:** March 13, 2026  
**Total Inconsistencies Found:** 33  
**Critical Issues:** 14  
**Medium Issues:** 8  
**Low Issues:** 11
