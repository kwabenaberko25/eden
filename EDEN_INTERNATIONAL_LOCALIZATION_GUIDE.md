# Eden Templating Engine - International & Localization Support

**Status:** ✅ Complete specification  
**Focus Countries:** Ghana, Nigeria, USA, UK, France, Germany, Japan, China  
**Currency Support:** 30+ currencies with symbols and ISO codes

---

## Ghana-Specific Examples

### Phone Numbers (Ghana)

```html
<!-- Local format -->
{{ contact.phone | phone }}
{{ "0248160391" | phone }}
→ "024 816 0391"

<!-- International format -->
{{ contact.phone | phone("GH") }}
{{ "0248160391" | phone("GH") }}
→ "+233 248 160 391"

<!-- Standard format (alternative) -->
{{ contact.phone | phone("GH-standard") }}
→ "024 816 0391"

<!-- Dashed format -->
{{ contact.phone | phone("dash") }}
→ "024-816-0391"

<!-- Different phone networks -->
<!-- MTN (0248...) → +233 24/25/26... -->
{{ "0248160391" | phone("GH") }}
→ "+233 248 160 391"

<!-- Vodafone (0207...) → +233 20... -->
{{ "0207123456" | phone("GH") }}
→ "+233 207 123 456"

<!-- Airtel (0209...) → +233 209... -->
{{ "0209654321" | phone("GH") }}
→ "+233 209 654 321"
```

### Currency (Ghana Cedi - GHS/¢)

```html
<!-- Basic formatting with cedi symbol -->
{{ price | currency("¢") }}
{{ 99.99 | currency("¢") }}
→ "¢99.99"

<!-- With 2 decimal places (standard) -->
{{ price | currency("¢", 2) }}
{{ 1234.567 | currency("¢", 2) }}
→ "¢1,234.57" (rounded)

<!-- Using ISO code -->
{{ price | currency("GHS", 2) }}
{{ 500 | currency("GHS", 2) }}
→ "GHS 500.00"

<!-- Ghana locale formatting -->
{{ price | currency("¢", 2, "gh_GH") }}
{{ 1234.56 | currency("¢", 2, "gh_GH") }}
→ "¢ 1,234.56"

<!-- Prices in form context -->
<div class="product">
    <h3>{{ product.name }}</h3>
    <p class="price">{{ product.price | currency("¢", 2) }}</p>
    
    <!-- With discount -->
    @if (product.discount_price) {
        <p class="original">{{ product.price | currency("¢", 2) }}</p>
        <p class="sale">{{ product.discount_price | currency("¢", 2) }}</p>
    }
</div>

<!-- Invoice example -->
<table class="invoice">
    @for (item in invoice.items) {
        <tr>
            <td>{{ item.name }}</td>
            <td style="text-align: right;">{{ item.quantity }}</td>
            <td style="text-align: right;">{{ item.unit_price | currency("¢", 2) }}</td>
            <td style="text-align: right;">{{ item.total | currency("¢", 2) }}</td>
        </tr>
    }
    <tr class="total">
        <td colspan="3">Total:</td>
        <td style="text-align: right;">{{ invoice.total | currency("¢", 2) }}</td>
    </tr>
</table>
```

---

## Multi-Country Examples

### Phone Numbers Across Countries

```html
<!-- Ghana -->
{{ "0248160391" | phone("GH") }} → "+233 248 160 391"

<!-- Nigeria -->
{{ "8012345678" | phone("NG") }} → "+234 801 2345 678"

<!-- USA -->
{{ "5551234567" | phone("US") }} → "+1 (555) 123-4567"

<!-- UK -->
{{ "2071838750" | phone("UK") }} → "+44 20 7183 8750"

<!-- France -->
{{ "156784512" | phone("FR") }} → "+33 1 5678 4512"

<!-- Germany -->
{{ "3089516018" | phone("DE") }} → "+49 30 8951 6018"

<!-- Japan -->
{{ "312345678" | phone("JP") }} → "+81 3 1234 5678"

<!-- China -->
{{ "1012345678" | phone("CN") }} → "+86 10 1234 5678"
```

### Currency Formatting Across Locales

