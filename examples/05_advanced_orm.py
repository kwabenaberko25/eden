"""
05_advanced_orm.py — Relationships, Queries, and Transactions

Master ORM with relationships, advanced queries, aggregations,
and transactions.

Run:
    python examples/05_advanced_orm.py
"""

from eden import Eden, Model, StringField, IntField, ForeignKeyField, Q, F

app = Eden(title="Advanced ORM", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///blog.db"


class Author(Model):
    """Blog author."""
    name = StringField(max_length=200)
    email = StringField()


class Post(Model):
    """Blog post with author."""
    title = StringField(max_length=200)
    content = StringField()
    views = IntField(default=0)
    author_id = ForeignKeyField(Author)


@app.get("/posts")
async def list_posts():
    """Get all posts with related authors (eager loading)."""
    posts = await Post.select().prefetch_related("author").all()
    return {"posts": posts}


@app.get("/posts/popular")
async def popular_posts():
    """Get top 5 posts by view count."""
    posts = await Post.select().order_by("-views").limit(5).all()
    return {"posts": posts}


@app.post("/posts/{post_id:int}/view")
async def increment_views(post_id: int):
    """Increment view counter for a post."""
    post = await Post.get(post_id)
    post.views = F("views") + 1
    await post.save()
    return {"views": post.views}


@app.get("/authors/{author_id:int}/posts")
async def author_posts(author_id: int):
    """Get all posts by an author."""
    posts = await Post.filter(author_id=author_id).all()
    return {"posts": posts}


if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)

# What you learned:
#   - ForeignKeyField for relationships
#   - prefetch_related() for eager loading
#   - order_by() and limit() for queries
#   - F() for field references in updates
#   - Q() for complex queries (see docs)
#
# Next: See 06_multi_tenant.py for row-level security
