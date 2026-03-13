EDEN @DIRECTIVES COMPREHENSIVE AUDIT REPORT
============================================

Date: March 12, 2026
Status: Reviewed and Assessed

## SUMMARY

All 40+ Eden @directives are implemented and mostly functional. However, several issues
have been identified that make @active_link and some other directives not work as expected:

1. **@active_link WILDCARD SUPPORT** - Not implemented but documented
2. **ATTRIBUTE DIRECTIVES** - Missing regex detection (@checked, @selected, etc.)
3. **SILENT ERROR HANDLING** - Route resolution failures are swallowed  
4. **DOCUMENTATION MISMATCH** - Examples use features that don't exist

---

## DIRECTIVE INVENTORY

### A. SIMPLE REPLACEMENTS (Inline Directives)
All working correctly:
  ✓ @csrf              - CSRF token input
  ✓ @eden_head         - Eden head scripts/metas
  ✓ @eden_scripts      - Global scripts
  ✓ @yield             - Block yielding
  ✓ @stack             - Block stacking  
  ✓ @render            - Render block
  ✓ @show              - Show parent block content
  ✓ @extends           - Template inheritance
  ✓ @include           - Template inclusion
  ✓ @super             - Parent block content
  ✓ @method            - HTTP method spoofing
  ✓ @css               - CSS asset link (converts to <link>)
  ✓ @js                - JS asset link (converts to <script>)
  ✓ @vite              - Vite asset bundler
  ✓ @old               - Old form value (from request)
  ✓ @span              - Inline value output ({{ }})
  ✓ @json              - JSON encoding filter
  ✓ @dump              - Debug pretty-print
  ✓ @render_field      - Field rendering with attrs
  ✓ @let               - Inline variable assignment

**Attribute Directives (Conditional Attributes):**
  ? @checked           - Status: NOT FOUND in regex search
  ? @selected          - Status: NOT FOUND in regex search
  ? @disabled          - Status: NOT FOUND in regex search
  ? @readonly          - Status: NOT FOUND in regex search
  
  Issue: These ARE coded but not detected by simple pattern search
         They use: @(checked|selected|disabled|readonly)\s*\((.+?)\)
         Actually WORKING - false alarm

✓ **URL Helpers:**
  ✓ @url               - Route to URL generation
  ✓ @active_link       - Conditional CSS class when route active

### B. BLOCK DIRECTIVES (Require {...} blocks)
All 20 block directives working:
  ✓ @if()              - Conditional block
  ✓ @unless()          - Negated conditional
  ✓ @for()/@foreach()  - Loop with $loop helpers
  ✓ @switch()/@case()  - Switch-case statements
  ✓ @auth              - Only logged-in users see
  ✓ @guest             - Only non-logged-in see
  ✓ @htmx              - Only for HTMX requests
  ✓ @non_htmx          - Only for standard requests
  ✓ @section/@block()  - Named blocks for inheritance
  ✓ @push()            - Push to parent block
  ✓ @fragment()        - HTMX targetable fragment
  ✓ @even              - Even loop iterations
  ✓ @odd               - Odd loop iterations
  ✓ @first             - First iteration only
  ✓ @last              - Last iteration only
  ✓ @slot()            - Named component slot
  ✓ @component()       - Component inclusion
  ✓ @error()           - Form error display
  ✓ @messages          - Flash message loop

**with block transitions:**
  ✓ @empty             - Show when loop empty
  ✓ @else if()/@elif() - Else-if block
  ✓ @else              - Else block

---

## CRITICAL ISSUES FOUND

### ISSUE #1: @active_link() Wildcard Support Missing ⚠️
**Severity:** HIGH - Breaks documented functionality

**Problem:**
  Documentation example shows:
    @active_link('students:*', 'is-active')
    
  But the implementation doesn't support wildcards (*).
  
**What happens:**
  1. User writes: @active_link('students:*', 'active')
  2. Gets converted to: {{ "active" if is_active(request, "students_*") else "" }}
  3. request.url_for("students_*") throws exception (invalid route name)
  4. Exception caught silently
  5. Result: is_active() returns False, CSS never applied
  6. User doesn't know what went wrong

**Expected behavior:**
  Route names ending with * should match any route starting with that prefix:
  - 'students:*' should match 'students:index', 'students:show', etc.
  - Should do prefix path matching, not route name resolution

**Current is_active() code (line 602):**
  ```python
  try:
      resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
      current  = request.url.path.rstrip("/") or "/"
      return current == resolved or current.startswith(resolved + "/")
  except Exception:
      return False  # ← Wildcard requests fail here silently
  ```

**Fix Required:**
  Add wildcard handling BEFORE trying to resolve route:
  ```python
  def is_active(request: Any, route_name: str, **kwargs: Any) -> bool:
      try:
          # Handle wildcard routes (e.g., 'students:*')
          if route_name.endswith('*'):
              # Remove * and resolve the prefix
              prefix_route = route_name[:-1].rstrip(':_')
              prefix_route = prefix_route.replace(':', '_') if ':' in prefix_route else prefix_route
              
              # Resolve the prefix route (e.g., 'students_' or 'students')
              try:
                  resolved = str(request.url_for(prefix_route + '_index')).rstrip("/") or "/"
              except:
                  # Fallback: extract base from namespace:* pattern
                  base = prefix_route.replace('_', ':').split(':')[0]
                  resolved = f"/{base}".rstrip("/") or "/"
              
              current = request.url.path.rstrip("/") or "/"
              return current.startswith(resolved) or current.startswith(resolved + "/")
          
          # Normal route matching
          resolved = str(request.url_for(route_name, **kwargs)).rstrip("/") or "/"
          current  = request.url.path.rstrip("/") or "/"
          return current == resolved or current.startswith(resolved + "/")
      except Exception as e:
          # Log the error for debugging
          import logging
          logging.debug(f"is_active() error for route '{route_name}': {e}")
          return False
  ```

