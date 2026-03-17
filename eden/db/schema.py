
from __future__ import annotations
import typing
import re
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, get_type_hints, Annotated
from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Table,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Uuid,
    JSON,
    func,
    Enum,
    Numeric,
    Text,
    Date,
    Time,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    declared_attr,
)

if typing.TYPE_CHECKING:
    from eden.db.base import Model
    import pydantic

from sqlalchemy.ext.mutable import MutableDict, MutableList

# Helper to map Python types to SQLAlchemy types for Annotated inference
_PYTHON_TO_SA = {
    str: String,
    int: Integer,
    float: Float,
    bool: Boolean,
    datetime: DateTime,
    uuid.UUID: Uuid,
    dict: MutableDict.as_mutable(JSON),
    list: MutableList.as_mutable(JSON),
}

_MISSING = object()

def _camel_to_snake(name: str) -> str:
    """Helper to convert CamelCase to snake_case."""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

def _resolve_table_name(target_name: str, model_cls: Type[Model]) -> str:
    """Safely resolve table name for a target class name."""
    try:
        from eden.db.base import Base, Model
        reg = Base.registry._class_registry
        if target_name in reg:
            target_cls = reg[target_name]
            if hasattr(target_cls, "__tablename__"):
                return target_cls.__tablename__
            
        for sub in Model.__subclasses__():
            if sub.__name__ == target_name:
                if hasattr(sub, "__tablename__"):
                    return sub.__tablename__
                break
    except (KeyError, AttributeError, NameError):
        pass

    return _camel_to_snake(target_name) + "s"

