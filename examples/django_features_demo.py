"""
Complete example demonstrating all Django-inspired features in Eden.
Run with: python examples/django_features_demo.py
"""

from eden import Eden, Model, StringField, TextField, Request
from eden.panel import ControlPanel, BasePanel, PanelConfig
from eden.schemas import ModelSchema
from eden.querysets import Manager
from eden.enums import ChoiceField, ChoiceEnum
from eden.models import ModelConfig
from datetime import datetime
import uuid

app = Eden(
    title="Django Features Demo",
    debug=True,
    secret_key="demo-secret-key"
)

# ────────────────────────────────────────────────────────────────────────
# Enums (ChoiceField)
# ────────────────────────────────────────────────────────────────────────

class ArticleStatus(ChoiceEnum):
    """Article publication status."""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @property
    def display_name(self) -> str:
        names = {
            "draft": "Draft",
            "review": "Under Review",
            "published": "Published",
            "archived": "Archived",
        }
        return names.get(self.value, self.name)


class UserRole(ChoiceEnum):
    """User roles."""
    ADMIN = "admin"
    EDITOR = "editor"
    AUTHOR = "author"

    @property
    def display_name(self) -> str:
        return self.value.title()


# ────────────────────────────────────────────────────────────────────────
# Models with ModelConfig
# ────────────────────────────────────────────────────────────────────────

class User(Model):
    """User model with role-based access."""
    username = StringField(max_length=50, unique=True)
    email = StringField(max_length=255, unique=True)
    role = ChoiceField(choices=UserRole, default=UserRole.AUTHOR)
    is_active = StringField(max_length=5, default="true")  # Simplified boolean

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

        # API configuration
        api_resource = True
        api_readonly_fields = ["id"]
        api_required_fields = ["username", "email"]
        api_exclude_fields = []

        # Admin configuration
        admin_list_display = ["username", "email", "role", "is_active"]
        admin_list_filter = ["role", "is_active"]
        admin_search_fields = ["username", "email"]
        admin_ordering = ["username"]
        admin_list_per_page = 20

        # Database configuration
        db_table = "users"
        indexes = [
            {"fields": ["email"]},
            {"fields": ["role"]},
        ]

        # Validation
        unique_together = [["username", "email"]]


class Article(Model):
    """Article model with all features."""
    title = StringField(max_length=200)
    slug = StringField(max_length=200, unique=True)
    content = TextField()
    excerpt = TextField(default="")
    status = ChoiceField(choices=ArticleStatus, default=ArticleStatus.DRAFT)
    author_id = StringField(max_length=36)  # UUID reference
    word_count = StringField(max_length=10, default="0")
    published_at = StringField(max_length=30)  # ISO datetime string

    # Custom manager
    objects = ArticleManager()

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-published_at", "-created_at"]

        # API configuration
        api_resource = True
        api_readonly_fields = ["id", "word_count"]
        api_required_fields = ["title", "content", "author_id"]
        api_nested_fields = ["author"]  # Would expand to full author object

        # Admin configuration
        admin_list_display = ["title", "status", "author_name", "word_count", "published_at"]
        admin_list_filter = ["status", "published_at"]
        admin_search_fields = ["title", "content", "slug"]
        admin_ordering = ["-published_at"]
        admin_list_editable = ["status"]
        admin_date_hierarchy = "published_at"

        # Database configuration
        db_table = "articles"
        indexes = [
            {"fields": ["slug"]},
            {"fields": ["status"]},
            {"fields": ["author_id"]},
            {"fields": ["published_at"]},
        ]


# ────────────────────────────────────────────────────────────────────────
# Managers (QuerySet)
# ────────────────────────────────────────────────────────────────────────

class ArticleManager(Manager):
    """Custom manager for articles with business logic."""

    def published(self):
        """Get published articles."""
        return self.filter(status=ArticleStatus.PUBLISHED.value)

    def drafts(self):
        """Get draft articles."""
        return self.filter(status=ArticleStatus.DRAFT.value)

    def by_author(self, author_id: str):
        """Get articles by author."""
        return self.filter(author_id=author_id)

    def recent(self, days: int = 7):
        """Get recently published articles."""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        return self.filter(published_at__gte=cutoff.isoformat())

    async def with_author_stats(self):
        """Get articles with author statistics."""
        # This would be a more complex query in real implementation
        articles = await self.all()
        # Add computed fields
        for article in articles:
            article.author_stats = f"Author: {article.author_id}"
        return articles

    async def publish_draft(self, article_id: str):
        """Publish a draft article."""
        article = await self.filter(id=article_id).first()
        if article and article.status == ArticleStatus.DRAFT.value:
            article.status = ArticleStatus.PUBLISHED.value
            article.published_at = datetime.now().isoformat()
            await article.save()
            return article
        return None


# ────────────────────────────────────────────────────────────────────────
# Schemas (ModelSchema)
# ────────────────────────────────────────────────────────────────────────

