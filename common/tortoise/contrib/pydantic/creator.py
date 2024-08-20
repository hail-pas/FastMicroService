# ruff: noqa
import inspect
from types import UnionType, GenericAlias
from base64 import b32encode
from typing import TYPE_CHECKING, Any, Union, Optional, _UnionGenericAlias
from hashlib import sha3_224

from pydantic import Field, ConfigDict, create_model, computed_field
from tortoise.fields import IntField, JSONField, TextField, relational
from tortoise.models import Model
from tortoise.queryset import QuerySet
from tortoise.fields.data import IntEnumFieldInstance, CharEnumFieldInstance
from pydantic._internal._decorators import PydanticDescriptorProxy
from tortoise.contrib.pydantic.base import PydanticModel as OriginPydanticModel
from tortoise.contrib.pydantic.base import PydanticListModel as OriginPydanticListModel
from tortoise.contrib.pydantic.utils import get_annotations
from tortoise.contrib.pydantic.creator import PydanticMeta as TortoisePydanticMeta


class PydanticModel(OriginPydanticModel):
    @classmethod
    async def from_queryset(
        cls,
        queryset: "QuerySet",
    ) -> "list[OriginPydanticModel]":
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(
            cls,
            cls.model_config["orig_model"],  # type: ignore
        )
        fetch_fields = [f for f in fetch_fields if f not in queryset._prefetch_queries]
        return [cls.model_validate(e) for e in await queryset.prefetch_related(*fetch_fields)]


def _get_fetch_fields(
    pydantic_class: type[PydanticModel],
    model_class: type[Model],
) -> list[str]:
    fetch_fields = []

    for field_name, mf in pydantic_class.model_fields.items():
        annotation = mf.annotation
        if annotation.__class__ in (GenericAlias, _UnionGenericAlias, UnionType):
            field_type = annotation.__args__[0]
        else:
            field_type = annotation

        if field_name in model_class._meta.fetch_fields and issubclass(
            field_type,
            PydanticModel,
        ):
            subclass_fetch_fields = _get_fetch_fields(
                field_type,
                field_type.model_config["orig_model"],
            )
            if subclass_fetch_fields:
                fetch_fields.extend(
                    [field_name + "__" + f for f in subclass_fetch_fields],
                )
            else:
                fetch_fields.append(field_name)

    return list(set(fetch_fields))


