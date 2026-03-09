"""
Eden Unified — Resource & Model Layer
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union

from eden.db.base import Model
from eden.tenancy.mixins import TenantMixin
from eden.forms import BaseForm, FormField
from eden.routing import Router, Route
from eden.responses import JsonResponse, HtmlResponse


class action:
    """
    Decorator to mark a method as a Resource action.
    """
    def __init__(
        self,
        path: Optional[str] = None,
        methods: List[str] = ["GET"],
        detail: bool = True,
        name: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        self.path = path
        self.methods = methods
        self.detail = detail
        self.name = name
        self.summary = summary

    def __call__(self, func: Callable) -> Callable:
        func._is_eden_action = True
        func._action_meta = {
            "path": self.path or func.__name__,
            "methods": self.methods,
            "detail": self.detail,
            "name": self.name or func.__name__,
            "summary": self.summary or (func.__doc__.strip().split("\n")[0] if func.__doc__ else None),
        }
        return func


class Resource(Model):
    """
    The heart of Eden Unified.
    A Resource represents a domain entity, its data, its forms, and its behavior.
    """
    __abstract__ = True

    @classmethod
    def get_form(cls, data: Optional[Dict[str, Any]] = None) -> BaseForm:
        """Returns a BaseForm initialized with this resource's schema."""
        return BaseForm(schema=cls.to_schema(), data=data)

    @property
    def Form(self) -> BaseForm:
        """Returns a form pre-populated with this instance's data."""
        return BaseForm(schema=self.__class__.to_schema(), data=self.model_dump())

    @classmethod
    def router(cls, prefix: Optional[str] = None) -> Router:
        """
        Generates a Router with CRUD and custom actions.
        """
        # Default prefix logic: use model's tablename if available, otherwise fallback to class's own tablename
        target_name = cls.__tablename__
        if hasattr(cls, "model") and hasattr(cls.model, "__tablename__"):
            target_name = cls.model.__tablename__
            
        router_prefix = prefix or f"/{target_name}"
        res_router = Router(prefix=router_prefix, tags=[cls.__name__])

        # 1. Collection Actions (List, Create)
        @res_router.get("/", name=f"{cls.__tablename__}_list")
        async def list_items(request: Any):
            items = await cls.all()
            
            # Content Negotiation: Render HTML if requested and template exists
            if "text/html" in request.headers.get("accept", "") and hasattr(cls, "template_prefix"):
                from eden.app import Eden
                app: Eden = request.app.eden
                return app.render(f"{cls.template_prefix}/list.html", {"items": items})
                
            return [item.to_dict() for item in items]

        @res_router.post("/", name=f"{cls.__tablename__}_create")
        async def create_item(request: Any):
            if request.is_json:
                data = await request.json()
            else:
                data = await request.form_data()
                
            try:
                if isinstance(data, dict):
                    data.pop("csrf_token", None)
                item = await cls.create(**data)
                
                # If it's a form submission, redirect to list
                if not request.is_json and hasattr(cls, "template_prefix"):
                    from eden.responses import redirect
                    return redirect(url=str(request.url_for(f"{cls.__tablename__}_list")), status_code=303)
                    
                return item.to_dict()
            except Exception as e:
                # If it's a form submission, re-render form with errors
                if not request.is_json and hasattr(cls, "template_prefix"):
                    from eden.app import Eden
                    app: Eden = request.app.eden
                    errors = getattr(e, "errors", [{"msg": str(e)}])
                    return app.render(f"{cls.template_prefix}/create.html", {"errors": errors, "data": data})
                raise e

        # 2. Instance Actions (Get, Update, Delete)
        @res_router.get("/{id:uuid}", name=f"{cls.__tablename__}_detail")
        async def get_item(id: Any, request: Any):
            item = await cls.get_or_404(id=id)
            
            # Content Negotiation: Render HTML if requested and template exists
            if "text/html" in request.headers.get("accept", "") and hasattr(cls, "template_prefix"):
                from eden.app import Eden
                app: Eden = request.app.eden
                return app.render(f"{cls.template_prefix}/detail.html", {"item": item})
                
            return item.to_dict()

        @res_router.patch("/{id:uuid}", name=f"{cls.__tablename__}_update")
        @res_router.post("/{id:uuid}", name=f"{cls.__tablename__}_update_form", include_in_schema=False)
        async def update_item(id: Any, request: Any):
            if request.is_json:
                data = await request.json()
            else:
                data = await request.form_data()
                
            item = await cls.get_or_404(id=id)
            try:
                await item.update(**data)
                
                # If it's a form submission, redirect to detail or list
                if not request.is_json and hasattr(cls, "template_prefix"):
                    from eden.responses import redirect
                    return redirect(url=str(request.url_for(f"{cls.__tablename__}_list")), status_code=303)
                    
                return item.to_dict()
            except Exception as e:
                # If it's a form submission, re-render form with errors
                if not request.is_json and hasattr(cls, "template_prefix"):
                    from eden.app import Eden
                    app: Eden = request.app.eden
                    errors = getattr(e, "errors", [{"msg": str(e)}])
                    return app.render(f"{cls.template_prefix}/edit.html", {"item": item, "errors": errors, "data": data})
                raise e

        @res_router.delete("/{id:uuid}", name=f"{cls.__tablename__}_delete")
        async def delete_item(id: Any):
            item = await cls.get_or_404(id=id)
            await item.delete()
            return {"status": "deleted"}

        # 3. View Actions (Create/Edit Forms)
        if hasattr(cls, "template_prefix"):
            @res_router.get("/create", name=f"{cls.__tablename__}_create_page")
            async def create_page(request: Any):
                from eden.app import Eden
                app: Eden = request.app.eden
                return app.render(f"{cls.template_prefix}/create.html")

            @res_router.get("/{id:uuid}/edit", name=f"{cls.__tablename__}_edit_page")
            async def edit_page(id: Any, request: Any):
                from eden.app import Eden
                app: Eden = request.app.eden
                item = await cls.get_or_404(id=id)
                return app.render(f"{cls.template_prefix}/edit.html", {"item": item})

        # 4. Discover Custom Actions
        for name, member in inspect.getmembers(cls):
            if hasattr(member, "_is_eden_action"):
                meta = member._action_meta
                path = meta["path"]
                methods = meta["methods"]
                
                if meta["detail"]:
                    # Instance-level action: /resource/{id}/action
                    full_path = f"/{{id:uuid}}/{path}"
                    
                    def make_detail_handler(m=member):
                        async def handler(id: Any, **kwargs):
                            instance = await cls.get_or_404(id=id)
                            result = m(instance, **kwargs)
                            if inspect.isawaitable(result):
                                result = await result
                            return result
                        return handler
                    
                    res_router.route(full_path, methods=methods, name=f"{cls.__tablename__}_{name}")(make_detail_handler())
                else:
                    # Collection-level action: /resource/action
                    full_path = f"/{path}"
                    
                    def make_collection_handler(m=member):
                        async def handler(**kwargs):
                            result = m(**kwargs)
                            if inspect.isawaitable(result):
                                result = await result
                            return result
                        return handler
                        
                    res_router.route(full_path, methods=methods, name=f"{cls.__tablename__}_{name}")(make_collection_handler())

        return res_router


class TenantResource(Resource, TenantMixin):
    """A Resource that is automatically scoped to a tenant."""
    __abstract__ = True


class FusionResource(Resource):
    """Backward compatibility for FusionResource."""
    __abstract__ = True
