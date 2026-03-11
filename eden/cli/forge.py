"""
Eden Forge — CLI code generation utilities.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import click


@click.group()
def cli() -> None:
    """🌿 Eden Framework — The elite web framework for professionals."""
    pass


@cli.group(name="generate")
def generate() -> None:
    """🛠️  Eden Generate — Scaffold models, routes, and components."""
    pass


@generate.command()
@click.argument("name")
def model(name: str) -> None:
    """Scaffold a new database model."""
    # Convert name to different cases
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    project_root = Path.cwd()
    models_dir = project_root / "app" / "models"
    
    if not models_dir.exists():
        click.echo("  ❌ Error: 'app/models/' directory not found. Are you in an Eden project root?", err=True)
        return

    model_file = models_dir / f"{snake_name}.py"
    if model_file.exists():
        click.echo(f"  ❌ Error: Model file '{model_file.name}' already exists.", err=True)
        return

    # 1. Create the model file
    content = f'''from eden.orm import Model, f
 
class {class_name}(Model):
    """
    {class_name} model.
    """
    # Use f() for simple fields. Type hints are auto-mapped.
    name: str = f(max_length=255)
 
    # Use f(json=True) for dict/list data
    # payload: dict = f(json=True)
'''
    model_file.write_text(content, encoding="utf-8")
    click.echo(f"  ✨ Created model: app/models/{snake_name}.py")

    # 2. Update app/models/__init__.py
    init_file = models_dir / "__init__.py"
    init_line = f"from .{snake_name} import {class_name}\n"
    
    if init_file.exists():
        current_init = init_file.read_text(encoding="utf-8")
        if init_line not in current_init:
            init_file.write_text(current_init + init_line, encoding="utf-8")
            click.echo("  📝 Updated app/models/__init__.py")
    else:
        init_file.write_text(init_line, encoding="utf-8")
        click.echo("  📝 Created app/models/__init__.py")


@generate.command()
@click.argument("name")
def route(name: str) -> None:
    """Scaffold a new routing module."""
    # Convert name to snake_case for filename and router name
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    router_name = f"{snake_name}_router"

    project_root = Path.cwd()
    routes_dir = project_root / "app" / "routes"

    if not routes_dir.exists():
        click.echo("  ❌ Error: 'app/routes/' directory not found. Are you in an Eden project root?", err=True)
        return

    route_file = routes_dir / f"{snake_name}.py"
    if route_file.exists():
        click.echo(f"  ❌ Error: Route file '{route_file.name}' already exists.", err=True)
        return

    # 1. Create the route file
    content = f'''from eden import Router

{router_name} = Router()

@{router_name}.get("/")
async def index():
    """
    Index endpoint for {snake_name}.
    """
    return {{"message": "Hello from {snake_name} router! 🌿"}}
'''
    route_file.write_text(content, encoding="utf-8")
    click.echo(f"  ✨ Created route: app/routes/{snake_name}.py")

    # 2. Update app/routes/__init__.py for auto-registration
    init_file = routes_dir / "__init__.py"
    if init_file.exists():
        lines = init_file.read_text(encoding="utf-8").splitlines()
        
        # Add import
        import_line = f"from .{snake_name} import {router_name}"
        if import_line not in lines:
            # Place import at the top, after other imports
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    insert_pos = i + 1
            lines.insert(insert_pos, import_line)

        # Add inclusion in main_router
        inclusion_line = f"main_router.include_router({router_name})"
        if inclusion_line not in "".join(lines):
            lines.append(f"\n{inclusion_line}")
        
        init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        click.echo("  📝 Updated app/routes/__init__.py (auto-registered)")
    else:
        # Should not happen in a standard Eden project, but handle just in case
        init_content = f'''from eden import Router
from .{snake_name} import {router_name}

main_router = Router()
main_router.include_router({router_name})
'''
        init_file.write_text(init_content, encoding="utf-8")
        click.echo("  📝 Created app/routes/__init__.py")


@generate.command()
@click.argument("name")
def component(name: str) -> None:
    """Scaffold a new UI component."""
    # PascalCase for class, snake_case for filename/registration
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    class_name = name[0].upper() + name[1:] if not name[0].isupper() else name
    if not class_name.endswith("Component"):
        class_name += "Component"

    project_root = Path.cwd()
    components_dir = project_root / "app" / "components"
    templates_dir = project_root / "templates" / "components"

    # Ensure directories exist
    components_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)

    logic_file = components_dir / f"{snake_name}.py"
    tmpl_file = templates_dir / f"{snake_name}.html"

    if logic_file.exists():
        click.echo(f"  ❌ Error: Component logic file '{logic_file.name}' already exists.", err=True)
        return

    # 1. Create Python Logic
    logic_content = f'''from eden.components import Component, register

@register("{snake_name}")
class {class_name}(Component):
    """
    {name} component.
    """
    template_name = "components/{snake_name}.html"

    def get_context_data(self, **kwargs):
        # Add your component logic here
        return kwargs
'''
    logic_file.write_text(logic_content, encoding="utf-8")
    click.echo(f"  ✨ Created logic: app/components/{snake_name}.py")

    # 2. Create HTML Template
    tmpl_content = f'''<div class="eden-component-{snake_name} p-4 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md">
    <!-- {name} Component Content -->
    <h3 class="text-lg font-bold text-white mb-2">{{{{ title|default("{name}") }}}}</h3>
    <div class="text-slate-400">
        {{% slot "default" %}}
            This is the default content for the {name} component.
        {{% endslot %}}
    </div>
</div>
'''
    tmpl_file.write_text(tmpl_content, encoding="utf-8")
    click.echo(f"  ✨ Created template: templates/components/{snake_name}.html")

    # 3. Update app/components/__init__.py
    comp_init = components_dir / "__init__.py"
    import_line = f"from .{snake_name} import {class_name}"
    
    if comp_init.exists():
        lines = comp_init.read_text(encoding="utf-8").splitlines()
        if import_line not in lines:
            lines.append(import_line)
            comp_init.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo("  📝 Updated app/components/__init__.py")
    else:
        comp_init.write_text(import_line + "\n", encoding="utf-8")
        click.echo("  📝 Created app/components/__init__.py")

    # 4. Ensure app/__init__.py imports components
    app_init = project_root / "app" / "__init__.py"
    if app_init.exists():
        content = app_init.read_text(encoding="utf-8")
        if "from . import components" not in content:
            # Insert after other relative imports
            lines = content.splitlines()
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("from ."):
                    insert_pos = i + 1
            lines.insert(insert_pos, "from . import components")
            app_init.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo("  📝 Updated app/__init__.py (enabled component discovery)")


@generate.command()
@click.argument("name")
def entity(name: str) -> None:
    """Scaffold a full model-schema-router stack."""
    # Convert name to different cases
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    router_name = f"{snake_name}_router"

    project_root = Path.cwd()
    models_dir = project_root / "app" / "models"
    schemas_dir = project_root / "app" / "schemas"
    routes_dir = project_root / "app" / "routes"

    if not all(d.exists() for d in [models_dir, routes_dir]):
        click.echo("  ❌ Error: Eden project structure not found. Are you in the project root?", err=True)
        return

    # 1. Ensure schemas directory exists
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "__init__.py").touch(exist_ok=True)

    # 2. Scaffold Model
    model_file = models_dir / f"{snake_name}.py"
    if not model_file.exists():
        model_content = f'''from eden.orm import Model, f

class {class_name}(Model):
    """
    {class_name} database model.
    """
    __tablename__ = "{snake_name}s"

    name: str = f(max_length=255)
'''
        model_file.write_text(model_content, encoding="utf-8")
        
        # Update app/models/__init__.py
        init_file = models_dir / "__init__.py"
        init_line = f"from .{snake_name} import {class_name}\n"
        if init_file.exists():
            current_init = init_file.read_text(encoding="utf-8")
            if init_line not in current_init:
                init_file.write_text(current_init + init_line, encoding="utf-8")
        else:
            init_file.write_text(init_line, encoding="utf-8")
        click.echo(f"  ✨ Created model: app/models/{snake_name}.py")
    else:
        click.echo(f"  ⏩ Skipping model: app/models/{snake_name}.py (already exists)")

    # 3. Scaffold Schemas
    schema_file = schemas_dir / f"{snake_name}.py"
    if not schema_file.exists():
        schema_content = f'''from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class {class_name}Base(BaseModel):
    name: str

class {class_name}Create({class_name}Base):
    pass

class {class_name}Update(BaseModel):
    name: Optional[str] = None

class {class_name}Read({class_name}Base):
    id: UUID

    class Config:
        from_attributes = True
'''
        schema_file.write_text(schema_content, encoding="utf-8")
        click.echo(f"  ✨ Created schema: app/schemas/{snake_name}.py")
    else:
        click.echo(f"  ⏩ Skipping schema: app/schemas/{snake_name}.py (already exists)")

    # 4. Scaffold Router (CRUD)
    route_file = routes_dir / f"{snake_name}.py"
    if not route_file.exists():
        route_content = f'''from eden import Router, Response, status
from app.models.{snake_name} import {class_name}
from app.schemas.{snake_name} import {class_name}Create, {class_name}Update, {class_name}Read
from typing import List
from uuid import UUID

{router_name} = Router()

@{router_name}.get("/", response_model=List[{class_name}Read])
async def list_{snake_name}s():
    """List all {class_name} entities."""
    return await {class_name}.all()

@{router_name}.post("/", response_model={class_name}Read, status_code=status.HTTP_201_CREATED)
async def create_{snake_name}(data: {class_name}Create):
    """Create a new {class_name}."""
    return await {class_name}.create(**data.model_dump())

@{router_name}.get("/{{id}}", response_model={class_name}Read)
async def get_{snake_name}(id: UUID):
    """Retrieve a {class_name} by ID."""
    item = await {class_name}.get(id)
    if not item:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return item

@{router_name}.put("/{{id}}", response_model={class_name}Read)
async def update_{snake_name}(id: UUID, data: {class_name}Update):
    """Update an existing {class_name}."""
    item = await {class_name}.get(id)
    if not item:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    await item.update(**data.model_dump(exclude_unset=True))
    return item

@{router_name}.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{snake_name}(id: UUID):
    """Delete a {class_name}."""
    item = await {class_name}.get(id)
    if not item:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    await item.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
'''
        route_file.write_text(route_content, encoding="utf-8")
        click.echo(f"  ✨ Created router: app/routes/{snake_name}.py")

        # Update app/routes/__init__.py
        init_file = routes_dir / "__init__.py"
        if init_file.exists():
            lines = init_file.read_text(encoding="utf-8").splitlines()
            import_line = f"from .{snake_name} import {router_name}"
            if import_line not in lines:
                # Place import at typical position
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith("from ") or line.startswith("import "):
                        insert_pos = i + 1
                lines.insert(insert_pos, import_line)

            inclusion_line = f"main_router.include_router({router_name})"
            if inclusion_line not in "".join(lines):
                lines.append(f"\n{inclusion_line}")
            
            init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo("  📝 Updated app/routes/__init__.py (auto-registered)")
    else:
        click.echo(f"  ⏩ Skipping router: app/routes/{snake_name}.py (already exists)")

@generate.command()
@click.argument("name")
@click.option("--tenant", is_flag=True, help="Inherit from TenantResource for data isolation.")
def resource(name: str, tenant: bool) -> None:
    """Scaffold a full Unified Resource stack (Model + Resource + Templates)."""
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    base_class = "TenantResource" if tenant else "Resource"
    
    project_root = Path.cwd()
    models_dir = project_root / "app" / "models"
    res_dir = project_root / "app" / "resources"
    tmpl_dir = project_root / "templates" / "resources" / snake_name
    routes_init = project_root / "app" / "routes" / "__init__.py"

    if not all(d.exists() for d in [models_dir, project_root / "app" / "routes"]):
        click.echo("  ❌ Error: Eden project structure not found.", err=True)
        return

    # 1. Ensure directories
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "__init__.py").touch(exist_ok=True)
    tmpl_dir.mkdir(parents=True, exist_ok=True)

    # 2. Scaffold Model
    model_file = models_dir / f"{snake_name}.py"
    if not model_file.exists():
        model_content = f'''from eden.orm import Model, f

class {class_name}(Model):
    """
    {class_name} database model.
    """
    __tablename__ = "{snake_name}s"

    title: str = f(max_length=200, required=True)
    description: str | None = f(nullable=True)
    
    # Example attachment field
    # photo: str = f(upload_to="{snake_name}s/photos")
'''
        model_file.write_text(model_content, encoding="utf-8")
        
        # Update app/models/__init__.py
        init_file = models_dir / "__init__.py"
        init_line = f"from .{snake_name} import {class_name}\n"
        if init_file.exists():
            current_init = init_file.read_text(encoding="utf-8")
            if init_line not in current_init:
                init_file.write_text(current_init + init_line, encoding="utf-8")
        click.echo(f"  ✨ Created model: app/models/{snake_name}.py")

    # 3. Scaffold Router
    res_file = res_dir / f"{snake_name}.py"
    if not res_file.exists():
        res_content = f'''from eden.routing import Router
from app.models.{snake_name} import {class_name}

{snake_name}_router = Router(prefix="/{snake_name}s", model={class_name})

@{snake_name}_router.get("/stats")
async def stats(request):
    """Custom collection-level action."""
    count = await {class_name}.count()
    return {{"total": count}}
'''
        res_file.write_text(res_content, encoding="utf-8")
        click.echo(f"  ✨ Created router: app/resources/{snake_name}.py")

    # 4. Scaffold Templates (Premium Obsidian)
    templates = {
        "list.html": f'''@extends("layout.html")

@push("styles") {{
<style>
    .res-card {{ transition: transform 0.3s; }}
    .res-card:hover {{ transform: scale(1.02); }}
</style>
}}

@block("content") {{
<div class="space-y-6">
    <div class="flex justify-between items-center">
        <h1 class="text-3xl font-bold text-white font-heading">{class_name}s</h1>
        <button class="btn-primary" hx-get="/{snake_name}s/create" hx-target="#modal-body">
            New {class_name}
        </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="{snake_name}-list">
        @for(item in items) {{
            @fragment("item_card") {{
            <div class="res-card glass p-6 rounded-2xl border border-white/10 shadow-lg shadow-blue-500/5">
                <h3 class="text-xl font-semibold text-white mb-2">{{{{ item.title }}}}</h3>
                <p class="text-slate-400 text-sm line-clamp-2">{{{{ item.description|default("No description") }}}}</p>
                <div class="mt-4 flex gap-2">
                    <a href="/{snake_name}s/{{{{ item.id }}}}" class="text-blue-400 hover:text-blue-300 text-sm">View Details →</a>
                </div>
            </div>
            }}
        }}
    </div>
</div>
}}
''',
        "detail.html": f'''@extends("layout.html")

@block("content") {{
<div class="glass p-10 rounded-3xl border border-white/10">
    <nav class="mb-8">
        <a href="/{snake_name}s" class="text-slate-500 hover:text-white transition-colors">← Back to {class_name}s</a>
    </nav>
    
    <h1 class="text-5xl font-bold text-white mb-4">{{{{ item.title }}}}</h1>
    <div class="prose prose-invert max-w-none text-slate-300">
        {{{{ item.description|markdown }}}}
    </div>
</div>
}}
'''
    }

    for filename, content in templates.items():
        (tmpl_dir / filename).write_text(content, encoding="utf-8")
    click.echo(f"  ✨ Created templates: templates/resources/{snake_name}/")

    # 5. Auto-register in routes/__init__.py
    if routes_init.exists():
        content = routes_init.read_text(encoding="utf-8")
        import_line = f"from app.resources.{snake_name} import {snake_name}_router"
        reg_line = f"main_router.include_router({snake_name}_router)"
        
        if import_line not in content:
            lines = content.splitlines()
            # Add import
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    insert_pos = i + 1
            lines.insert(insert_pos, import_line)
            
            # Add registration
            if reg_line not in "".join(lines):
                lines.append(f"\n# Auto-registered Router\n{reg_line}")
                
            routes_init.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo("  📝 Auto-registered router in app/routes/__init__.py")


if __name__ == "__main__":
    cli()