```html
<!-- US Dollar -->
{{ 1234.56 | currency("$", 2) }}
→ "$1,234.56"

<!-- Euro (Germany) -->
{{ 1234.56 | currency("€", 2, "de_DE") }}
→ "1.234,56 €"

<!-- Euro (France) -->
{{ 1234.56 | currency("€", 2, "fr_FR") }}
→ "1 234,56 €"

<!-- British Pound -->
{{ 1234.56 | currency("£", 2) }}
→ "£1,234.56"

<!-- Japanese Yen (no decimals) -->
{{ 100000 | currency("¥", 0) }}
→ "¥100,000"

<!-- Indian Rupee -->
{{ 50000 | currency("₹", 2, "en_IN") }}
→ "₹50,000.00"

<!-- Philippine Peso -->
{{ 5000 | currency("₱", 2) }}
→ "₱5,000.00"
```

---

## Real-World Use Cases

### E-commerce Product Listing (Ghana)

```html
@extends("layouts/shop.html")

@block("content") {
    <div class="products">
        @for (product in products) {
            <div class="product-card">
                <h3>{{ product.name }}</h3>
                <p class="price">
                    {{ product.price | currency("¢", 2) }}
                </p>
                
                @if (product.contact_phone) {
                    <p class="contact">
                        Contact: {{ product.contact_phone | phone }}
                    </p>
                }
                
                @if (product.seller_phone) {
                    <a href="tel:{{ product.seller_phone | phone('raw') }}">
                        {{ product.seller_phone | phone }}
                    </a>
                }
            </div>
        }
    </div>
}
```

### Invoice/Receipt (Ghana)

```html
<div class="invoice">
    <h1>Invoice</h1>
    
    <div class="details">
        <p><strong>Date:</strong> {{ invoice.date | date("M d, Y") }}</p>
        <p><strong>Invoice #:</strong> {{ invoice.number }}</p>
        <p><strong>Customer Phone:</strong> {{ invoice.customer_phone | phone }}</p>
    </div>
    
    <table class="line-items">
        <thead>
            <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Amount</th>
            </tr>
        </thead>
        <tbody>
            @for (line in invoice.lines) {
                <tr>
                    <td>{{ line.description }}</td>
                    <td class="right">{{ line.quantity }}</td>
                    <td class="right">{{ line.unit_price | currency("¢", 2) }}</td>
                    <td class="right">{{ line.amount | currency("¢", 2) }}</td>
                </tr>
            }
        </tbody>
    </table>
    
    <div class="summary">
        <div class="row">
            <label>Subtotal:</label>
            <span>{{ invoice.subtotal | currency("¢", 2) }}</span>
        </div>
        <div class="row">
            <label>Tax ({{ invoice.tax_rate | format("{:.0%}") }}):</label>
            <span>{{ invoice.tax | currency("¢", 2) }}</span>
        </div>
        <div class="row total">
            <label>Total:</label>
            <span>{{ invoice.total | currency("¢", 2) }}</span>
        </div>
    </div>
    
    <div class="terms">
        <p>Thank you for your business!</p>
    </div>
</div>
```

### Contact Form (Multi-country)

```html
<form method="POST" action="@url('contacts.store')">
    @csrf()
    
    <div class="form-group">
        <label>Country</label>
        <select name="country">
            <option value="">Select Country</option>
            <option value="GH">Ghana</option>
            <option value="NG">Nigeria</option>
            <option value="US">USA</option>
            <option value="UK">UK</option>
            <option value="FR">France</option>
        </select>
    </div>
    
    <div class="form-group">
        <label>Phone Number</label>
        <input 
            type="tel" 
            name="phone" 
            placeholder="e.g., 024 816 0391"
            value="@old('phone', '')"
        >
        
        <!-- Show formatted example based on country -->
        <small id="phone-example"></small>
    </div>
    
    <div class="form-group">
        <label>Amount (in local currency)</label>
        <input 
            type="number" 
            name="amount"
            step="0.01"
            value="@old('amount', '')"
        >
        <small id="currency-example"></small>
    </div>
    
    <button type="submit">Submit</button>
</form>

<!-- JavaScript to update examples -->
<script>
document.querySelector('[name="country"]').addEventListener('change', function(e) {
    const country = e.target.value;
    const examples = {
        'GH': '024 816 0391',
        'NG': '801 234 5678',
        'US': '(555) 123-4567',
        'UK': '020 7183 8750',
        'FR': '1 45 67 89 01'
    };
    document.getElementById('phone-example').textContent = 
        'Example: ' + (examples[country] || '');
});
</script>
```