class UserSchema(ModelSchema):
    """Schema for user management."""

    async def clean_username(self, value: str) -> str:
        """Validate username."""
        if len(value) < 3:
            from eden.schemas import ValidationError
            raise ValidationError("Username must be at least 3 characters")
        return value.lower()

    async def clean_email(self, value: str) -> str:
        """Validate email."""
        if "@" not in value:
            from eden.schemas import ValidationError
            raise ValidationError("Invalid email address")
        return value.lower()

    class Meta:
        model = User
        exclude_fields = []
        read_only_fields = ["id"]
        required_fields = ["username", "email", "role"]


class ArticleSchema(ModelSchema):
    """Schema for article management."""

    async def clean_title(self, value: str) -> str:
        """Validate and clean title."""
        if len(value) < 5:
            from eden.schemas import ValidationError
            raise ValidationError("Title must be at least 5 characters")
        return value.strip()

    async def clean_slug(self, value: str) -> str:
        """Generate slug from title if not provided."""
        if not value and hasattr(self, 'title'):
            import re
            value = re.sub(r'[^\w\s-]', '', self.title).strip().lower()
            value = re.sub(r'[-\s]+', '-', value)
        return value

    async def clean_content(self, value: str) -> str:
        """Clean content and update word count."""
        cleaned = value.strip()
        self.word_count = str(len(cleaned.split()))
        return cleaned

    class Meta:
        model = Article
        exclude_fields = []
        read_only_fields = ["id", "word_count"]
        required_fields = ["title", "content", "author_id"]


# ────────────────────────────────────────────────────────────────────────
# Admin Panels (ControlPanel)
# ────────────────────────────────────────────────────────────────────────

class UserPanel(BasePanel):
    """Admin panel for users."""
    display_fields = ["username", "email", "role", "is_active"]
    search_fields = ["username", "email"]
    filter_fields = ["role", "is_active"]
    ordering = ["username"]

    async def get_queryset(self, request):
        """Custom queryset with role-based filtering."""
        qs = User.objects.all()
        # In a real app, filter based on current user permissions
        return qs


class ArticlePanel(BasePanel):
    """Admin panel for articles."""
    display_fields = ["title", "status", "author_name", "word_count", "published_at"]
    search_fields = ["title", "content", "slug"]
    filter_fields = ["status"]
    ordering = ["-published_at"]
    list_per_page = 25

    async def get_queryset(self, request):
        """Custom queryset for articles."""
        return Article.objects.all()

    async def author_name(self, obj) -> str:
        """Display author name instead of ID."""
        # In a real app, this would join with User table
        return f"User {obj.author_id[:8]}"

    async def word_count(self, obj) -> int:
        """Display word count."""
        return int(obj.word_count or 0)


# ────────────────────────────────────────────────────────────────────────
# Setup Admin Interface
# ────────────────────────────────────────────────────────────────────────

admin_config = PanelConfig(
    title="Django Features Demo - Admin",
    theme="light",
    auth_required=False,  # Disabled for demo
    items_per_page=20,
    enable_realtime=True,
    enable_export=True,
    enable_bulk_actions=True,
    custom_css="/static/admin.css",
    custom_js="/static/admin.js"
)

admin_panel = ControlPanel(admin_config)
admin_panel.register(User)(UserPanel)
admin_panel.register(Article)(ArticlePanel)


# ────────────────────────────────────────────────────────────────────────
# API Routes
# ────────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Home page with feature overview."""
    return {
        "message": "Eden Django Features Demo",
        "features": [
            "ControlPanel - Admin Interface",
            "ModelSchema - Form Validation",
            "QuerySet Managers - Enhanced Queries",
            "ChoiceField - Enum Validation",
            "ModelConfig - Model Metadata"
        ],
        "endpoints": {
            "admin": "/admin",
            "api_users": "/api/users",
            "api_articles": "/api/articles",
            "docs": "/docs"
        }
    }


@app.get("/api/users")
async def list_users():
    """List all users."""
    users = await User.objects.all()
    return {"users": users, "count": len(users)}


@app.post("/api/users")
async def create_user(request: Request):
    """Create a new user."""
    data = await request.json()
    schema = UserSchema(**data)

    if await schema.is_valid(data):
        user = await schema.save()
        return {"user": user, "message": "User created successfully"}
    else:
        return {"errors": schema.errors, "message": "Validation failed"}


@app.get("/api/articles")
async def list_articles(status: str = None):
    """List articles with optional status filter."""
    if status:
        articles = await Article.objects.filter(status=status).all()
    else:
        articles = await Article.objects.all()

    return {"articles": articles, "count": len(articles)}


@app.post("/api/articles")
async def create_article(request: Request):
    """Create a new article."""
    data = await request.json()
    schema = ArticleSchema(**data)

    if await schema.is_valid(data):
        article = await schema.save()
        return {"article": article, "message": "Article created successfully"}
    else:
        return {"errors": schema.errors, "message": "Validation failed"}


