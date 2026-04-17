"""
Complete example showing how to use all Django-inspired features in Eden.

This example demonstrates:
1. ModelConfig for model metadata
2. ChoiceField for enum-based fields
3. Custom Manager with QuerySet methods
4. ModelSchema for form validation
5. ControlPanel for admin interface

Run this example to see all features working together.
"""

from eden import Eden, Model, StringField, Request, render_template
from eden.schemas import ModelSchema
from eden.querysets import Manager
from eden.enums import ChoiceField, ChoiceEnum
from eden.models import ModelConfig
import uuid


# Initialize the app
app = Eden(title="Eden Django Features Demo", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///demo.db"


# ────────────────────────────────────────────────────────────────────────
# 1. ChoiceField Example
# ────────────────────────────────────────────────────────────────────────

class ArticleStatus(ChoiceEnum):
    """Article publication status."""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @property
    def display_name(self) -> str:
        return {
            "draft": "Draft",
            "review": "Under Review",
            "published": "Published",
            "archived": "Archived"
        }.get(self.value, self.name)


# ────────────────────────────────────────────────────────────────────────
# 2. Model with ModelConfig
# ────────────────────────────────────────────────────────────────────────

class Article(Model):
    """Blog article model with comprehensive configuration."""

    title: str = StringField(max_length=200)
    content: str = StringField()
    status: str = ChoiceField(choices=ArticleStatus, default=ArticleStatus.DRAFT)
    author_name: str = StringField(max_length=100)
    tags: str = StringField(default="")  # Comma-separated tags

    # ModelConfig - Django-style meta options
    class Meta:
        # Ordering
        ordering = ["-created_at"]

        # Display names
        verbose_name = "Article"
        verbose_name_plural = "Articles"

        # API configuration
        api_resource = True
        api_readonly_fields = ["id", "created_at", "updated_at"]
        api_required_fields = ["title", "status", "author_name"]
        api_exclude_fields = []  # Can exclude sensitive fields

        # Admin configuration
        admin_list_display = ["title", "status", "author_name", "created_at"]
        admin_list_display_links = ["title"]
        admin_list_filter = ["status", "created_at"]
        admin_search_fields = ["title", "content", "author_name", "tags"]
        admin_ordering = ["-created_at"]
        admin_list_per_page = 25
        admin_readonly_fields = ["id", "created_at", "updated_at"]
        admin_list_editable = ["status"]

        # Database options
        db_table = "articles"
        indexes = [
            {"fields": ["status"]},
            {"fields": ["author_name"]},
            {"fields": ["created_at", "status"], "unique": False}
        ]

        # Permissions
        permissions = [
            ("can_publish", "Can publish articles"),
            ("can_archive", "Can archive articles"),
        ]

        # Validation
        unique_together = [["title", "author_name"]]  # No duplicate titles per author


# ────────────────────────────────────────────────────────────────────────
# 3. Custom Manager with QuerySet Methods
# ────────────────────────────────────────────────────────────────────────

class ArticleManager(Manager):
    """Custom manager for articles with specialized query methods."""

    def published(self):
        """Get all published articles."""
        return self.filter(status=ArticleStatus.PUBLISHED.value)

    def by_author(self, author_name: str):
        """Get articles by specific author."""
        return self.filter(author_name=author_name)

    def drafts(self):
        """Get draft articles."""
        return self.filter(status=ArticleStatus.DRAFT.value)

    def recent(self, limit: int = 10):
        """Get most recent articles."""
        return self.order_by("-created_at")[:limit]

    async def get_popular_tags(self) -> list[str]:
        """Get most popular tags across all articles."""
        # This would be a more complex query in real implementation
        all_articles = await self.all()
        tag_counts = {}

        for article in all_articles:
            if article.tags:
                for tag in article.tags.split(","):
                    tag = tag.strip()
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by popularity
        return sorted(tag_counts.keys(), key=lambda x: tag_counts[x], reverse=True)


# Attach custom manager to model
Article.objects = ArticleManager(Article)


# ────────────────────────────────────────────────────────────────────────
# 4. ModelSchema for Forms
# ────────────────────────────────────────────────────────────────────────

class ArticleSchema(ModelSchema):
    """Form schema for article creation/editing."""

    class Meta:
        model = Article
        exclude_fields = ["id", "created_at", "updated_at"]  # Auto-managed fields
        read_only_fields = []  # All fields editable in forms
        required_fields = ["title", "status", "author_name"]  # Must be provided

    async def clean_title(self, value: str) -> str:
        """Custom validation for title field."""
        if len(value.strip()) < 5:
            raise ValueError("Title must be at least 5 characters long")
        return value.strip()

    async def clean_content(self, value: str) -> str:
        """Custom validation for content field."""
        if len(value.strip()) < 10:
            raise ValueError("Content must be at least 10 characters long")
        return value.strip()


# ────────────────────────────────────────────────────────────────────────
# 5. Admin Interface
# ────────────────────────────────────────────────────────────────────────

from eden.admin import admin, ModelAdmin

# Register the Article model with the admin
class ArticleAdmin(ModelAdmin):
    """Custom admin configuration for articles."""

    # Display configuration
    list_display = ["title", "status", "author_name", "created_at"]
    search_fields = ["title", "content", "author_name", "tags"]
    list_filter = ["status", "author_name"]

    # Pagination
    list_per_page = 25

    # Custom field labels (optional)
    field_labels = {
        "author_name": "Author",
        "created_at": "Published Date"
    }

admin.register(Article, ArticleAdmin)


# ────────────────────────────────────────────────────────────────────────
# Web Routes
# ────────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Homepage showing recent articles."""
    recent_articles = await Article.objects.recent(5)
    published_count = await Article.objects.published().count()

    return render_template("index.html", {
        "recent_articles": recent_articles,
        "published_count": published_count,
        "total_count": await Article.objects.count()
    })


@app.get("/articles")
async def article_list():
    """List all articles with filtering."""
    # Get query parameters
    status_filter = None  # Would come from request.query_params

    if status_filter:
        articles = await Article.objects.filter(status=status_filter).all()
    else:
        articles = await Article.objects.all()

    return render_template("articles.html", {
        "articles": articles,
        "status_choices": ArticleStatus.choices,
        "current_filter": status_filter
    })


@app.get("/articles/new")
async def new_article():
    """Show form to create new article."""
    schema = ArticleSchema()
    return render_template("article_form.html", {
        "schema": schema,
        "action": "create",
        "status_choices": ArticleStatus.choices
    })


@app.post("/articles")
async def create_article(request: Request):
    """Handle article creation."""
    form_data = await request.form()

    # Create schema with form data
    schema = ArticleSchema(
        title=form_data.get("title", ""),
        content=form_data.get("content", ""),
        status=form_data.get("status", ArticleStatus.DRAFT.value),
        author_name=form_data.get("author_name", ""),
        tags=form_data.get("tags", "")
    )

    # Validate
    if await schema.is_valid(dict(form_data)):
        # Save the article
        article = await schema.save()
        return render_template("article_created.html", {"article": article})
    else:
        # Show form with errors
        return render_template("article_form.html", {
            "schema": schema,
            "action": "create",
            "status_choices": ArticleStatus.choices,
            "errors": schema.errors
        })


@app.get("/articles/{article_id}")
async def view_article(article_id: str):
    """View a specific article."""
    try:
        article = await Article.objects.filter(id=article_id).first()
        if not article:
            return render_template("404.html", {"message": "Article not found"})

        return render_template("article_detail.html", {"article": article})
    except ValueError:
        return render_template("404.html", {"message": "Invalid article ID"})


@app.get("/authors/{author_name}")
async def author_articles(author_name: str):
    """Show all articles by a specific author."""
    articles = await Article.objects.by_author(author_name).all()
    author_stats = {
        "name": author_name,
        "article_count": len(articles),
        "published_count": len([a for a in articles if a.status == ArticleStatus.PUBLISHED.value])
    }

    return render_template("author_articles.html", {
        "author": author_stats,
        "articles": articles
    })


@app.get("/tags")
async def popular_tags():
    """Show popular tags."""
    tags = await Article.objects.get_popular_tags()
    return render_template("tags.html", {"tags": tags})


# ────────────────────────────────────────────────────────────────────────
# Admin Panel Routes
# ────────────────────────────────────────────────────────────────────────

# Mount the admin panel
app.mount_admin("/admin")


# ────────────────────────────────────────────────────────────────────────
# API Routes (using ModelConfig.api_resource)
# ────────────────────────────────────────────────────────────────────────

@app.get("/api/articles")
async def api_articles():
    """JSON API for articles."""
    articles = await Article.objects.all()

    # Convert to dict format
    article_data = []
    for article in articles:
        article_data.append({
            "id": str(article.id),
            "title": article.title,
            "status": article.status,
            "status_display": ArticleStatus.get_display_name(article.status),
            "author_name": article.author_name,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "tags": article.tags.split(",") if article.tags else []
        })

    return {"articles": article_data, "count": len(article_data)}


@app.post("/api/articles")
async def api_create_article(request: Request):
    """API endpoint to create articles."""
    data = await request.json()

    schema = ArticleSchema(**data)

    if await schema.is_valid(data):
        article = await schema.save()
        return {
            "success": True,
            "article": {
                "id": str(article.id),
                "title": article.title,
                "status": article.status
            }
        }
    else:
        return {"success": False, "errors": schema.errors}


# ────────────────────────────────────────────────────────────────────────
# Demo Data Creation
# ────────────────────────────────────────────────────────────────────────

@app.post("/demo-data")
async def create_demo_data():
    """Create sample articles for demonstration."""
    demo_articles = [
        {
            "title": "Getting Started with Eden Framework",
            "content": "Eden is a modern async Python web framework inspired by Django's productivity and FastAPI's performance...",
            "status": ArticleStatus.PUBLISHED.value,
            "author_name": "Eden Team",
            "tags": "eden, python, web framework, tutorial"
        },
        {
            "title": "Django-inspired Features in Eden",
            "content": "Learn about the Django-like features available in Eden: ModelConfig, ChoiceField, ControlPanel, and more...",
            "status": ArticleStatus.PUBLISHED.value,
            "author_name": "Developer",
            "tags": "django, eden, features, comparison"
        },
        {
            "title": "Async Database Operations",
            "content": "Eden provides full async support for database operations, making it perfect for high-performance applications...",
            "status": ArticleStatus.REVIEW.value,
            "author_name": "Async Expert",
            "tags": "async, database, performance, sql"
        },
        {
            "title": "Building Admin Interfaces",
            "content": "The ControlPanel feature makes it easy to create powerful admin interfaces with minimal code...",
            "status": ArticleStatus.DRAFT.value,
            "author_name": "UI Developer",
            "tags": "admin, ui, panel, interface"
        }
    ]

    created_articles = []
    for article_data in demo_articles:
        article = await Article.create(**article_data)
        created_articles.append(article)

    return {
        "message": f"Created {len(created_articles)} demo articles",
        "articles": [{"id": str(a.id), "title": a.title} for a in created_articles]
    }


# ────────────────────────────────────────────────────────────────────────
# Main Application
# ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting Eden Django Features Demo")
    print("📝 Features demonstrated:")
    print("  • ModelConfig - Django-style model metadata")
    print("  • ChoiceField - Enum-based field choices")
    print("  • Custom Manager - Enhanced QuerySet operations")
    print("  • ModelSchema - Form validation and processing")
    print("  • ControlPanel - Admin interface")
    print()
    print("🌐 Visit http://localhost:8000 for the main site")
    print("🔧 Visit http://localhost:8000/admin for the admin panel")
    print("📊 Visit http://localhost:8000/api/articles for the JSON API")
    print("🎯 POST to /demo-data to create sample articles")
    print()

    app.run()