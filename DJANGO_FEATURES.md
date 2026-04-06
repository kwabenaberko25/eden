# Eden Django-Inspired Features

This document describes the Django-inspired features implemented in Eden Framework, providing familiar patterns for developers coming from Django while maintaining Eden's async-first, type-safe architecture.

## Overview

Eden now includes five key Django-inspired features:

1. **ControlPanel** - Admin interface with HTMX-powered CRUD operations
2. **ModelSchema** - Type-safe form validation and serialization
3. **QuerySet Managers** - Enhanced query operations with async methods
4. **ChoiceField** - Enum-based field validation with display names
5. **ModelConfig** - Comprehensive model metadata and configuration

## ControlPanel - Admin Interface

The ControlPanel provides a Django Admin-like interface for managing your models with real-time updates via HTMX.

### Basic Usage

```python
from eden.panel import ControlPanel, BasePanel
from your_app.models import Article

class ArticlePanel(BasePanel):
    display_fields = ["title", "status", "author"]
    search_fields = ["title", "content"]
    filter_fields = ["status", "author"]
    ordering = ["-created_at"]

# Register the panel
panel = ControlPanel()
panel.register(Article)(ArticlePanel)

# Add to your app
app.add_route("/admin", panel.routes())
```

### Panel Configuration

```python
from eden.panel import PanelConfig

config = PanelConfig(
    title="My Admin",
    theme="dark",
    auth_required=True,
    items_per_page=50,
    enable_realtime=True,
    enable_export=True,
    enable_bulk_actions=True
)

panel = ControlPanel(config)
```

### Custom Panels

```python
class CustomArticlePanel(BasePanel):
    display_fields = ["title", "status", "word_count"]
    search_fields = ["title", "content"]
    filter_fields = ["status"]
    readonly_fields = ["word_count"]

    async def get_queryset(self, request):
        # Custom queryset logic
        return Article.query.filter(published=True)

    async def word_count(self, obj):
        # Custom display method
        return len(obj.content.split())
```

## ModelSchema - Form Validation

ModelSchema provides type-safe form validation and serialization, similar to Django's ModelForm but with Pydantic integration.

### Basic Usage

```python
from eden.schemas import ModelSchema
from your_app.models import Article

class ArticleSchema(ModelSchema):
    class Meta:
        model = Article
        exclude_fields = ["internal_notes"]
        read_only_fields = ["id", "created_at"]
        required_fields = ["title", "content"]

# Create and validate
schema = ArticleSchema(
    title="My Article",
    content="Article content...",
    status="published"
)

is_valid = await schema.is_valid(request_data)
if is_valid:
    article = await schema.save()
```

### Advanced Configuration

```python
class ArticleSchema(ModelSchema):
    # Custom validation
    async def clean_title(self, value):
        if len(value) < 5:
            raise ValidationError("Title too short")
        return value

    class Meta:
        model = Article
        fields = ["title", "content", "status"]
        required_fields = ["title"]
        nested_fields = ["author"]  # For related objects
```

### Schema Methods

```python
schema = ArticleSchema.from_model(existing_article)  # Load from instance
data = schema.to_dict()  # Serialize to dict
await schema.save()  # Save to database
await schema.delete()  # Delete instance
```

## QuerySet Managers - Enhanced Queries

QuerySet provides enhanced query operations with async methods and chainable operations.

### Basic Usage

```python
from eden.querysets import QuerySet, Manager

# Direct QuerySet usage
articles = QuerySet(Article)
published = await articles.filter(status="published").all()
count = await articles.count()

# Bulk operations
await articles.bulk_create(article_list)
await articles.bulk_update(article_list, ["status"])
```

### Custom Managers

```python
class ArticleManager(Manager):
    def published(self):
        return self.filter(status="published")

    def by_author(self, author_id):
        return self.filter(author_id=author_id)

    async def recent_comments(self):
        # Custom async method
        return await self.filter(
            created_at__gte=datetime.now() - timedelta(days=7)
        ).aggregate(count=Count("id"))

# Use in model
class Article(Model):
    objects = ArticleManager()

    # Usage
    published_articles = await Article.objects.published().all()
    author_articles = await Article.objects.by_author(123).all()
```

### QuerySet Methods

```python
qs = Article.objects.all()

# Filtering
filtered = qs.filter(title__icontains="python")

# Ordering
ordered = qs.order_by("-created_at")

# Limiting
limited = qs.limit(10).offset(20)

# Aggregation
stats = await qs.aggregate(
    total=Count("*"),
    avg_length=Avg("content_length")
)

# Exists check
exists = await qs.exists()

# Values
titles = await qs.values("title").all()
title_list = await qs.values_list("title", flat=True).all()
```

## ChoiceField - Enum Validation

ChoiceField provides enum-based field validation with automatic display names.

### Basic Usage