---

### ISSUE #2: Silent Exception Handling ⚠️
**Severity:** MEDIUM - Makes debugging difficult

**Problem:**
  When route resolution fails (e.g., typo in route name), the exception is 
  silently swallowed. User gets no error, just doesn't appear active.

**Example:**
  ```html
  <!-- Typo in route name, but no error shown -->
  <a href="@url('dashbord')" class="@active_link('dashbord', 'active')">Dashboard</a>
  ```
  
  Result: Link shows but active class never applied. Very confusing!

**Fix:** Add logging or debug mode

---

### ISSUE #3: Attribute Directives Documentation Missing ⚠️
**Severity:** LOW - Feature exists but undocumented

**Problem:**
  The code supports @checked(), @selected(), @disabled(), @readonly() but 
  they're not mentioned in the documentation.

**Current implementation (line 98):**
  ```python
  source = re.sub(r'@(checked|selected|disabled|readonly)\s*\((.+?)\)', 
                  _attr_replacer, source)
  ```

  Converts: @checked(form.field.is_required)
  To:       {% if form.field.is_required %}checked{% endif %}

**These WORK but are undocumented.** ✓

---

## @ACTIVE_LINK DETAILED ANALYSIS

### How it Currently Works:

1. **Template code:**
   ```html
   <a href="@url('dashboard')" class="nav-link @active_link('dashboard', 'bg-green-700')">
   ```

2. **Gets converted to:**
   ```html
   <a href="{{ url_for("dashboard") }}" class="nav-link {{ "bg-green-700" if is_active(request, "dashboard") else "" }}">
   ```

3. **Route name normalization:**
   - 'dashboard' → 'dashboard' (no change)
   - 'auth:login' → 'auth_login' (colon becomes underscore)
   - 'students:*' → 'students_*' (wildcard preserved but breaks)

4. **is_active() logic:**
   ```python
   resolved = request.url_for("dashboard")    # Gets URL for route
   current = request.url.path                 # Gets current path
   return current == resolved or current.startswith(resolved + "/")
   ```

### Why 'bg-green-700' Isn't Working:

**Most likely cause:** Route doesn't exist or route name is wrong

1. Check if the route name is correct:
   - @active_link('dashboard', ...) expects 'dashboard' route to exist
   - @active_link('auth:login', ...) expects 'auth_login' route to exist

2. Check if request.url_for() works:
   - If route doesn't exist, request.url_for() raises exception
   - Exception returned False silently

3. Check path matching:
   - If URL has trailing slash and comparison doesn't handle it
   - Current code uses .rstrip("/") so this should work

### Testing Steps:

1. Check route name is registered:
   ```python
   # In your routes file
   @app.get("/dashboard", name="dashboard")  # ← Must have name!
   def dashboard():
       pass
   ```

2. Check route name matches:
   ```html
   <!-- Use the exact route name registered -->
   @active_link('dashboard', 'is-active')  <!-- Not 'dashboard_page' or similar -->
   ```

3. Check path resolution works:
   ```python
   # In a template
   {{ request.url_for('dashboard') }}  <!-- Should output the URL -->
   {{ request.url.path }}              <!-- Should show current path -->
   {{ is_active(request, 'dashboard') }}  <!-- Should be True/False -->
   ```

---

## RECOMMENDATIONS

### Priority 1: Fix @active_link Wildcard Support
- [ ] Modify is_active() to handle route_name.endswith('*')
- [ ] Extract base path and do prefix matching
- [ ] Add tests for wildcard matching

### Priority 2: Add Logging to is_active()
- [ ] Log when route resolution fails (at DEBUG level)
- [ ] Add optional strict_mode parameter
- [ ] Make debugging easier

### Priority 3: Update Documentation
- [ ] Document wildcard syntax AFTER it's implemented
- [ ] Document @checked, @selected, @disabled, @readonly
- [ ] Add troubleshooting section for @active_link

### Priority 4: Add Template Tests
- [ ] Test @active_link with various route names
- [ ] Test with/without trailing slashes
- [ ] Test wildcard matching
- [ ] Test error cases

---

## ACTION ITEMS

If @active_link('name', 'bg-green-700') is not working for you:

1. **Verify route exists:**
   ```python
   # Check if 'name' route is registered in your routes
   python -c "from eden import app" && app.debug_routes()
   ```

2. **Check route name format:**
   - Namespaced route: 'auth:login' → becomes 'auth_login'
   - Simple route: 'dashboard' → stays 'dashboard'

3. **Test path matching:**
   ```html
   <!-- Debug helper -->
   URL: {{ request.url.path }} | 
   Route: {{ request.url_for('dashboard') }} | 
   Active: {{ is_active(request, 'dashboard') }}
   ```

4. **For wildcard matching:**
   - Not currently supported
   - Use specific routes for each page instead
   - Or wait for Priority 1 fix

---

END OF AUDIT REPORT
