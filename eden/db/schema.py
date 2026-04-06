import re
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints, Annotated, get_origin, get_args
from datetime import datetime, date
import uuid
from decimal import Decimal
import sys

from sqlalchemy import (
    Column,
    ForeignKey,
    Table,
    MetaData,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Uuid,
    JSON,
    Numeric,
    inspect,
)
from sqlalchemy.orm import (
    Mapped,
    relationship,
    mapped_column,
    declared_attr,
    backref
)

# Avoid circular imports by importing Model inside methods if needed
Model = Any

def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    # Handle abbreviations like SQLModel -> sql_model
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def _resolve_table_name(target_name: str, model_cls: Type[Model]) -> str:
    """Resolves a model name to its likely table name."""
    # logger.debug(f"RESOLVING {target_name} for {model_cls.__name__}")
    # 1. Try to find target_name in registry FIRST to get its actual __tablename__
    try:
        from eden.db.base import Base
        if hasattr(Base, "registry"):
            target_cls = Base.registry._class_registry.get(target_name)
            if target_cls and hasattr(target_cls, "__tablename__"):
                return target_cls.__tablename__
    except (ImportError, AttributeError):
        pass

    # 2. Fallbacks for built-in models (if class not yet in registry)
    if target_name == "User":
        return "eden_users"
    
    # 3. Default to pluralized snake_case
    return _camel_to_snake(target_name) + "s"

_PYTHON_TO_SA = {
    str: String, "str": String,
    int: Integer, "int": Integer,
    float: Float, "float": Float,
    bool: Boolean, "bool": Boolean,
    datetime: DateTime, "datetime": DateTime,
    uuid.UUID: Uuid, "uuid.UUID": Uuid, "uuid": Uuid, "UUID": Uuid,
    dict: JSON, "dict": JSON,
    list: JSON, "list": JSON,
    Decimal: Numeric, "Decimal": Numeric,
}