class SchemaInferenceEngine:
    """
    Handles automatic schema inference from type hints and metadata.
    Reduces complexity in Model.__init_subclass__.
    """
    
    @classmethod
    def process_class(cls, model_cls: Type[Model]) -> List[str]:
        """
        Process the given model class to infer columns and relationships.
        Returns a list of relationship names that should be excluded from regular column mapping.
        """
        # 1. Infer relationships first
        rel_names = cls.infer_relationships(model_cls)
        
        # 2. Process Annotated Column Metadata (Modern Schema)
        from .metadata import parse_metadata
        
        try:
            hints = get_type_hints(model_cls, include_extras=True)
        except Exception:
            hints = getattr(model_cls, "__annotations__", {})

        for name, hint in hints.items():
            if name.startswith("_") or name in rel_names:
                continue
                
            raw_hint = getattr(model_cls, "__annotations__", {}).get(name, hint)
            is_annotated = typing.get_origin(hint) is typing.Annotated or typing.get_origin(raw_hint) is typing.Annotated
            
            if is_annotated:
                effective_hint = hint if typing.get_origin(hint) is typing.Annotated else raw_hint
                metadata = getattr(effective_hint, "__metadata__", ())
                sa_kwargs, sa_args, info = parse_metadata(metadata)
                
                if sa_kwargs or sa_args or info:
                    if cls._is_already_defined(model_cls, name):
                        continue

                    # Auto-create mapped_column
                    args = typing.get_args(effective_hint)
                    if not args:
                        continue
                    
                    base_type = args[0]
                    if typing.get_origin(base_type) is Mapped:
                        base_type = typing.get_args(base_type)[0]
                    
                    # Unwrap Optional/Union
                    while typing.get_origin(base_type) in (typing.Union, getattr(typing, "UnionType", None)):
                        u_args = [a for a in typing.get_args(base_type) if a is not type(None)]
                        if u_args:
                            base_type = u_args[0]
                        else:
                            break

                    sa_type = _PYTHON_TO_SA.get(base_type, base_type)
                    if not isinstance(sa_type, type) and not hasattr(sa_type, "__visit_name__"):
                        continue

                    # Apply constraints
                    if sa_type is String and "max" in info and not sa_args:
                        sa_type = String(info["max"])
                    elif isinstance(sa_type, type) and issubclass(sa_type, String) and "max" in info and not sa_args:
                        sa_type = sa_type(info["max"])

                    if sa_type is Uuid:
                        sa_type = Uuid(native_uuid=False)

                    # Manage default value
                    default_val = model_cls.__dict__.get(name, _MISSING)
                    if default_val is not _MISSING and not hasattr(default_val, "__visit_name__"):
                        sa_kwargs.setdefault("default", default_val)

                    setattr(model_cls, name, mapped_column(sa_type, *sa_args, info=info, **sa_kwargs))
        
        return rel_names

    @classmethod
    def infer_relationships(cls, model_cls: Type[Model]) -> List[str]:
        """Introspect type hints to automatically define SQLAlchemy relationships."""
        from .metadata import parse_metadata
        inferred_names = []
        
        try:
            hints = get_type_hints(model_cls, include_extras=True)
        except Exception:
            hints = getattr(model_cls, "__annotations__", {})

        for name, hint in hints.items():
            if name.startswith("_") or name in ("registry", "metadata", "type_annotation_map"):
                continue

            metadata, final_type, is_list, is_union, target_name = cls._analyze_type_hint(hint)
            if not target_name:
                continue

            # Identify if it's a basic type or a model reference
            basic_types = ("str", "int", "float", "bool", "uuid.UUID", "UUID", "datetime", "dict", "list", "Any", "None", "Decimal", "bytes")
            if any(bt.lower() == target_name.lower() for bt in basic_types) or (target_name and target_name[0].islower()):
                continue

            sa_kwargs, sa_args, info = parse_metadata(metadata)
            should_skip, is_reference, is_m2m_explicit = cls._is_already_mapped(model_cls, name, info)
            if should_skip:
                continue

            inferred_names.append(name)

            if is_list:
                cls._build_one_to_many(model_cls, name, target_name, info, is_m2m_explicit)
            else:
                cls._build_many_to_one(model_cls, name, target_name, info, sa_kwargs, is_reference)

        return inferred_names

    @classmethod
    def apply_comparators(cls, model_cls: Type[Model]) -> None:
        """Attach EdenComparator to all ColumnProperty attributes on the class."""
        from eden.db.lookups import EdenComparator

        for attr_name in list(model_cls.__dict__):
            attr = model_cls.__dict__[attr_name]
            if hasattr(attr, '_attribute_options'):
                try:
                    attr.comparator_factory = EdenComparator
                except (AttributeError, TypeError):
                    pass

    @classmethod
    def generate_pydantic_schema(
        cls,
        model_cls: Type[Model],
        include: Optional[List[str]] = None,
        exclude: Optional[set] = None,
        only_columns: bool = False,
    ) -> Type[pydantic.BaseModel]:
        """Automatically generate a Pydantic schema from the model definition."""
        from pydantic import create_model, ConfigDict, Field
        from eden.forms import Schema as EdenSchema

        # Check cache for efficiency
        if "_schema_cache" not in model_cls.__dict__:
            model_cls._schema_cache = {}
        
        cache_key = f"{model_cls.__name__}:{include}:{exclude}:{only_columns}"
        if cache_key in model_cls._schema_cache:
            return model_cls._schema_cache[cache_key]

        exclude = exclude or set()
        fields = {}
        try:
            annotations = get_type_hints(model_cls)
        # Removed silent pass to debug
        except Exception:
            annotations = getattr(model_cls, "__annotations__", {})

        for name, hint in annotations.items():
            if name.startswith("_") or name in ("registry", "metadata") or name in exclude:
                continue

            if include is not None and name not in include:
                continue

            col = model_cls.__table__.columns.get(name)

            if only_columns and col is None:
                continue

            # Handle Mapped types
            origin = getattr(hint, "__origin__", None)
            if origin is Mapped:
                hint = hint.__args__[0] if hasattr(hint, "__args__") and hint.__args__ else hint

            is_nullable = col is not None and getattr(col, "nullable", False)
            has_default = col is not None and (
                getattr(col, "default", None) is not None
                or getattr(col, "server_default", None) is not None
            )

            field_kwargs = {}
            if col is not None:
                # Extract constraints
                if isinstance(col.type, String) and col.type.length:
                    field_kwargs["max_length"] = col.type.length

                # Propagate Eden metadata (label, widget, etc.)
                info = dict(col.info) if col.info else {}

                # Auto-infer choices from Enum
                if isinstance(col.type, Enum) and "choices" not in info:
                    info["choices"] = [(v, v.title()) for v in col.type.enums]
                    if "widget" not in info:
                        info["widget"] = "select"

                # Numeric constraints
                if isinstance(col.type, (Integer, Float, Numeric)):
                    if "min" in info: field_kwargs["ge"] = info["min"]
                    if "max" in info: field_kwargs["le"] = info["max"]

                if "widget" not in info:
                    if isinstance(col.type, Text): info["widget"] = "textarea"
                    elif isinstance(col.type, Boolean): info["widget"] = "checkbox"
                    elif isinstance(col.type, Date): info["widget"] = "date"
                    elif isinstance(col.type, DateTime): info["widget"] = "datetime-local"
                    elif isinstance(col.type, Time): info["widget"] = "time"
                    elif isinstance(col.type, (Integer, Float, Numeric)):
                        info["widget"] = "number"
                        if "step" not in info and isinstance(col.type, (Float, Numeric)):
                            info["step"] = "any"

                if info:
                    field_kwargs["json_schema_extra"] = info

            # Defaults and optionality
            is_internal = name in ("id", "created_at", "updated_at", "deleted_at")
            if is_internal and include is None:
                continue

            if col is None or is_internal or is_nullable or has_default:
                default_val = None
            else:
                default_val = ...

            fields[name] = (hint, Field(default_val, **field_kwargs))

        config = ConfigDict(arbitrary_types_allowed=True)
        dynamic_model = create_model(
            f"{model_cls.__name__}Schema", __config__=config, __base__=EdenSchema, **fields
        )
        model_cls._schema_cache[cache_key] = dynamic_model
        return dynamic_model

    @classmethod
    def _analyze_type_hint(cls, hint: Any) -> tuple:
        """Analyzes a type hint to extract metadata and target information."""
        metadata = []
        final_type = hint
        
        if typing.get_origin(hint) is typing.Annotated:
            metadata = getattr(hint, "__metadata__", ())
            final_type = typing.get_args(hint)[0]

        if typing.get_origin(final_type) is Mapped:
            final_type = typing.get_args(final_type)[0]

        is_list = False
        origin = typing.get_origin(final_type)
        if origin in (list, List, typing.Sequence, typing.Collection):
            is_list = True
            final_type = typing.get_args(final_type)[0]

        is_union = False
        origin = typing.get_origin(final_type)
        if origin in (typing.Union, getattr(typing, "UnionType", None)):
            is_union = True
            args = [a for a in typing.get_args(final_type) if a is not type(None)]
            if args:
                final_type = args[0]

        target_name = None
        if isinstance(final_type, str):
            target_name = final_type
            if "[" in target_name:
                target_name = target_name.split("[")[-1].split("]")[0]
            target_name = target_name.strip("'\" ")
        elif hasattr(final_type, "__name__"):
            target_name = final_type.__name__
        elif hasattr(final_type, "__forward_arg__"):
            target_name = final_type.__forward_arg__

        return metadata, final_type, is_list, is_union, target_name

    @classmethod
    def _is_already_mapped(cls, model_cls: Type[Model], name: str, info: dict) -> tuple[bool, bool, bool]:
        """Checks if a field is already mapped explicitly or in a base class."""
        existing = model_cls.__dict__.get(name)
        if existing is None:
            # Check for inheritance of columns
            for base in model_cls.mro()[1:]:
                if base.__name__ in ("Model", "Base", "object"):
                    continue
                if name in base.__dict__:
                    # If it's already in a base class, we skip auto-mapping it here
                    return True, False, False
            return False, False, False

        is_reference = bool(hasattr(existing, "info") and existing.info.get("is_reference", False))
        is_m2m_explicit = bool(hasattr(existing, "info") and existing.info.get("is_m2m", False))
        
        if not is_reference and not is_m2m_explicit:
            if hasattr(existing, "column") or isinstance(existing, (property, declared_attr)) or hasattr(existing, "direction"):
                return True, is_reference, is_m2m_explicit
            if hasattr(existing, "argument") or hasattr(existing, "mapper") or hasattr(existing, "direction"):
                return True, is_reference, is_m2m_explicit

        # Merge existing info if present
        existing_info = getattr(existing, "info", {})
        for k, v in existing_info.items():
            if k not in info:
                info[k] = v
        
        if is_reference or is_m2m_explicit:
            # Try to grab back_populates/lazy/secondary from the existing property if not in info
            for attr in ("back_populates", "lazy", "secondary"):
                if not info.get(attr):
                    val = getattr(existing, attr, None)
                    if val:
                        info[attr] = val

        return False, is_reference, is_m2m_explicit

    @classmethod
    def _build_one_to_many(cls, model_cls: Type[Model], name: str, target_name: str, info: dict, is_m2m_explicit: bool) -> None:
        """Sets up a one-to-many relationship."""
        if is_m2m_explicit:
            cls._setup_m2m(model_cls, name, target_name)
        else:
            backref_name = _camel_to_snake(model_cls.__name__) + "s"
            kwargs = {
                "lazy": info.get("lazy", "selectin"),
                "overlaps": "*",
                "back_populates": info.get("back_populates"),
            }
            if not kwargs["back_populates"]:
                kwargs["backref"] = backref_name
            setattr(model_cls, name, relationship(target_name, **kwargs))

    @classmethod
    def _setup_m2m(cls, model_cls: Type[Model], name: str, target_name: str) -> None:
        """Sets up a many-to-many relationship with an implicit join table."""
        cls_snake = _camel_to_snake(model_cls.__name__)
        names = sorted([cls_snake, _camel_to_snake(target_name)])
        table_name = f"rel_{names[0]}_{names[1]}"

        # Track M2M tables to avoid duplicates
        metadata = model_cls.metadata
        if table_name not in metadata.tables:
            cls._create_m2m_table(model_cls, {
                "table_name": table_name,
                "target_name": target_name,
                "cls_snake": cls_snake,
            })
            model_cls.__m2m_registry__[table_name] = True

        table_obj = metadata.tables.get(table_name)
        if table_obj is None:
            raise RuntimeError(f"Failed to create M2M table {table_name}. Metadata tables: {list(metadata.tables.keys())}")
        
        existing = getattr(model_cls, name, None)
        backref_name = _camel_to_snake(model_cls.__name__) + "s"
        back_populates = getattr(existing, "back_populates", None)

        setattr(
            model_cls,
            name,
            relationship(
                target_name,
                secondary=table_obj,
                back_populates=back_populates,
                backref=getattr(existing, "backref", None) or (backref_name if not back_populates else None),
                lazy=getattr(existing, "lazy", "selectin"),
                overlaps=getattr(existing, "overlaps", name),
            ),
        )

    @classmethod
    def _create_m2m_table(cls, model_cls: Type[Model], data: Dict[str, Any]) -> None:
        """Actually creates the M2M table in metadata."""
        table_name = data["table_name"]
        target_name = data["target_name"]
        cls_snake = data["cls_snake"]

        from eden.db.base import Base, Model
        target_cls = Base.registry._class_registry.get(target_name)
        
        # Process M2M table
        metadata = model_cls.metadata
        if table_name in metadata.tables:
            return

        try:
            target_table_name = _resolve_table_name(target_name, model_cls)
            source_table_name = model_cls.__tablename__
            
            # Default to Uuid for now, as Eden models use Uuid.
            # We avoid accessing model_cls.id.type directly because it might be a MappedColumn
            # that doesn't have the type attribute yet during initialization.
            pk_type = Uuid(native_uuid=True)
            
            metadata = model_cls.metadata
            t = Table(
                table_name,
                metadata,
                Column(
                    f"{cls_snake}_id",
                    pk_type,
                    ForeignKey(f"{source_table_name}.id", ondelete="CASCADE"),
                    primary_key=True,
                ),
                Column(
                    f"{_camel_to_snake(target_name)}_id",
                    pk_type,
                    ForeignKey(f"{target_table_name}.id", ondelete="CASCADE"),
                    primary_key=True,
                ),
            )
        except Exception as e:
            raise RuntimeError(f"Failed inside _create_m2m_table for {table_name}: {e}") from e

    @classmethod
    def _build_many_to_one(cls, model_cls: Type[Model], name: str, target_name: str, info: dict, sa_kwargs: dict, is_reference: bool) -> None:
        """Sets up a many-to-one relationship and its corresponding foreign key."""
        fk_col = f"{name}_id"
        if not hasattr(model_cls, fk_col):
            target_table = _resolve_table_name(target_name, model_cls)
            is_legacy = target_name in ("Role", "Permission")
            fk_type = Uuid(native_uuid=True) if not is_legacy else Integer
            
            fk_info = info.copy()
            fk_info.pop("is_reference", None)
            fk_info.pop("is_m2m", None)

            col = mapped_column(
                fk_type,
                ForeignKey(f"{target_table}.id", ondelete=info.get("on_delete", "CASCADE")),
                nullable=sa_kwargs.get("nullable", True),
                index=sa_kwargs.get("index", True),
                info=fk_info
            )
            setattr(model_cls, fk_col, col)

        backref_name = _camel_to_snake(model_cls.__name__)
        kwargs = {
            "overlaps": "*",
            "uselist": False,
            "foreign_keys": f"{model_cls.__name__}.{fk_col}",
            "back_populates": info.get("back_populates"),
        }
        if not kwargs["back_populates"]:
            kwargs["backref"] = backref_name

        # Always update/set the relationship to ensure it has the correct foreign_keys and overlaps
        setattr(model_cls, name, relationship(target_name, **kwargs))

    @classmethod
    def _is_already_defined(cls, model_cls: Type[Model], name: str) -> bool:
        """Check if attribute is already mapped in current class or parents."""
        if name in model_cls.__dict__:
            val = model_cls.__dict__[name]
            if hasattr(val, "column") or hasattr(val, "__visit_name__") or isinstance(val, (property, declared_attr)):
                return True
        
        for base in model_cls.mro()[1:]:
            if base.__name__ in ("Model", "Base", "object"):
                continue
            if name in base.__dict__:
                val = base.__dict__[name]
                if hasattr(val, "column") or hasattr(val, "__visit_name__") or isinstance(val, (property, declared_attr)):
                    return True
        return False


class ValidationScanner:
    """Discovers validation rules from model attributes."""
    
    @classmethod
    def discover_rules(cls, model_cls: Type[Model]) -> List[tuple]:
        """Scans model dictionary for attributes with 'info' containing validation metadata."""
        discovered_rules = []
        for name, attr in model_cls.__dict__.items():
            info = None
            if hasattr(attr, "info"):
                info = attr.info
            elif hasattr(attr, "column") and hasattr(attr.column, "info"):
                info = attr.column.info
            
            if info:
                if "max" in info:
                    discovered_rules.append((model_cls.rule_max_length, name, info["max"]))
                if "min" in info:
                    discovered_rules.append((model_cls.rule_min_length, name, info["min"]))
                if "required" in info and info["required"]:
                    if not info.get("is_reference") and not info.get("is_m2m"):
                        discovered_rules.append((model_cls.rule_required, name, None))
                if "choices" in info:
                    discovered_rules.append((model_cls.rule_choices, name, info["choices"]))
                if "pattern" in info:
                    discovered_rules.append((model_cls.rule_pattern, name, info["pattern"]))
        return discovered_rules