### Dashboard/Report (Multi-currency)

```html
@extends("layouts/admin.html")

@block("content") {
    <div class="dashboard">
        <h1>Sales Dashboard</h1>
        
        <div class="metrics">
            @for (region in regions) {
                <div class="metric">
                    <h3>{{ region.name }}</h3>
                    <p class="amount">
                        {{ region.revenue | currency(region.currency_symbol, 2) }}
                    </p>
                    <p class="small">
                        @for (contact in region.contacts) {
                            <span>{{ contact.phone | phone(region.country_code) }}</span><br>
                        }
                    </p>
                </div>
            }
        </div>
        
        <table class="sales">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Seller</th>
                    <th>Phone</th>
                    <th>Amount</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                @for (sale in sales) {
                    <tr>
                        <td>{{ sale.date | date("M d, Y") }}</td>
                        <td>{{ sale.seller_name }}</td>
                        <td>{{ sale.seller_phone | phone(sale.country) }}</td>
                        <td class="amount">
                            {{ sale.amount | currency(sale.currency, 2) }}
                        </td>
                        <td>
                            <span class="badge badge-{{ sale.status }}">
                                {{ sale.status | capitalize }}
                            </span>
                        </td>
                    </tr>
                }
            </tbody>
        </table>
    </div>
}
```

---

## Implementation Details

### Phone Filter Algorithm

The `phone` filter:
1. Detects country from parameter
2. Strips all non-digit characters
3. Identifies phone component (country code, area code, local)
4. Formats according to country-specific rules
5. Handles missing digits gracefully

### Currency Filter Algorithm

The `currency` filter:
1. Converts input to float
2. Rounds to specified decimals (default: 2)
3. Formats with thousands separator
4. Applies currency symbol or code
5. Respects locale for decimal/thousands separator

---

## Testing Strategy (International)

### Phone Filter Tests (30+ tests)
- Ghana: Local format, international, variants (MTN, Vodafone, Airtel)
- Nigeria: Various formats and area codes
- USA: Standard (555) 123-4567 format
- UK: London, Manchester, Birmingham formats
- France: Paris and regional codes
- Germany: Multiple area codes
- Japan: Tokyo and regional codes
- China: Beijing and mobile prefixes
- Edge cases: Invalid digits, partial numbers, special chars

### Currency Filter Tests (40+ tests)
- Base currencies: USD, EUR, GBP, JPY, CNY
- Local currencies: GHS, NGN, PHP, INR
- Decimal handling: 0, 2, 3 decimals
- Locale formatting: US, EU, Asia formats
- Symbols: $, €, £, ¥, ¢, ₹, ₱, ₩
- Large numbers: Thousands separators
- Edge cases: Zero, negative, very large/small

---

## Supported Locales

| Locale | Country | Currency | Format |
|--------|---------|----------|--------|
| gh_GH | Ghana | GHS (¢) | 1,234.56 GHS |
| en_NG | Nigeria | NGN | ₦1,234.56 |
| en_US | USA | USD ($) | $1,234.56 |
| en_GB | UK | GBP (£) | £1,234.56 |
| fr_FR | France | EUR (€) | 1 234,56 € |
| de_DE | Germany | EUR (€) | 1.234,56 € |
| ja_JP | Japan | JPY (¥) | ¥1,234 |
| zh_CN | China | CNY (¥) | ¥1,234.56 |
| en_PH | Philippines | PHP (₱) | ₱1,234.56 |
| en_IN | India | INR (₹) | ₹1,234.56 |

---

## See Also

- [EDEN_BUILTIN_FILTERS_REFERENCE.md](EDEN_BUILTIN_FILTERS_REFERENCE.md) — Complete filter documentation
- [EDEN_SYNTAX_STANDARD_FINAL.md](EDEN_SYNTAX_STANDARD_FINAL.md) — Syntax reference with examples
- [EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md](EDEN_TEMPLATING_ENGINE_IMPLEMENTATION_PLAN.md) — Implementation details
