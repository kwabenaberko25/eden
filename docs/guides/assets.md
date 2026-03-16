# Asset Pipeline 🛠️

Eden includes a lightweight but powerful asset pipeline for managing your CSS, JavaScript, and static files.

## Static Files

By default, any file placed in the `static/` directory at the root of your project is served by Eden.

### Template Usage
Use the `@static` directive to generate the correct URL for an asset.

```html
<link rel="stylesheet" href="@static('css/main.css')">
<script src="@static('js/app.js')"></script>
```

---

## The Build System

For production, you should bundle and version your assets to enable long-term caching and reduce payload sizes.

### Initializing Assets
```bash
eden assets init
```
This creates a `assets.json` configuration file.

### Building for Production
```bash
eden assets build --minify --hash
```
**What this does:**
1. **Minification**: Compresses CSS/JS.
2. **Hashing**: Appends a unique hash to filenames (e.g., `main.a1b2c3.css`) to break cache when content changes.
3. **Manifest**: Updates `assets.json` with the mapping from source name to hashed name.

---

## HTMX Integration

Eden is optimized for **HTMX**. You can include it via the built-in CDN helper or host it locally.

```html
<!-- Via CDN (Managed by Eden versioning) -->
@htmx_script

<!-- In your components -->
<button hx-post="/like" hx-swap="outerHTML">
    Like
</button>
```

---

## Customizing the Pipeline

You can extend the asset pipeline via the `eden.json` file:

```json
{
    "assets": {
        "source_dir": "assets",
        "output_dir": "dist/static",
        "compilers": {
            ".scss": "sass {input} {output}",
            ".ts": "esbuild {input} --bundle --outfile={output}"
        }
    }
}
```

---

## Best Practices

1. **Versioning**: Always use `--hash` in production.
2. **Compression**: Enable Gzip/Brotli on your production server (e.g., Nginx) even if minified.
3. **Organization**: Keep your raw assets in an `assets/` folder and only let the `build` command write to `static/`.

---

**Next Steps**: [Optional Extras](optional-extras.md)