```python
from eden.enums import ChoiceField, ChoiceEnum

class Status(ChoiceEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @property
    def display_name(self) -> str:
        return self.value.title()

class Article(Model):
    status = ChoiceField(choices=Status, default=Status.DRAFT)

# Usage
article = Article(status=Status.PUBLISHED)
print(article.status.display_name)  # "Published"
```

### Field Configuration

```python
# With custom validation
status_field = ChoiceField(
    choices=Status,
    default=Status.DRAFT,
    validators=[custom_validator],
    help_text="Publication status"
)

# SQLAlchemy integration
status_column = status_field.get_sqlalchemy_column("status")
```

### Choice Methods

```python
# Validation
Status.validate_choice("draft")  # True
Status.validate_choice("invalid")  # False

# Display names
Status.get_display_name("draft")  # "Draft"

# Collections
Status.choices  # [("draft", "Draft"), ...]
Status.values  # ["draft", "published", "archived"]
Status.display_names  # ["Draft", "Published", "Archived"]
```

## ModelConfig - Model Metadata

ModelConfig provides comprehensive model metadata and configuration options.

### Basic Usage

```python
from eden.models import ModelConfig

class Article(Model):
    title = StringField(max_length=200)
    content = TextField()

    class Meta:
        # Basic options
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-created_at"]

        # API options
        api_resource = True
        api_readonly_fields = ["id", "created_at"]
        api_required_fields = ["title"]
        api_exclude_fields = ["internal_notes"]

        # Admin options
        admin_list_display = ["title", "status", "created_at"]
        admin_list_filter = ["status", "created_at"]
        admin_search_fields = ["title", "content"]
        admin_ordering = ["-created_at"]
        admin_list_per_page = 25

        # Database options
        db_table = "articles"
        indexes = [
            {"fields": ["title"]},
            {"fields": ["status", "created_at"], "unique": False}
        ]

        # Validation
        unique_together = [["title", "author"]]
        validators = [custom_validator]
```

### Configuration Methods

```python
config = Article.Meta

# API field handling
api_fields = config.api_fields  # Dict of field configs
field_info = config.get_api_field_info("title")  # Field metadata

# Admin field handling
admin_fields = config.admin_fields
admin_info = config.get_admin_field_info("title")

# Database configuration
table_name = config.db_table
model_indexes = config.indexes
```

## Integration Example

Here's a complete example showing all features working together:

```python
from eden import Eden, Model, StringField, TextField
from eden.panel import ControlPanel, BasePanel
from eden.schemas import ModelSchema
from eden.querysets import Manager
from eden.enums import ChoiceField, ChoiceEnum
from eden.models import ModelConfig

# Define choices
class Status(ChoiceEnum):
    DRAFT = "draft"
    PUBLISHED = "published"

    @property
    def display_name(self):
        return self.value.title()

# Define model
class Article(Model):
    title = StringField(max_length=200)
    content = TextField()
    status = ChoiceField(choices=Status, default=Status.DRAFT)

    # Custom manager
    objects = ArticleManager()

    class Meta:
        verbose_name = "Article"
        api_resource = True
        admin_list_display = ["title", "status"]
        admin_list_filter = ["status"]
        admin_search_fields = ["title", "content"]

# Custom manager
class ArticleManager(Manager):
    def published(self):
        return self.filter(status=Status.PUBLISHED.value)

# Schema
class ArticleSchema(ModelSchema):
    class Meta:
        model = Article
        required_fields = ["title", "content"]

# Admin panel
class ArticlePanel(BasePanel):
    display_fields = ["title", "status"]
    search_fields = ["title", "content"]
    filter_fields = ["status"]

# Setup app
app = Eden()

# Register admin
panel = ControlPanel()
panel.register(Article)(ArticlePanel)
app.add_route("/admin", panel.routes())

# API endpoints
@app.post("/articles")
async def create_article(request):
    schema = ArticleSchema(**(await request.json()))
    if await schema.is_valid():
        article = await schema.save()
        return {"id": article.id}
    return {"errors": schema.errors}

@app.get("/articles/published")
async def get_published():
    articles = await Article.objects.published().all()
    return {"articles": articles}
```

## Migration from Django

| Django | Eden |
|--------|------|
| `ModelForm` | `ModelSchema` |
| `ModelAdmin` | `BasePanel` |
| `ModelManager` | `Manager` |
| `choices` | `ChoiceField` |
| `Meta` class | `ModelConfig` |
| `QuerySet` | `QuerySet` (enhanced) |

## Best Practices

1. **Use Type Hints**: All features are designed with full type safety
2. **Async First**: All database operations are async
3. **Validation**: Always validate data before saving
4. **Configuration**: Use Meta classes for model configuration
5. **Managers**: Create custom managers for complex queries
6. **Schemas**: Use schemas for all form handling

## Testing

Run the integration tests:

```bash
pytest tests/test_integration.py -v
```

The tests cover:
- Complete workflow integration
- Panel CRUD operations
- Schema validation
- QuerySet operations
- ChoiceField validation
- ModelConfig metadata
- Error handling
- Performance characteristics