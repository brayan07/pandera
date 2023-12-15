"""Pandera type annotations for Dask."""
import functools
from typing import TYPE_CHECKING, Generic, TypeVar, Any, get_args

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from pandera.engines import PYDANTIC_V2
from pandera.errors import SchemaInitError, SchemaError
from pandera.typing.common import (
    DataFrameBase,
    GenericDtype,
    IndexBase,
    SeriesBase,
)
from pandera.typing.pandas import DataFrameModel, _GenericAlias

try:
    import pyspark.pandas as ps

    PYSPARK_INSTALLED = True
except ImportError:  # pragma: no cover
    PYSPARK_INSTALLED = False


# pylint:disable=invalid-name
if TYPE_CHECKING:
    T = TypeVar("T")  # pragma: no cover
else:
    T = DataFrameModel


class _PydanticIntegrationMixIn:
    """Mixin class for pydantic integration with pyspark DataFrames"""

    @classmethod
    def _get_schema_model(cls, field):
        if not field.sub_fields:
            raise TypeError(
                "Expected a typed pandera.typing.DataFrame,"
                " e.g. DataFrame[Schema]"
            )
        schema_model = field.sub_fields[0].type_
        return schema_model

    if PYDANTIC_V2:

        @classmethod
        def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            schema_model = get_args(_source_type)[0]
            return core_schema.no_info_plain_validator_function(
                functools.partial(
                    cls.pydantic_validate,
                    schema_model=schema_model,
                ),
            )

    else:

        @classmethod
        def __get_validators__(cls):
            yield cls._pydantic_validate

    @classmethod
    def pydantic_validate(cls, obj: Any, schema_model) -> ps.DataFrame:
        """
        Verify that the input can be converted into a pandas dataframe that
        meets all schema requirements.

        This is for pydantic >= v2
        """
        try:
            schema = schema_model.to_schema()
        except SchemaInitError as exc:
            raise ValueError(
                f"Cannot use {cls.__name__} as a pydantic type as its "
                "DataFrameModel cannot be converted to a DataFrameSchema.\n"
                f"Please revisit the model to address the following errors:"
                f"\n{exc}"
            ) from exc

        try:
            valid_data = schema.validate(obj, lazy=False)
        except SchemaError as exc:
            raise ValueError(str(exc)) from exc

        return valid_data

    @classmethod
    def _pydantic_validate(cls, obj: Any, field) -> ps.DataFrame:
        """
        Verify that the input can be converted into a pandas dataframe that
        meets all schema requirements.

        This is for pydantic < v1
        """
        schema_model = cls._get_schema_model(field)
        return cls.pydantic_validate(obj, schema_model)


if PYSPARK_INSTALLED:
    # pylint: disable=too-few-public-methods,arguments-renamed

    class DataFrame(
        DataFrameBase, _PydanticIntegrationMixIn, ps.DataFrame, Generic[T]
    ):
        """
        Representation of dask.dataframe.DataFrame, only used for type
        annotation.

        *new in 0.8.0*
        """

        def __class_getitem__(cls, item):
            """Define this to override's pyspark.pandas generic type."""
            return _GenericAlias(cls, item)

    # pylint:disable=too-few-public-methods,arguments-renamed
    class Series(SeriesBase, ps.Series, Generic[GenericDtype]):  # type: ignore [misc]  # noqa
        """Representation of pandas.Series, only used for type annotation.

        *new in 0.8.0*
        """

        def __class_getitem__(cls, item):
            """Define this to override pyspark.pandas generic type"""
            return _GenericAlias(cls, item)

    # pylint:disable=too-few-public-methods
    class Index(IndexBase, ps.Index, Generic[GenericDtype]):
        """Representation of pandas.Index, only used for type annotation.

        *new in 0.8.0*
        """
