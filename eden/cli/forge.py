"""
Eden Forge — CLI code generation utilities.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import click


@click.group()
def generate() -> None:
    """🌿 Eden Framework — The elite web framework for professionals."""
    pass


def get_project_layout() -> tuple[Path, str]:
    """Detect the project layout (flat vs app-package)."""
    project_root = Path.cwd()
    if (project_root / "app").is_dir():
        return project_root, "package"
    return project_root, "flat"


@generate.command()
@click.argument("name")
def model(name: str) -> None:
    """Scaffold a new database model."""
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    root, layout = get_project_layout()
    
    if layout == "package":
        models_dir = root / "app" / "models"
        if not models_dir.exists():
            click.echo("  ❌ Error: 'app/models/' not found.", err=True)
            return
        model_file = models_dir / f"{snake_name}.py"
        display_path = f"app/models/{snake_name}.py"
    else:
        model_file = root / "models.py"
        display_path = "models.py"

    content = f'''
class {class_name}(Model):
    """{class_name} model."""
    name: str = f(max_length=255)
'''

    if layout == "package":
        if model_file.exists():
            click.echo(f"  ❌ Error: Model file '{model_file.name}' already exists.", err=True)
            return
        full_content = f"from eden.orm import Model, f\n{content}"
        model_file.write_text(full_content, encoding="utf-8")
        
        # Update app/models/__init__.py
        init_file = models_dir / "__init__.py"
        init_line = f"from .{snake_name} import {class_name}\n"
        if init_file.exists():
            current_init = init_file.read_text(encoding="utf-8")
            if init_line not in current_init:
                init_file.write_text(current_init + init_line, encoding="utf-8")
        else:
            init_file.write_text(init_line, encoding="utf-8")
    else:
        # Append to root models.py
        if model_file.exists():
            existing = model_file.read_text(encoding="utf-8")
            if f"class {class_name}" in existing:
                click.echo(f"  ⏩ Model {class_name} already exists in models.py")
                return
            model_file.write_text(existing + content, encoding="utf-8")
        else:
            full_content = f"from eden.orm import Model, f\n{content}"
            model_file.write_text(full_content, encoding="utf-8")

    click.echo(f"  ✨ {'Created' if layout=='package' else 'Updated'} model: {display_path}")


@generate.command()
@click.argument("name")
def route(name: str) -> None:
    """Scaffold a new routing module."""
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    router_name = f"{snake_name}_router"

    root, layout = get_project_layout()
    
    if layout == "package":
        routes_dir = root / "app" / "routes"
        prefix_path = "app/routes"
    else:
        routes_dir = root / "routes"
        prefix_path = "routes"

    if not routes_dir.exists():
        click.echo(f"  ❌ Error: '{prefix_path}/' directory not found.", err=True)
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
    """Index endpoint for {snake_name}."""
    return {{"message": "Hello from {snake_name} router! 🌿"}}
'''
    route_file.write_text(content, encoding="utf-8")
    click.echo(f"  ✨ Created route: {prefix_path}/{snake_name}.py")

    # 2. Update routes/__init__.py for auto-registration
    init_file = routes_dir / "__init__.py"
    if init_file.exists():
        lines = init_file.read_text(encoding="utf-8").splitlines()
        
        import_line = f"from .{snake_name} import {router_name}"
        if import_line not in lines:
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    insert_pos = i + 1
            lines.insert(insert_pos, import_line)

        inclusion_line = f"main_router.include_router({router_name})"
        if inclusion_line not in "".join(lines):
            lines.append(f"\n{inclusion_line}")
        
        init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        click.echo(f"  📝 Updated {prefix_path}/__init__.py (auto-registered)")


@generate.command()
@click.argument("name")
def component(name: str) -> None:
    """Scaffold a new UI component."""
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    class_name = name[0].upper() + name[1:] if not name[0].isupper() else name
    if not class_name.endswith("Component"):
        class_name += "Component"

    root, layout = get_project_layout()
    
    if layout == "package":
        components_dir = root / "app" / "components"
        prefix_path = "app/components"
    else:
        components_dir = root / "components"
        prefix_path = "components"

    templates_dir = root / "templates" / "components"

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
    """{class_name} component."""
    template_name = "components/{snake_name}.html"

    def get_context_data(self, **kwargs):
        # Add your component logic here
        return kwargs
'''
    logic_file.write_text(logic_content, encoding="utf-8")
    click.echo(f"  ✨ Created logic: {prefix_path}/{snake_name}.py")

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

    # 3. Update components/__init__.py
    comp_init = components_dir / "__init__.py"
    import_line = f"from .{snake_name} import {class_name}"
    
    if comp_init.exists():
        lines = comp_init.read_text(encoding="utf-8").splitlines()
        if import_line not in lines:
            lines.append(import_line)
            comp_init.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo(f"  📝 Updated {prefix_path}/__init__.py")
    else:
        comp_init.write_text(import_line + "\n", encoding="utf-8")
        click.echo(f"  📝 Created {prefix_path}/__init__.py")

    # 4. Ensure discovery is enabled in entry point
    if layout == "package":
        entry_file = root / "app" / "__init__.py"
        import_line = "from . import components"
    else:
        entry_file = root / "app.py"
        import_line = "import components"

    if entry_file.exists():
        content = entry_file.read_text(encoding="utf-8")
        if import_line not in content:
            entry_file.write_text(content + f"\n\n# Enable component discovery\n{import_line}\n", encoding="utf-8")
            click.echo(f"  📝 Updated {entry_file.name} (enabled component discovery)")


@generate.command()
@click.argument("name")
def entity(name: str) -> None:
    """Scaffold a full model-schema-router stack."""
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    router_name = f"{snake_name}_router"

    root, layout = get_project_layout()
    
    if layout == "package":
        models_dir = root / "app" / "models"
        schemas_dir = root / "app" / "schemas"
        routes_dir = root / "app" / "routes"
        prefix_app = "app."
    else:
        models_file = root / "models.py"
        schemas_dir = root / "schemas"
        routes_dir = root / "routes"
        prefix_app = ""

    # Ensure directories exist
    schemas_dir.mkdir(parents=True, exist_ok=True)
    if not (schemas_dir / "__init__.py").exists():
        (schemas_dir / "__init__.py").touch()
    
    routes_dir.mkdir(parents=True, exist_ok=True)
    if not (routes_dir / "__init__.py").exists():
        (routes_dir / "__init__.py").touch()

    # 1. Model
    if layout == "package":
        model_file = models_dir / f"{snake_name}.py"
        if not model_file.exists():
            model_content = f'''from eden.orm import Model, f

class {class_name}(Model):
    """{class_name} model."""
    __tablename__ = "{snake_name}s"
    name: str = f(max_length=255)
'''
            model_file.write_text(model_content, encoding="utf-8")
            
            init_file = models_dir / "__init__.py"
            init_line = f"from .{snake_name} import {class_name}\n"
            if init_file.exists():
                current = init_file.read_text(encoding="utf-8")
                if init_line not in current:
                    init_file.write_text(current + init_line, encoding="utf-8")
            click.echo(f"  ✨ Created model: app/models/{snake_name}.py")
    else:
        content = models_file.read_text(encoding="utf-8")
        if f"class {class_name}" not in content:
            model_content = f'''

class {class_name}(db.Model):
    """{class_name} model."""
    __tablename__ = "{snake_name}s"
    id: db.Mapped[int] = db.mapped_column(primary_key=True)
    name: db.Mapped[str] = db.mapped_column(db.String(255))
'''
            models_file.write_text(content + model_content, encoding="utf-8")
            click.echo(f"  ✨ Updated models.py")

    # 2. Schema
    schema_file = schemas_dir / f"{snake_name}.py"
    if not schema_file.exists():
        schema_content = f'''from eden.schemas import Schema
from typing import Optional

class {class_name}Base(Schema):
    name: str

class {class_name}Create({class_name}Base):
    pass

class {class_name}Update(Schema):
    name: Optional[str] = None

class {class_name}Read({class_name}Base):
    id: int
    class Config:
        from_attributes = True
'''
        schema_file.write_text(schema_content, encoding="utf-8")
        click.echo(f"  ✨ Created schema: {prefix_app}schemas/{snake_name}.py")

    # 3. Router
    route_file = routes_dir / f"{snake_name}.py"
    if not route_file.exists():
        model_imp = f"from {prefix_app}models.{snake_name} import {class_name}" if layout == "package" else f"from models import {class_name}"
        route_content = f'''from eden import Router, Response, status
{model_imp}
from {prefix_app}schemas.{snake_name} import {class_name}Create, {class_name}Update, {class_name}Read
from typing import List

{router_name} = Router()

@{router_name}.get("/", response_model=List[{class_name}Read])
async def list_{snake_name}s():
    return await {class_name}.all()

@{router_name}.post("/", response_model={class_name}Read, status_code=status.HTTP_201_CREATED)
async def create_{snake_name}(data: {class_name}Create):
    return await {class_name}.create(**data.model_dump())
'''
        route_file.write_text(route_content, encoding="utf-8")
        click.echo(f"  ✨ Created router: {prefix_app}routes/{snake_name}.py")

        # Update routes/__init__.py
        init_file = routes_dir / "__init__.py"
        if init_file.exists():
            lines = init_file.read_text(encoding="utf-8").splitlines()
            import_line = f"from .{snake_name} import {router_name}"
            if import_line not in lines:
                pos = 0
                for i, ln in enumerate(lines):
                    if ln.startswith("from ") or ln.startswith("import "):
                        pos = i + 1
                lines.insert(pos, import_line)
            
            inc_line = f"main_router.include_router({router_name})"
            if inc_line not in "".join(lines):
                lines.append(f"\n{inc_line}")
            init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo(f"  📝 Updated {prefix_app}routes/__init__.py")


@generate.command()
@click.argument("name")
@click.option("--tenant", is_flag=True, help="Scaffold as a multi-tenant resource.")
def resource(name: str, tenant: bool) -> None:
    """Scaffold a full premium resource (Model + Router + Views)."""
    class_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).title().replace('_', '')
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    
    root, layout = get_project_layout()
    base_class = "TenantResource" if tenant else "Resource"
    
    if layout == "package":
        models_dir = root / "app" / "models"
        res_dir = root / "app" / "resources"
        routes_init = root / "app" / "routes" / "__init__.py"
        prefix_app = "app."
    else:
        models_file = root / "models.py"
        res_dir = root / "resources"
        routes_init = root / "routes" / "__init__.py"
        prefix_app = ""

    tmpl_dir = root / "templates" / "resources" / snake_name

    # 1. Directories
    res_dir.mkdir(parents=True, exist_ok=True)
    if not (res_dir / "__init__.py").exists():
        (res_dir / "__init__.py").touch()
    tmpl_dir.mkdir(parents=True, exist_ok=True)

    # 2. Model
    if layout == "package":
        model_file = models_dir / f"{snake_name}.py"
        if not model_file.exists():
            model_content = f'''from eden.orm import Model, f

class {class_name}(Model):
    """{class_name} model."""
    __tablename__ = "{snake_name}s"
    title: str = f(max_length=200, required=True)
    description: str | None = f(nullable=True)
'''
            model_file.write_text(model_content, encoding="utf-8")
            click.echo(f"  ✨ Created model: app/models/{snake_name}.py")
    else:
        content = models_file.read_text(encoding="utf-8")
        if f"class {class_name}" not in content:
            model_content = f'''

class {class_name}(db.Model):
    """{class_name} model."""
    __tablename__ = "{snake_name}s"
    id: db.Mapped[int] = db.mapped_column(primary_key=True)
    title: db.Mapped[str] = db.mapped_column(db.String(200))
    description: db.Mapped[str | None] = db.mapped_column(db.Text, nullable=True)
'''
            models_file.write_text(content + model_content, encoding="utf-8")
            click.echo(f"  ✨ Updated models.py")

    # 3. Router/Resource
    res_file = res_dir / f"{snake_name}.py"
    if not res_file.exists():
        model_imp = f"from {prefix_app}models.{snake_name} import {class_name}" if layout == "package" else f"from models import {class_name}"
        res_content = f'''from eden.routing import Router
{model_imp}

{snake_name}_router = Router(prefix="/{snake_name}s", model={class_name})

@{snake_name}_router.get("/stats")
async def stats(request):
    count = await {class_name}.count()
    return {{"total": count}}
'''
        res_file.write_text(res_content, encoding="utf-8")
        click.echo(f"  ✨ Created resource router: {prefix_app}resources/{snake_name}.py")

    # 4. Templates
    list_tmpl = f'''@extends("layout.html")
@block("content") {{
    <h1 class="text-3xl font-bold text-white mb-6">{class_name}s</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        @for(item in items) {{
            <div class="glass p-6 rounded-2xl border border-white/10">
                <h3 class="text-xl font-semibold text-white">{{{{ item.title }}}}</h3>
                <p class="text-slate-400 mt-2">{{{{ item.description }}}}</p>
            </div>
        }}
    </div>
</div>
}}
'''
    (tmpl_dir / "list.html").write_text(list_tmpl, encoding="utf-8")
    click.echo(f"  ✨ Created templates in templates/resources/{snake_name}/")

    # 5. Registration
    if routes_init.exists():
        content = routes_init.read_text(encoding="utf-8")
        import_ln = f"from {prefix_app}resources.{snake_name} import {snake_name}_router"
        if import_ln not in content:
            lines = content.splitlines()
            pos = 0
            for i, ln in enumerate(lines):
                if ln.startswith("from ") or ln.startswith("import "):
                    pos = i + 1
            lines.insert(pos, import_ln)
            lines.append(f"main_router.include_router({snake_name}_router)")
            routes_init.write_text("\n".join(lines) + "\n", encoding="utf-8")
            click.echo(f"  📝 Updated {prefix_app}routes/__init__.py")


if __name__ == "__main__":
    generate()
