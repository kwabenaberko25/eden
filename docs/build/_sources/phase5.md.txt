# Phase 5: Reactive Interactivity (HTMX) ⚡

The modern web is reactive. In this phase, we master the integration between **Eden** and **HTMX**—the power to update your UI dynamically without writing a single line of custom JavaScript.

---

## 🛰️ Hypermedia Systems

Eden is optimized for hypermedia. It understands **HTMX fragments**, allowing you to render only the parts of a page that actually changed.

### 1. The @fragment Directive

The `@fragment` directive allows you to define a sub-section of a template that can be returned independently.

```html
@block('content') {
    <div id="sector-status">
        @fragment('sector-status') {
            <p>Current Load: {{ load_percentage }}%</p>
            <button hx-get="/sectors/{{ sector.slug }}/refresh" 
                    hx-target="#sector-status">
                Refresh Pulse
            </button>
        }
    </div>
}
```

When you request this route via HTMX, Eden will automatically return *only* the content inside the `@fragment('sector-status')` block if requested.

---

## 🛡️ HTMX Guards

Sometimes you want content to appear *only* during an HTMX request, or *only* during a full page load.

### 1. @htmx and @non_htmx

```html
@non_htmx {
    <nav>Full Site Navigation Sidebar</nav>
}

@htmx {
    <div class="toast">Sector Telemetry Refreshed!</div>
}
```

---

## 🎨 Professional Indicators

Always provide feedback to your users during async operations.

```html
<button hx-post="/sector/deploy" 
        hx-indicator="#deploy-spinner">
    Deploy Drone
</button>
<div id="deploy-spinner" class="htmx-indicator">
    🛰️ Deploying...
</div>
```

---

## ✅ Verification

To verify your Reactive Interactivity:

1. **Test Fragments**: Verify that `hx-get` correctly swaps the fragment content.
2. **Test Guards**: Ensure the `@non_htmx` content does not appear in Eden partial responses.
3. **Test Indicators**: Verify that loaders appear during server communication.

If your UI feels fluid and reactive with zero JavaScript, your HTMX integration is **100% Verified**. You are ready for **Phase 6: Input Governance (Forms)**.

