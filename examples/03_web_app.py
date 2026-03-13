"""
03_web_app.py — Web App with HTML Templates & Forms

Add HTML templating and form handling to build a web application
with both server-side rendering and data persistence.

Run:
    python examples/03_web_app.py

Then visit http://localhost:8000 in your browser.
"""

from eden import Eden, Model, StringField, Request, render_template

app = Eden(title="Web App", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///notes.db"

# ────────────────────────────────────────────────────────────────────────
# Model
# ────────────────────────────────────────────────────────────────────────

class Note(Model):
    """A simple note."""
    title = StringField(max_length=200)
    content = StringField(default="")


# ────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Show all notes."""
    notes = await Note.all()
    return render_template("notes_list.html", {"notes": notes})


@app.get("/notes/new")
async def new_note():
    """Show form to create a note."""
    return render_template("note_form.html", {"note": None})


@app.post("/notes")
async def create_note(request: Request):
    """Handle form submission to create note."""
    form = await request.form()
    note = await Note.create(
        title=form.get("title", "Untitled"),
        content=form.get("content", "")
    )
    return {"redirect": f"/notes/{note.id}"}


@app.get("/notes/{note_id:int}")
async def view_note(note_id: int):
    """View a single note."""
    note = await Note.get(note_id)
    return render_template("note_detail.html", {"note": note})


@app.get("/notes/{note_id:int}/edit")
async def edit_note(note_id: int):
    """Show form to edit a note."""
    note = await Note.get(note_id)
    return render_template("note_form.html", {"note": note})


if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)

# What you learned:
#   - render_template() for HTML responses
#   - Form handling: await request.form()
#   - Template variables: {"key": value}
#   - Web app flow: list → detail → edit → update
#
# Next: See 04_authentication.py to add login and user accounts
