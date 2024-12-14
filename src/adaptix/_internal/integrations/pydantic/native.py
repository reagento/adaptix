from collections.abc import Mapping
from typing import Any, Callable, Literal, Optional, TypeVar, Union

from ...common import Dumper, Loader
from ...morphing.load_error import LoadError
from ...morphing.provider_template import DumperProvider, LoaderProvider
from ...morphing.request_cls import DumperRequest, LoaderRequest
from ...provider.essential import Mediator, Provider
from ...provider.facade.provider import bound_by_any
from ...provider.loc_stack_filtering import Pred
from ...utils import Omittable, Omitted

try:
    from pydantic import ConfigDict, TypeAdapter, ValidationError
    from pydantic.main import IncEx
except ImportError:
    pass


T = TypeVar("T")


class NativePydanticProvider(LoaderProvider, DumperProvider):
    def __init__(
        self,
        config: Optional["ConfigDict"],
        validation_params: Mapping[str, Omittable[Any]],
        serialization_params: Mapping[str, Omittable[Any]],
    ):
        self._config = config
        self._validation_params = validation_params
        self._serialization_params = serialization_params

    def _skip_omitted(self, mapping: Mapping[str, T]) -> Mapping[str, T]:
        return {k: v for k, v in mapping.items() if v != Omitted()}

    def provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        validation_params = self._skip_omitted(self._validation_params)
        validator = TypeAdapter(request.last_loc.type, config=self._config).validator.validate_python

        if not validation_params:
            def native_pydantic_loader_no_params(data):
                try:
                    return validator(data)
                except ValidationError as e:
                    raise LoadError from e

            return native_pydantic_loader_no_params

        def native_pydantic_loader(data):
            try:
                return validator(data, **validation_params)
            except ValidationError as e:
                raise LoadError from e

        return native_pydantic_loader

    def provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        serialization_params = self._skip_omitted(self._serialization_params)
        serializer = TypeAdapter(request.last_loc.type, config=self._config).serializer.to_python

        if not serialization_params:
            return serializer

        def native_pydantic_dumper(data):
            return serializer(data, **serialization_params)

        return native_pydantic_dumper


def native_pydantic(
    *preds: Pred,
    # loading (validation) parameters
    strict: Omittable[Optional[bool]] = Omitted(),
    from_attributes: Omittable[Optional[bool]] = Omitted(),
    self_instance: Omittable[Any] = Omitted(),
    allow_partial: Omittable[Union[bool, Literal["off", "on", "trailing-strings"]]] = Omitted(),
    # dumping (serialization) parameters
    mode: Omittable[Union[Literal["json", "python"], str]] = Omitted(),  # noqa: PYI051
    include: Omittable["IncEx"] = Omitted(),
    exclude: Omittable["IncEx"] = Omitted(),
    by_alias: Omittable[bool] = Omitted(),
    exclude_unset: Omittable[bool] = Omitted(),
    exclude_defaults: Omittable[bool] = Omitted(),
    exclude_none: Omittable[bool] = Omitted(),
    round_trip: Omittable[bool] = Omitted(),
    warnings: Omittable[Union[bool, Literal["none", "warn", "error"]]] = Omitted(),
    fallback: Omittable[Callable[[Any], Any]] = Omitted(),
    serialize_as_any: Omittable[bool] = Omitted(),
    # common parameters
    context: Omittable[Optional[dict[str, Any]]] = Omitted(),
    config: Optional["ConfigDict"] = None,
) -> Provider:
    """Provider that represents value via pydantic.
    You can use this function to validate or serialize pydantic models via pydantic itself.
    Provider constructs ``TypeAdapter`` for a type to load and dump data.

    :param preds: Predicates specifying where the provider should be used.
        The provider will be applied if any predicates meet the conditions,
        if no predicates are passed, the provider will be used for all Enums.
        See :ref:`predicate-system` for details.

    :param strict: Parameter passed directly to ``.validate_python()`` method
    :param from_attributes: Parameter passed directly to ``.validate_python()`` method
    :param self_instance: Parameter passed directly to ``.validate_python()`` method
    :param allow_partial: Parameter passed directly to ``.validate_python()`` method

    :param mode: Parameter passed directly to ``.to_python()`` method
    :param include: Parameter passed directly to ``.to_python()`` method
    :param exclude: Parameter passed directly to ``.to_python()`` method
    :param by_alias: Parameter passed directly to ``.to_python()`` method
    :param exclude_unset: Parameter passed directly to ``.to_python()`` method
    :param exclude_defaults: Parameter passed directly to ``.to_python()`` method
    :param exclude_none: Parameter passed directly to ``.to_python()`` method
    :param round_trip: Parameter passed directly to ``.to_python()`` method
    :param warnings: Parameter passed directly to ``.to_python()`` method
    :param fallback: Parameter passed directly to ``.to_python()`` method
    :param serialize_as_any: Parameter passed directly to ``.to_python()`` method

    :param context: Parameter passed directly to ``.validate_python()`` and ``.to_python()`` methods
    :param config: Parameter passed directly to ``config`` parameter of ``TypeAdapter`` constructor

    :return: Desired provider
    """
    return bound_by_any(
        preds,
        NativePydanticProvider(
            config=config,
            validation_params={
                "strict": strict,
                "from_attributes": from_attributes,
                "self_instance": self_instance,
                "allow_partial": allow_partial,
                "context": context,
            },
            serialization_params={
                "mode": mode,
                "include": include,
                "exclude": exclude,
                "by_alias": by_alias,
                "exclude_unset": exclude_unset,
                "exclude_defaults": exclude_defaults,
                "exclude_none": exclude_none,
                "round_trip": round_trip,
                "warnings": warnings,
                "fallback": fallback,
                "serialize_as_any": serialize_as_any,
                "context": context,
            },
        ),
    )