@app.get("/api/articles/published")
async def published_articles():
    """Get published articles."""
    articles = await Article.objects.published().all()
    return {"articles": articles, "count": len(articles)}


@app.get("/api/articles/recent")
async def recent_articles(days: int = 7):
    """Get recently published articles."""
    articles = await Article.objects.recent(days).all()
    return {"articles": articles, "days": days}


@app.put("/api/articles/{article_id}/publish")
async def publish_article(article_id: str):
    """Publish a draft article."""
    article = await Article.objects.publish_draft(article_id)
    if article:
        return {"article": article, "message": "Article published successfully"}
    else:
        return {"error": "Article not found or not a draft", "status_code": 404}


@app.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    user_count = await User.objects.count()
    article_count = await Article.objects.count()
    published_count = await Article.objects.published().count()

    return {
        "stats": {
            "users": user_count,
            "articles": article_count,
            "published_articles": published_count
        }
    }


# ────────────────────────────────────────────────────────────────────────
# Admin Routes
# ────────────────────────────────────────────────────────────────────────

@app.route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def admin_handler(request: Request):
    """Handle admin panel routes."""
    return await admin_panel.handle_request(request)


# ────────────────────────────────────────────────────────────────────────
# Demo Data Setup
# ────────────────────────────────────────────────────────────────────────

@app.post("/setup-demo-data")
async def setup_demo_data():
    """Setup demo data for testing."""

    # Create demo users
    users_data = [
        {"username": "admin", "email": "admin@example.com", "role": UserRole.ADMIN.value},
        {"username": "editor", "email": "editor@example.com", "role": UserRole.EDITOR.value},
        {"username": "author", "email": "author@example.com", "role": UserRole.AUTHOR.value},
    ]

    created_users = []
    for user_data in users_data:
        schema = UserSchema(**user_data)
        if await schema.is_valid(user_data):
            user = await schema.save()
            created_users.append(user)

    # Create demo articles
    articles_data = [
        {
            "title": "Getting Started with Eden Framework",
            "content": "Eden is a modern async Python web framework...",
            "status": ArticleStatus.PUBLISHED.value,
            "author_id": str(created_users[0].id) if created_users else str(uuid.uuid4()),
            "slug": "getting-started-eden"
        },
        {
            "title": "Django-inspired Features in Eden",
            "content": "Eden now supports many Django-like features...",
            "status": ArticleStatus.PUBLISHED.value,
            "author_id": str(created_users[1].id) if len(created_users) > 1 else str(uuid.uuid4()),
            "slug": "django-features-eden"
        },
        {
            "title": "Draft Article: Async Best Practices",
            "content": "This is a draft article about async programming...",
            "status": ArticleStatus.DRAFT.value,
            "author_id": str(created_users[2].id) if len(created_users) > 2 else str(uuid.uuid4()),
            "slug": "draft-async-practices"
        }
    ]

    created_articles = []
    for article_data in articles_data:
        schema = ArticleSchema(**article_data)
        if await schema.is_valid(article_data):
            article = await schema.save()
            created_articles.append(article)

    return {
        "message": "Demo data created successfully",
        "users": len(created_users),
        "articles": len(created_articles)
    }


# ────────────────────────────────────────────────────────────────────────
# Documentation
# ────────────────────────────────────────────────────────────────────────

@app.get("/docs")
async def api_docs():
    """API documentation."""
    return {
        "title": "Eden Django Features Demo - API Documentation",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "Home page with feature overview",
            "GET /api/users": "List all users",
            "POST /api/users": "Create a new user",
            "GET /api/articles": "List articles (optional ?status= filter)",
            "POST /api/articles": "Create a new article",
            "GET /api/articles/published": "Get published articles",
            "GET /api/articles/recent": "Get recent articles (?days=7)",
            "PUT /api/articles/{id}/publish": "Publish a draft article",
            "GET /api/stats": "Get system statistics",
            "POST /setup-demo-data": "Setup demo data",
            "/admin/*": "Admin interface (ControlPanel)"
        },
        "features_demonstrated": [
            "ControlPanel - Full admin interface at /admin",
            "ModelSchema - Form validation on POST endpoints",
            "QuerySet Managers - Custom queries on Article.objects",
            "ChoiceField - Enum validation on status/role fields",
            "ModelConfig - Model metadata and configuration"
        ]
    }


if __name__ == "__main__":
    print("🚀 Eden Django Features Demo")
    print("📋 Features demonstrated:")
    print("  • ControlPanel - Admin interface at /admin")
    print("  • ModelSchema - Form validation")
    print("  • QuerySet Managers - Enhanced queries")
    print("  • ChoiceField - Enum validation")
    print("  • ModelConfig - Model metadata")
    print("\n📖 API Documentation at /docs")
    print("🔧 Setup demo data: POST /setup-demo-data")
    print("\nStarting server on http://localhost:8000")

    app.run(host="0.0.0.0", port=8000)