class SchemaInferenceEngine:
    """
    Introspects Python type hints to generate SQLAlchemy model configuration.
    This enables a Django-like declarative experience but built on SA 2.0+ Mapped types.
    """
    
    # Registry to detect reciprocal relationships for back_populates and 1:1 inference
    # (SourceClassName, AttrName) -> (TargetName, IsList)
    _relationship_memo: Dict[Any, Any] = {}


    @classmethod
    def process_class(cls, model_cls: Type[Model]) -> None:
        """Entry point for model processing during __init_subclass__."""
        # 1. Infer basic columns from type hints if not explicitly defined
        cls.infer_columns(model_cls)
        # 2. Infer relationships from type hints
        cls._pre_scan_relationships(model_cls)
        cls.infer_relationships(model_cls)


    @classmethod
    def _analyze_type_hint(cls, hint: Any) -> tuple[List[Any], Any, bool, bool, Optional[str]]:
        """Extracts metadata, type, and relationship info from a type hint."""
        metadata = []
        final_type = hint
        is_list = False
        is_union = False
        target_name = None

        # Iteratively unwrap Annotated and Mapped
        while True:
            # Handle Annotated
            if hasattr(final_type, "__metadata__"):
                metadata.extend(list(getattr(final_type, "__metadata__", [])))
                args = get_args(final_type)
                if args:
                    final_type = args[0]
                else:
                    # Fallback for older versions or edge cases
                    final_type = getattr(final_type, "__origin__", None)
                continue

            
            # Unwrap Mapped[...]
            origin = get_origin(final_type)
            if origin is not None and getattr(origin, "__name__", "") == "Mapped":
                args = get_args(final_type)
                if args:
                    final_type = args[0]
                    # We continue because the inner type could be Annotated
                    continue
            
            # If we didn't unwrap anything, break
            break


        # Re-fetch origin after unwrapping everything
        origin = get_origin(final_type)

        # Handle List/list for relationships
        if origin in (list, List):
            is_list = True
            args = get_args(final_type)
            if args:
                item_type = args[0]
                # In case of List[Annotated[...]] or List[Mapped[...]]
                _, _, _, _, sub_target = cls._analyze_type_hint(item_type)
                target_name = sub_target
            return metadata, final_type, is_list, is_union, target_name
        
        # Handle Union/Optional for relationships
        elif origin is Union:
            is_union = True
            args = get_args(final_type)
            # Extract non-None types
            real_types = [a for a in args if a is not type(None)]
            if real_types:
                main_type = real_types[0]
                # Recurse for the actual type inside Union
                _, _, sub_is_list, _, sub_target = cls._analyze_type_hint(main_type)
                is_list = sub_is_list
                target_name = sub_target
            return metadata, final_type, is_list, is_union, target_name

        # Handle Forward Reference strings or directly passed classes
        basic_type_names = {"str", "int", "float", "bool", "dict", "list", "datetime", "uuid", "decimal", "any", "none", "uuid.uuid", "union", "annotated", "list"}

        
        if isinstance(final_type, str):
            # Iteratively strip generic wrappers from stringified hints
            # e.g. "Mapped[List['EnhancedChild']]" -> "List['EnhancedChild']" -> "'EnhancedChild'" -> "EnhancedChild"
            while True:
                original = final_type
                if final_type.startswith("Mapped[") and final_type.endswith("]"):
                    final_type = final_type[7:-1]
                if final_type.startswith("Optional[") and final_type.endswith("]"):
                    is_union = True
                    final_type = final_type[9:-1]
                if (final_type.startswith("List[") or final_type.startswith("list[")) and final_type.endswith("]"):
                    is_list = True
                    final_type = final_type[5:-1]
                if final_type.startswith("Union[") and final_type.endswith("]"):
                    is_union = True
                    # Take first non-None type
                    inner = final_type[6:-1]
                    parts = [p.strip() for p in inner.split(",")]
                    for p in parts:
                        if p != "None":
                            final_type = p
                            break
                if final_type.startswith("Annotated[") and final_type.endswith("]"):
                    inner = final_type[10:-1]
                    # Take first arg (the actual type)
                    final_type = inner.split(",")[0].strip()
                
                final_type = final_type.strip("'\" \t")
                if final_type == original:
                    break

            lowered = final_type.lower()
            if lowered in basic_type_names or lowered == "mapped" or lowered == "annotated":
                target_name = None
            elif len(final_type) > 0 and final_type[0].isupper():
                target_name = final_type
            else:
                target_name = None
        elif hasattr(final_type, "__forward_arg__"):
            # This is a typing.ForwardRef
            target_name = getattr(final_type, "__forward_arg__")
            if target_name and target_name.lower() in basic_type_names:
                target_name = None
        elif hasattr(final_type, "__name__"):
            name = getattr(final_type, "__name__", "")
            if name.lower() not in basic_type_names and len(name) > 0 and name[0].isupper():
                target_name = name

        return metadata, final_type, is_list, is_union, target_name




    @classmethod
    def infer_columns(cls, model_cls: Type[Model]) -> List[str]:
        """Automatically defines SQLAlchemy columns for type-hinted attributes."""
        from .metadata import parse_metadata
        
        inferred_names = []
        annotations = getattr(model_cls, "__annotations__", {})

        if model_cls.__name__.startswith("Modern"):
            pass
            # logger.debug(f"INFERRING COLUMNS FOR {model_cls.__name__}")

        for name, hint in annotations.items():
            # Skip private or reserved attributes
            if name.startswith("_") or name in ("registry", "metadata", "type_annotation_map"):
                continue

            # Check if already explicitly defined in the class or parents
            if cls._is_already_defined(model_cls, name):
                continue

            # Try to resolve hint properly to handle Annotated
            try:
                resolved_hints = get_type_hints(model_cls, include_extras=True)
                attr_hint = resolved_hints.get(name, hint)
            except Exception:
                attr_hint = hint
            
            # Eval fallback for strings
            if isinstance(attr_hint, str):
                try:
                    mod = sys.modules.get(model_cls.__module__)
                    if mod:
                        namespace = mod.__dict__.copy()
                        import typing
                        namespace.update({
                            'Annotated': Annotated, 'Optional': Optional, 'List': List, 
                            'Dict': Dict, 'Any': Any, 'Union': Union, 'typing': typing,
                            'Mapped': Mapped, 'relationship': relationship,
                            'sys': sys, 'uuid': uuid, 'Decimal': Decimal, 
                            'datetime': datetime, 'date': date
                        })
                        attr_hint = eval(attr_hint, namespace)
                except Exception as e:
                    from eden.logging import get_logger
                    get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
            
            hint = attr_hint
            metadata, final_type, is_list, is_union, target_name = cls._analyze_type_hint(hint)

            # If it's a model relationship, infer_relationships will handle it
            if target_name:
                continue

            # Map Python type to SQLAlchemy type
            # Check origin if it's a generic (like Optional[str])
            origin = get_origin(final_type)
            base_type = final_type
            if origin is Union:
                args = get_args(final_type)
                # If it's Optional (Union[T, None]), extract T
                if type(None) in args:
                    base_type = next(a for a in args if a is not type(None))

            sa_type = _PYTHON_TO_SA.get(base_type)
            if not sa_type:
                # Try string name
                sa_type_name = getattr(base_type, "__name__", str(base_type))
                sa_type = _PYTHON_TO_SA.get(sa_type_name)

            if sa_type:
                # Merge Annotated metadata and generate column
                sa_kwargs, sa_args, info = parse_metadata(metadata)
                
                if model_cls.__name__.startswith("Modern"):
                    pass
                    # logger.debug(f"  SETTING {name}: type={sa_type}, info={info}")

                # Special handling: if sa_type is String and we have MaxLength (info["max"])
                # we need to instantiate String(length)
                actual_sa_type = sa_type
                if (sa_type is String or sa_type == String) and "max" in info:
                    actual_sa_type = String(info["max"])

                # Default nullable based on type hint (Optional)
                if origin is Union and type(None) in get_args(final_type):
                    sa_kwargs.setdefault("nullable", True)

                # Handle default values if provided at class level
                if name in model_cls.__dict__:
                    default_val = model_cls.__dict__[name]
                    if default_val is not None and not hasattr(default_val, "__visit_name__"):
                        sa_kwargs.setdefault("default", default_val)

                setattr(model_cls, name, mapped_column(actual_sa_type, *sa_args, info=info, **sa_kwargs))
                inferred_names.append(name)
        
        return inferred_names

    @classmethod
    def _pre_scan_relationships(cls, model_cls: Type[Model]) -> None:
        """Scan annotations and record relationship intent without building yet."""
        annotations = getattr(model_cls, "__annotations__", {})
        for name, hint in annotations.items():
            _, _, is_list, _, target_name = cls._analyze_type_hint(hint)
            if target_name:
                cls._relationship_memo[(model_cls.__name__, name)] = (target_name, is_list)

    @classmethod
    def infer_relationships(cls, model_cls: Type[Model]) -> List[str]:

        """Introspect type hints to automatically define SQLAlchemy relationships."""
        from .metadata import parse_metadata
        inferred_names = []
        
        annotations = getattr(model_cls, "__annotations__", {})
        for name, hint in annotations.items():
            if name.startswith("_") or name in ("registry", "metadata", "type_annotation_map"):
                continue

            # Try to resolve hint properly to handle Annotated
            try:
                # Use a specific field-focused resolution if possible
                # NOTE: get_type_hints on the class is still the best way to resolve forward refs
                # but we want to be resilient.
                resolved_hints = get_type_hints(model_cls, include_extras=True)
                attr_hint = resolved_hints.get(name, hint)
            except Exception:
                attr_hint = hint
            
            # If hint is still a string (due to from __future__ import annotations),
            # we might need to eval it if we really need the MetadataTokens.
            if isinstance(attr_hint, str):
                try:
                    mod = sys.modules.get(model_cls.__module__)
                    if mod:
                        # Add common types to help evaluation
                        namespace = mod.__dict__.copy()
                        # Ensure we have essential types in namespace
                        import typing
                        namespace.update({
                            'Annotated': Annotated, 'Optional': Optional, 'List': List, 
                            'Dict': Dict, 'Any': Any, 'Union': Union, 'typing': typing,
                            'Mapped': Mapped, 'relationship': relationship,
                            'sys': sys, 'uuid': uuid, 'Decimal': Decimal, 
                            'datetime': datetime, 'date': date
                        })
                        attr_hint = eval(attr_hint, namespace)
                        if model_cls.__name__.startswith("Modern"):
                            pass
                            # logger.debug(f"EVALUATED {name} -> {attr_hint} (type: {type(attr_hint)})")
                    else:
                        if model_cls.__name__.startswith("Modern"):
                            pass
                            # logger.debug(f"NO MODULE FOUND FOR {model_cls.__name__}")
                except Exception as e:
                    if model_cls.__name__.startswith("Modern"):
                        pass
                        # logger.debug(f"EVAL FAILED FOR {name}: {e}")
                    pass
            
            hint = attr_hint

            metadata_tokens, final_type, is_list, is_union, target_name = cls._analyze_type_hint(hint)
            if model_cls.__name__.startswith("Modern"):
                pass
                # logger.debug(f"  ANALYZED {name}: tokens={metadata_tokens}, target={target_name}")

            # Identify if it's a basic type or a model reference
            basic_types = ("str", "int", "float", "bool", "uuid.UUID", "UUID", "datetime", "dict", "list", "Any", "None", "Decimal", "bytes", "Optional")
            
            # If target_name is None, it might be a basic type
            current_target = target_name
            if not current_target:
                # Get the name of the final_type to check if it's basic
                current_target = getattr(final_type, "__name__", str(final_type))
            
            sa_kwargs, sa_args, info = parse_metadata(metadata_tokens)
            if model_cls.__name__.startswith("Modern"):
                pass
                # logger.debug(f"  INFO FOR {name}: {info}")
            if any(bt.lower() == current_target.lower() for bt in basic_types) or (target_name and target_name[0].islower()):
                continue

            sa_kwargs, sa_args, info = parse_metadata(metadata_tokens)
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
    def _is_already_mapped(cls, model_cls: Type[Model], name: str, info: dict) -> tuple[bool, bool, bool]:
        """Checks if a field is already mapped explicitly or in a base class."""
        existing = model_cls.__dict__.get(name)
        
        # Check annotations as well
        has_annotation = name in getattr(model_cls, "__annotations__", {})

        if existing is None:
            # Check for inheritance of columns
            for base in model_cls.mro()[1:]:
                if base.__name__ in ("Base", "object"):
                    continue
                if name in base.__dict__:
                    return True, False, False
            return False, False, False

        is_reference = bool(hasattr(existing, "info") and existing.info.get("is_reference", False))
        is_m2m_explicit = bool(hasattr(existing, "info") and existing.info.get("is_m2m", False))
        
        # If it's already a relationship or column, skip auto-mapping it
        # BUT: don't skip if it's a 'reference' or 'm2m' helper that hasn't been finished yet,
        # OR if it's a relationship without a target argument yet (to be inferred)
        is_sa_rel = (hasattr(existing, "argument") or hasattr(existing, "mapper") or hasattr(existing, "direction"))
        if hasattr(existing, "column") or isinstance(existing, (property, declared_attr)) or is_sa_rel:
            if not is_reference and not is_m2m_explicit:
                # If it's an sa_relationship and has an argument, it's already complete
                if is_sa_rel and getattr(existing, "argument", None) is not None:
                    return True, is_reference, is_m2m_explicit
                elif not is_sa_rel:
                    return True, is_reference, is_m2m_explicit

        # Merge existing info if present
        existing_info = getattr(existing, "info", {})
        for k, v in existing_info.items():
            if k not in info:
                info[k] = v
        
        if is_reference or is_m2m_explicit or is_sa_rel:
            # Try to grab back_populates/lazy/secondary from the existing property if not in info
            for attr in ("back_populates", "lazy", "secondary"):
                if not info.get(attr):
                    # We use __dict__.get to avoid triggering property evaluations 
                    # that might result in AttributeError (e.g. for back_populates early evaluation)
                    val = getattr(existing, "__dict__", {}).get(attr)
                    if val is None:
                        # Fallback for some SA versions that store them elsewhere
                        init_args = getattr(existing, "_init_args", {})
                        if isinstance(init_args, dict):
                            val = init_args.get(attr)
                        elif hasattr(init_args, attr):
                            val = getattr(init_args, attr, None)
                    if val:
                        info[attr] = val

        return False, is_reference, is_m2m_explicit

    @classmethod
    def _build_one_to_many(cls, model_cls: Type[Model], name: str, target_name: str, info: dict, is_m2m_explicit: bool) -> None:
        """Sets up a one-to-many relationship."""
        if is_m2m_explicit:
            cls._setup_m2m(model_cls, name, target_name)
        else:
            backref_name = _camel_to_snake(model_cls.__name__)
            
            # Check for reciprocal in memo
            reciprocal_attr = None
            for (t_cls, t_attr), (src_cls, is_list) in cls._relationship_memo.items():
                if t_cls == target_name and src_cls == model_cls.__name__:
                    reciprocal_attr = t_attr
                    break
            
            # Retroactive sync: Check if someone already pointed to us
            for (src_name, src_attr), (t_name, is_list) in cls._relationship_memo.items():
                if t_name == model_cls.__name__ and src_name == target_name:
                    # We are the target of an already defined relationship
                    reciprocal_attr = src_attr
                    # Update other side to back_populates to us
                    other_cls = cls._get_target_class(model_cls, target_name)
                    if other_cls:
                        other_rel = getattr(other_cls, src_attr, None)
                        if other_rel and hasattr(other_rel, "prop"):
                            other_rel.prop.back_populates = name
                            other_rel.prop.backref = None

            # Enhanced one-liner backref
            effective_back_populates = info.get("back_populates") or reciprocal_attr
            
            kwargs = {
                "lazy": info.get("lazy", "selectin"),
                "overlaps": "*",
                "back_populates": effective_back_populates,
            }
            
            if not effective_back_populates:
                if backref_name:
                    kwargs["backref"] = backref_name
                else:
                    kwargs["backref"] = _camel_to_snake(model_cls.__name__)
            
            setattr(model_cls, name, relationship(target_name, **kwargs))



    @classmethod
    def _setup_m2m(cls, model_cls: Type[Model], name: str, target_name: str) -> None:
        """
        Configures many-to-many relationship and creates through table.
        
        This method is called during model initialization and is safe to call
        multiple times (idempotent). The through table is created exactly once
        using alphabetical sorting to ensure stable table names regardless of
        the order models are defined.
        
        Args:
            model_cls: The model class containing the M2M relationship
            name: The attribute name of the relationship
            target_name: The name or class of the target model
        
        Raises:
            RuntimeError: If M2M table creation fails
        """
        # Initialize M2M registry if not present (safe for inheritance)
        if not hasattr(model_cls, "__m2m_registry__"):
            model_cls.__m2m_registry__ = {}

        target_table_name = _resolve_table_name(target_name, model_cls)
        # Alphabetical sort ensures stable join table names regardless of definition order
        table_parts = sorted([model_cls.__tablename__, target_table_name])
        table_name = f"{table_parts[0]}_{table_parts[1]}"
        
        # Check if table already created in this process (via metadata or registry)
        metadata = model_cls.metadata
        if table_name not in metadata.tables:
            if table_name not in model_cls.__m2m_registry__:
                cls._create_m2m_table(model_cls, {
                    "table_name": table_name,
                    "target_name": target_name,
                    "target_table": target_table_name,
                    "cls_snake": _camel_to_snake(model_cls.__name__)
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
    def _get_target_class(cls, model_cls: Type[Model], target_name: str) -> Optional[Type[Model]]:
        """Resolves target_name string to a model class."""
        from eden.db.base import Base
        if hasattr(Base, "registry"):
            return Base.registry._class_registry.get(target_name)
        return None
    @classmethod
    def _ensure_fk_column(cls, model_cls: Type[Model], name: str, target_name: str, info: dict, sa_kwargs: dict) -> str:
        """Ensures the foreign key column exists for a many-to-one relationship."""
        fk_col = f"{name}_id"
        
        # Check if the column already exists AND has a ForeignKey
        existing = getattr(model_cls, fk_col, None)
        has_fk = False
        if existing:
            # Check for MappedColumn or Column
            col_obj = None
            if hasattr(existing, "column"):
                col_obj = existing.column
            
            if col_obj is not None and hasattr(col_obj, "foreign_keys") and col_obj.foreign_keys:
                has_fk = True

        if not has_fk:
            target_table = _resolve_table_name(target_name, model_cls)
            is_legacy = target_name in ("Role", "Permission")
            
            # Use specified fk_type if provided in info, else default to UUID
            fk_type = info.get("fk_type") or (Uuid(native_uuid=True) if not is_legacy else Integer)
            
            fk_info = info.copy()
            fk_info.pop("is_reference", None)
            fk_info.pop("is_m2m", None)

            target_fk = f"{target_table}.id"
            col = mapped_column(
                fk_type,
                ForeignKey(target_fk, ondelete=info.get("on_delete", "CASCADE")),
                nullable=sa_kwargs.get("nullable", True),
                index=sa_kwargs.get("index", True),
                info=fk_info
            )
            setattr(model_cls, fk_col, col)
        return fk_col

    @classmethod
    def _build_many_to_one(cls, model_cls: Type[Model], name: str, target_name: str, info: dict, sa_kwargs: dict, is_reference: bool) -> None:
        """Sets up a many-to-one relationship."""
        fk_col = cls._ensure_fk_column(model_cls, name, target_name, info, sa_kwargs)

        # Check for reciprocal in memo to detect 1:1 vs N:1 and sync back_populates
        reciprocal_attr = info.get("back_populates")
        reciprocal_is_list = True # Default to many
        
        if not reciprocal_attr:
            for (memo_src_cls, memo_attr), (memo_tgt_cls, memo_is_list) in cls._relationship_memo.items():
                if memo_src_cls == target_name and memo_tgt_cls == model_cls.__name__:
                    reciprocal_attr = memo_attr
                    reciprocal_is_list = memo_is_list
                    
                    # Retroactive sync: if they already built their relationship, update it to point back to us
                    other_cls = cls._get_target_class(model_cls, target_name)
                    if other_cls:
                        other_rel = getattr(other_cls, memo_attr, None)
                        if other_rel and hasattr(other_rel, "prop"):
                            # This ensures two-way binding even if the other side was defined first
                            other_rel.prop.back_populates = name
                            other_rel.prop.backref = None
                    break

        # If it's 1:1 (singular on both sides), backref should also be singular and uselist=False
        is_o2o = not reciprocal_is_list
        default_backref = _camel_to_snake(model_cls.__name__)
        if not is_o2o:
             default_backref += "s" # Plural for many side
        
        backref_name = info.get("backref") or default_backref
        
        kwargs = {
            "overlaps": "*",
            "uselist": False,
            "foreign_keys": f"{model_cls.__name__}.{fk_col}",
            "back_populates": info.get("back_populates") or reciprocal_attr,
            "lazy": info.get("lazy", "selectin"),
        }
        
        if not kwargs["back_populates"]:
            # Fallback to backref
            target_cls = cls._get_target_class(model_cls, target_name)
            if target_cls and hasattr(target_cls, backref_name):
                pass # Avoid collision
            else:
                if is_o2o:
                    kwargs["backref"] = backref(backref_name, uselist=False, overlaps="*")
                else:
                    kwargs["backref"] = backref(backref_name, overlaps="*")
        
        setattr(model_cls, name, relationship(target_name, **kwargs))



    @classmethod
    def _is_already_defined(cls, model_cls: Type[Model], name: str) -> bool:
        """Check if attribute is already mapped in current class or parents."""
        # Check current class
        if name in model_cls.__dict__:
            val = model_cls.__dict__[name]
            if hasattr(val, "column") or hasattr(val, "mapper") or hasattr(val, "direction") or isinstance(val, (property, declared_attr)):
                return True
            # Also skip if it's one of our relationship helpers
            if hasattr(val, "info") and (val.info.get("is_reference") or val.info.get("is_m2m")):
                return True
        
        # Check parents (including Model)
        for base in model_cls.mro()[1:]:
            if base.__name__ in ("Base", "object"):
                continue
            if name in base.__dict__:
                val = base.__dict__[name]
                if hasattr(val, "column") or hasattr(val, "mapper") or hasattr(val, "direction") or isinstance(val, (property, declared_attr)):
                    return True
        return False


    @classmethod
    def generate_pydantic_schema(
        cls, 
        model_cls: Type[Model], 
        include: Optional[List[str]] = None, 
        exclude: Optional[List[str]] = None, 
        only_columns: bool = False
    ) -> Type[Any]:
        """
        Generates a Pydantic model (Schema) from an Eden Model's type hints and metadata.
        This provides the bridge between the ORM and the form/API layers.
        """
        from pydantic import create_model, Field
        from .metadata import parse_metadata
        
        fields = {}
        include_set = set(include) if include else None
        exclude_set = set(exclude) if exclude else set()
        
        # 1. Gather all annotations from the model class and its parents
        try:
            hints = get_type_hints(model_cls, include_extras=True)
        except Exception:
            # Fallback to direct annotations if get_type_hints fails (e.g. forward refs)
            hints = getattr(model_cls, "__annotations__", {})
            
        for name, hint in hints.items():
            if name.startswith("_") or name in ("registry", "metadata", "type_annotation_map"):
                continue
                
            if include_set and name not in include_set:
                continue
            if name in exclude_set:
                continue
                
            metadata, final_type, is_list, is_union, target_name = cls._analyze_type_hint(hint)
            
            # 2. Extract info from type hint metadata
            _, _, info = parse_metadata(metadata)
            
            # 3. Extract info from class attribute if it's a mapped_column-like object
            attr_val = getattr(model_cls, name, None)
            if attr_val is not None:
                 # mapped_column objects in SA 2.0 have .column.info
                 if hasattr(attr_val, "column") and hasattr(attr_val.column, "info"):
                     # Merge attribute info (priority to attribute info)
                     info.update(attr_val.column.info)
                 elif hasattr(attr_val, "info"):
                     # Relationship objects might have .info
                     info.update(attr_val.info)

            # 4. Handle relationships and field types
            if only_columns and target_name:
                continue
                
            field_type = final_type
            if target_name and not is_list:
                # Many-to-one or one-to-one: usually we want the ID here for forms
                field_type = Optional[uuid.UUID]
            elif target_name and is_list:
                 # One-to-many: usually skip for flat schemas or use List[UUID]
                 # For now, skip to match simple forms
                 continue
            
            # Infer widget if not explicitly provided
            if "widget" not in info:
                if final_type is int:
                    info["widget"] = "number"
                elif final_type is float:
                    info["widget"] = "number"
                elif final_type is bool:
                    info["widget"] = "checkbox"
                elif final_type is datetime:
                    info["widget"] = "datetime-local"
                elif final_type is date:
                    info["widget"] = "date"

            # Map Eden metadata to Pydantic field kwargs
            pydantic_kwargs = {}
            if "label" in info:
                pydantic_kwargs["description"] = info["label"]
            
            # pydantic uses json_schema_extra in v2
            pydantic_kwargs["json_schema_extra"] = info.copy()
            
            if "max" in info:
                if isinstance(final_type, type) and issubclass(final_type, str):
                    pydantic_kwargs["max_length"] = info["max"]
                else:
                    pydantic_kwargs["le"] = info["max"]
            if "min" in info:
                if isinstance(final_type, type) and issubclass(final_type, str):
                    pydantic_kwargs["min_length"] = info["min"]
                else:
                    pydantic_kwargs["ge"] = info["min"]
            
            # Default value
            default = ...
            if name in model_cls.__dict__:
                val = model_cls.__dict__[name]
                # If it's a mapped_column, InstrumentedAttribute, or similar, don't use it as default
                if not hasattr(val, "column") and not hasattr(val, "mapper") and not hasattr(val, "prop"):
                    default = val
            
            # Required status
            if info.get("required") is False or is_union:
                if default is ...:
                    default = None
            
            fields[name] = (field_type, Field(default=default, **pydantic_kwargs))
            
        # Create the dynamic Pydantic model
        schema_name = f"{model_cls.__name__}Schema"
        return create_model(schema_name, **fields)


class ValidationScanner:
    """Discovers validation rules from model attributes."""
    
    @classmethod
    def _has_default(cls, attr: Any) -> bool:
        """Check if attribute has a default or server_default."""
        col = None
        if hasattr(attr, "prop") and hasattr(attr.prop, "columns") and attr.prop.columns:
            col = attr.prop.columns[0]
        elif hasattr(attr, "column"):
            col = attr.column
        elif hasattr(attr, "mapped_column") and hasattr(attr, "column"):
            col = attr.column
            
        if col is not None:
            return (hasattr(col, "default") and col.default is not None) or \
                   (hasattr(col, "server_default") and col.server_default is not None)
        return False

    @classmethod
    def _is_numeric_attr(cls, attr: Any) -> bool:
        """Check if attribute represents a numeric field."""
        if hasattr(attr, "prop"):  # InstrumentedAttribute
            try:
                col = attr.prop.columns[0]
                return isinstance(col.type, (Integer, Float, Numeric))
            except (AttributeError, IndexError):
                pass

        if hasattr(attr, "type"):
            return isinstance(attr.type, (Integer, Float, Numeric))
        elif hasattr(attr, "column") and hasattr(attr.column, "type"):
            return isinstance(attr.column.type, (Integer, Float, Numeric))

        return False

    @classmethod
    def discover_rules(cls, model_cls: Type[Model]) -> List[tuple]:
        """Scans model and its base classes for validation metadata."""
        # logger.debug(f"SCANNING RULES FOR {model_cls.__name__}")
        discovered_rules = []

        for base in model_cls.__mro__:
            if base.__name__ == "object":
                continue

            # logger.debug(f"  SCANNING BASE {base.__name__}")
            for name, attr in base.__dict__.items():
                if model_cls.__name__.startswith("Modern") and not name.startswith("__"):
                    pass
                    # logger.debug(f"    CHECKING {name}: {type(attr)}")
                info = None
                if hasattr(attr, "info"):
                    info = attr.info
                    if model_cls.__name__.startswith("Modern") and not name.startswith("__"):
                        pass
                        # logger.debug(f"      FOUND ATTR.INFO: {info}")
                elif hasattr(attr, "column") and hasattr(attr.column, "info"):
                    info = attr.column.info
                    if model_cls.__name__.startswith("Modern") and not name.startswith("__"):
                        pass
                        # logger.debug(f"      FOUND ATTR.COLUMN.INFO: {info}")
                elif hasattr(attr, "prop") and hasattr(attr.prop, "columns") and attr.prop.columns:
                    info = attr.prop.columns[0].info
                    if model_cls.__name__.startswith("Modern") and not name.startswith("__"):
                        pass
                        # logger.debug(f"      FOUND ATTR.PROP.INFO: {info}")

                if not info:
                    continue

                # logger.debug(f"DISCOVERED INFO FOR {name}: {info}")
                is_numeric = cls._is_numeric_attr(attr)

                if "max" in info:
                    meth = model_cls.rule_max_value if is_numeric else model_cls.rule_max_length
                    discovered_rules.append((meth, name, info["max"]))
                if "min" in info:
                    meth = model_cls.rule_min_value if is_numeric else model_cls.rule_min_length
                    discovered_rules.append((meth, name, info["min"]))
                if info.get("required") and not cls._has_default(attr):
                    if not info.get("is_reference") and not info.get("is_m2m"):
                        discovered_rules.append((model_cls.rule_required, name, None))
                if "choices" in info:
                    discovered_rules.append((model_cls.rule_choices, name, info["choices"]))
                if "pattern" in info:
                    discovered_rules.append((model_cls.rule_pattern, name, info["pattern"]))

        return discovered_rules