class PydanticListModel(OriginPydanticListModel):
    @classmethod
    async def from_queryset(
        cls,
        queryset: "QuerySet",
    ) -> "OriginPydanticListModel":
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticListModel is based on.
        """
        submodel = cls.__config__.submodel  # type: ignore
        fetch_fields = _get_fetch_fields(
            submodel,
            submodel.model_config["orig_model"],
        )
        fetch_fields = [f for f in fetch_fields if f not in queryset._prefetch_queries]
        return cls(
            __root__=[  # type: ignore
                submodel.model_validate(e) for e in await queryset.prefetch_related(*fetch_fields)
            ],
        )


_MODEL_INDEX: dict[str, type[PydanticModel]] = {}


class PydanticMeta(TortoisePydanticMeta):
    backward_relations: bool = False


def _br_it(val: str) -> str:
    return val.replace("\n", "<br/>").strip()


def _cleandoc(obj: Any) -> str:
    return _br_it(inspect.cleandoc(obj.__doc__ or ""))


def _pydantic_recursion_protector(
    cls: "type[Model]",
    *,
    stack: tuple,
    exclude: tuple[str, ...] = (),
    include: tuple[str, ...] = (),
    computed: tuple[str, ...] = (),
    name=None,
    allow_cycles: bool = False,
    sort_alphabetically: bool | None = None,
) -> type[PydanticModel] | None:
    """
    It is an inner function to protect pydantic model creator against cyclic recursion
    """
    if not allow_cycles and cls in (c[0] for c in stack[:-1]):
        return None

    caller_fname = stack[0][1]
    prop_path = [caller_fname]  # It stores the fields in the hierarchy
    level = 1
    for _, parent_fname, parent_max_recursion in stack[1:]:
        # Check recursion level
        prop_path.insert(0, parent_fname)
        if level >= parent_max_recursion:
            # This is too verbose, Do we even need a way of reporting truncated models?
            # tortoise.logger.warning(
            #     "Recursion level %i has reached for model %s",
            #     level,
            #     parent_cls.__qualname__ + "." + ".".join(prop_path),
            # )
            return None

        level += 1

    return pydantic_model_creator(
        cls,
        exclude=exclude,
        include=include,
        computed=computed,
        name=name,
        _stack=stack,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
    )


def pydantic_model_creator(
    cls: "type[Model]",
    *,
    name=None,
    exclude: tuple[str, ...] = (),
    include: tuple[str, ...] = (),
    computed: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
    allow_cycles: bool | None = None,
    sort_alphabetically: bool | None = None,
    _stack: tuple = (),
    exclude_readonly: bool = False,
    meta_override: type | None = None,
    model_config: ConfigDict | None = None,
    validators: dict[str, Any] | None = None,
    module: str = __name__,
) -> type[PydanticModel]:
    """
    Function to build `Pydantic Model <https://pydantic-docs.helpmanual.io/usage/models/>`__ off Tortoise Model.

    :param _stack: Internal parameter to track recursion
    :param cls: The Tortoise Model
    :param name: Specify a custom name explicitly, instead of a generated name.
    :param exclude: Extra fields to exclude from the provided model.
    :param include: Extra fields to include from the provided model.
    :param computed: Extra computed fields to include from the provided model.
    :param optional: Extra optional fields for the provided model.
    :param allow_cycles: Do we allow any cycles in the generated model?
        This is only useful for recursive/self-referential models.

        A value of ``False`` (the default) will prevent any and all backtracking.
    :param sort_alphabetically: Sort the parameters alphabetically instead of Field-definition order.

        The default order would be:

            * Field definition order +
            * order of reverse relations (as discovered) +
            * order of computed functions (as provided).
    :param exclude_readonly: Build a subset model that excludes any readonly fields
    :param meta_override: A PydanticMeta class to override model's values.
    :param model_config: A custom config to use as pydantic config.
    :param validators: A dictionary of methods that validate fields.
    :param module: The name of the module that the model belongs to.

        Note: Created pydantic model uses config_class parameter and PydanticMeta's
            config_class as its Config class's bases(Only if provided!), but it
            ignores ``fields`` config. pydantic_model_creator will generate fields by
            include/exclude/computed parameters automatically.
    """

    # Fully qualified class name
    fqname = cls.__module__ + "." + cls.__qualname__
    postfix = ""

    def get_name() -> str:
        # If arguments are specified (different from the defaults), we append a hash to the
        # class name, to make it unique
        # We don't check by stack, as cycles get explicitly renamed.
        # When called later, include is explicitly set, so fence passes.
        nonlocal postfix
        is_default = (
            exclude == ()
            and include == ()
            and computed == ()
            and sort_alphabetically is None
            and allow_cycles is None
        )
        hashval = f"{fqname};{exclude};{include};{computed};{_stack}:{sort_alphabetically}:{allow_cycles}"
        postfix = (
            ":" + b32encode(sha3_224(hashval.encode("utf-8")).digest()).decode("utf-8").lower()[:6]
            if not is_default
            else ""
        )
        return fqname + postfix

    # We need separate model class for different exclude, include and computed parameters
    _name = name or get_name()
    has_submodel = False

    # Get settings and defaults
    meta = getattr(cls, "PydanticMeta", PydanticMeta)

    def get_param(attr: str) -> Any:
        if meta_override:
            return getattr(meta_override, attr, getattr(meta, attr, getattr(PydanticMeta, attr)))
        return getattr(meta, attr, getattr(PydanticMeta, attr))

    default_include: tuple[str, ...] = tuple(get_param("include"))
    default_exclude: tuple[str, ...] = tuple(get_param("exclude"))
    default_computed: tuple[str, ...] = tuple(get_param("computed"))
    default_config: ConfigDict | None = get_param("model_config")

    backward_relations: bool = bool(get_param("backward_relations"))

    max_recursion: int = int(get_param("max_recursion"))
    exclude_raw_fields: bool = bool(get_param("exclude_raw_fields"))
    _sort_fields: bool = (
        bool(get_param("sort_alphabetically")) if sort_alphabetically is None else sort_alphabetically
    )
    _allow_cycles: bool = bool(get_param("allow_cycles") if allow_cycles is None else allow_cycles)

    # Update parameters with defaults
    include = tuple(include) + default_include
    exclude = tuple(exclude) + default_exclude
    computed = tuple(computed) + default_computed

    annotations = get_annotations(cls)

    pconfig = PydanticModel.model_config.copy()
    if default_config:
        pconfig.update(default_config)
    if model_config:
        pconfig.update(model_config)
    if "title" not in pconfig:
        pconfig["title"] = name or cls.__name__
    if "extra" not in pconfig:
        pconfig["extra"] = "forbid"

    properties: dict[str, Any] = {}

    # Get model description
    model_description = cls.describe(serializable=False)

    # Field map we use
    field_map: dict[str, dict] = {}
    pk_raw_field: str = ""

    def field_map_update(keys: tuple, is_relation=True) -> None:
        nonlocal pk_raw_field

        for key in keys:
            fds = model_description[key]
            if isinstance(fds, dict):
                fds = [fds]
            for fd in fds:
                n = fd["name"]
                if key == "pk_field":
                    pk_raw_field = n
                # Include or exclude field
                if (include and n not in include) or n in exclude:
                    continue
                # Remove raw fields
                raw_field = fd.get("raw_field", None)
                if raw_field is not None and exclude_raw_fields and raw_field != pk_raw_field:
                    del field_map[raw_field]
                field_map[n] = fd

    # Update field definitions from description
    if not exclude_readonly:
        field_map_update(("pk_field",), is_relation=False)
    field_map_update(("data_fields",), is_relation=False)
    if not exclude_readonly:
        included_fields: tuple = (
            "fk_fields",
            "o2o_fields",
        )
        if backward_relations:
            included_fields = (
                *included_fields,
                "backward_fk_fields",
                "backward_o2o_fields",
                "m2m_fields",
            )

        field_map_update(included_fields)
        # Add possible computed fields
        field_map.update(
            {
                k: {
                    "field_type": callable,
                    "function": getattr(cls, k),
                    "description": None,
                }
                for k in computed
            },
        )

    # Sort field map (Python 3.7+ has guaranteed ordered dictionary keys)
    if _sort_fields:
        # Sort Alphabetically
        field_map = {k: field_map[k] for k in sorted(field_map)}
    else:
        # Sort to definition order
        field_map = {k: field_map[k] for k in tuple(cls._meta.fields_map.keys()) + computed if k in field_map}
    # Process fields
    for fname, fdesc in field_map.items():
        comment = ""
        json_schema_extra: dict[str, Any] = {}
        fconfig: dict[str, Any] = {
            "json_schema_extra": json_schema_extra,
        }
        field_type = fdesc["field_type"]
        field_default = fdesc.get("default")
        is_optional_field = fname in optional

        def get_submodel(_model: "type[Model]") -> type[PydanticModel] | None:
            """Get Pydantic model for the submodel"""
            nonlocal exclude, _name, has_submodel

            if _model:
                new_stack = _stack + ((cls, fname, max_recursion),)

                # Get pydantic schema for the submodel
                prefix_len = len(fname) + 1
                pmodel = _pydantic_recursion_protector(
                    _model,
                    exclude=tuple(str(v[prefix_len:]) for v in exclude if v.startswith(fname + ".")),
                    include=tuple(str(v[prefix_len:]) for v in include if v.startswith(fname + ".")),
                    computed=tuple(str(v[prefix_len:]) for v in computed if v.startswith(fname + ".")),
                    stack=new_stack,
                    allow_cycles=_allow_cycles,
                    sort_alphabetically=sort_alphabetically,
                )
            else:
                pmodel = None

            # If the result is None it has been excluded and we need to exclude the field
            if pmodel is None:
                exclude += (fname,)
            else:
                has_submodel = True
            # We need to rename if there are duplicate instances of this model
            if cls in (c[0] for c in _stack):
                _name = name or get_name()

            return pmodel

        # Foreign keys and OneToOne fields are embedded schemas
        is_to_one_relation = False
        if (
            field_type is relational.ForeignKeyFieldInstance
            or field_type is relational.OneToOneFieldInstance
            or field_type is relational.BackwardOneToOneRelation
        ):
            is_to_one_relation = True
            model = get_submodel(fdesc["python_type"])
            if model:
                if fdesc.get("nullable"):
                    json_schema_extra["nullable"] = True
                if fdesc.get("nullable") or field_default is not None:
                    model = Optional[model]  # type: ignore

                properties[fname] = model

        # Backward FK and ManyToMany fields are list of embedded schemas
        elif field_type is relational.BackwardFKRelation or field_type is relational.ManyToManyFieldInstance:
            model = get_submodel(fdesc["python_type"])
            if model:
                properties[fname] = list[model]  # type: ignore

        # Computed fields as methods
        elif field_type is callable:
            func = fdesc["function"]
            annotation = get_annotations(cls, func).get("return", None)
            comment = _cleandoc(func)
            if annotation is not None:
                properties[fname] = computed_field(return_type=annotation, description=comment)(func)

        # Json fields
        elif field_type is JSONField:
            properties[fname] = Any
        elif field_type in [IntEnumFieldInstance, CharEnumFieldInstance]:
            if fdesc.get("nullable"):
                properties[fname] = cls._meta.fields_map[fname].enum_type | None  # type: ignore
            else:
                properties[fname] = cls._meta.fields_map[fname].enum_type  # type: ignore
        # Any other tortoise fields
        else:
            annotation = annotations.get(fname, None)
            if "readOnly" in fdesc["constraints"]:
                json_schema_extra["readOnly"] = fdesc["constraints"]["readOnly"]
                del fdesc["constraints"]["readOnly"]
            fconfig.update(fdesc["constraints"])
            ptype = fdesc["python_type"]
            if fdesc.get("nullable"):
                json_schema_extra["nullable"] = True
            if is_optional_field or field_default is not None or fdesc.get("nullable"):
                ptype = Optional[ptype]
            if not (exclude_readonly and json_schema_extra.get("readOnly") is True):
                properties[fname] = annotation or ptype

        if fname in properties and not isinstance(properties[fname], tuple):
            fconfig["title"] = fname.replace("_", " ").title()
            description = comment or _br_it(fdesc.get("docstring") or fdesc["description"] or "")
            if description:
                fconfig["description"] = description
            ftype = properties[fname]
            if isinstance(ftype, PydanticDescriptorProxy):
                continue
            if is_optional_field or (field_default is not None and not callable(field_default)):
                properties[fname] = (ftype, Field(default=field_default, **fconfig))
            else:
                if (j := fconfig.get("json_schema_extra")) and (
                    (j.get("nullable") and not is_to_one_relation) or (exclude_readonly and j.get("readOnly"))
                ):
                    if field_type in (IntField, TextField):
                        fconfig["default"] = None
                    else:
                        fconfig["default_factory"] = lambda: None
                properties[fname] = (ftype, Field(**fconfig))

    # Here we endure that the name is unique, but complete objects are still labeled verbatim
    if not has_submodel:
        _name = name or f"{fqname}.leaf"
    elif has_submodel:
        _name = name or get_name()

    # Here we de-dup to ensure that a uniquely named object is a unique object
    # This fixes some Pydantic constraints.
    if _name in _MODEL_INDEX:
        return _MODEL_INDEX[_name]

    # Creating Pydantic class for the properties generated before
    properties["model_config"] = pconfig
    model = create_model(
        _name,
        __base__=PydanticModel,
        __module__=module,
        __validators__=validators,
        **properties,
    )
    # Copy the Model docstring over
    model.__doc__ = _cleandoc(cls)
    # Store the base class
    model.model_config["orig_model"] = cls  # type: ignore
    # Store model reference so we can de-dup it later on if needed.
    _MODEL_INDEX[_name] = model
    return model


def pydantic_queryset_creator(
    cls: "type[Model]",
    *,
    name=None,
    exclude: tuple[str, ...] = (),
    include: tuple[str, ...] = (),
    computed: tuple[str, ...] = (),
    allow_cycles: bool | None = None,
    sort_alphabetically: bool | None = None,
) -> type[PydanticListModel]:
    """
    Function to build a `Pydantic Model <https://pydantic-docs.helpmanual.io/usage/models/>`__ list off Tortoise Model.

    :param cls: The Tortoise Model to put in a list.
    :param name: Specify a custom name explicitly, instead of a generated name.

        The list generated name is currently naive and merely adds a "s" to the end
        of the singular name.
    :param exclude: Extra fields to exclude from the provided model.
    :param include: Extra fields to include from the provided model.
    :param computed: Extra computed fields to include from the provided model.
    :param allow_cycles: Do we allow any cycles in the generated model?
        This is only useful for recursive/self-referential models.

        A value of ``False`` (the default) will prevent any and all backtracking.
    :param sort_alphabetically: Sort the parameters alphabetically instead of Field-definition order.

        The default order would be:

            * Field definition order +
            * order of reverse relations (as discovered) +
            * order of computed functions (as provided).
    """

    submodel = pydantic_model_creator(
        cls,
        exclude=exclude,
        include=include,
        computed=computed,
        allow_cycles=allow_cycles,
        sort_alphabetically=sort_alphabetically,
        name=name,
    )
    lname = name or f"{submodel.__name__}_list"

    # Creating Pydantic class for the properties generated before
    model = create_model(
        lname,
        __base__=PydanticListModel,
        root=(list[submodel], Field(default_factory=list)),  # type: ignore
    )
    # Copy the Model docstring over
    model.__doc__ = _cleandoc(cls)
    # The title of the model to hide the hash postfix
    model.model_config["title"] = name or f"{submodel.model_config['title']}_list"
    model.model_config["submodel"] = submodel  # type: ignore
    return model
