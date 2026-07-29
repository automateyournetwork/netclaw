"""Field-definition (``FieldInfo``) tools.

The same numeric id is used as ``FieldInfo.id`` (definition), ``CustomField.id``
(a value carried on a ticket/asset) and ``RequestTypeField.fieldid`` (placement
on a ticket type), so a field looked up here can be written back by id in a
change-request ``customfields[]`` entry.
"""

from models.responses import FieldInfo
from tools._common import (
    _build_params,
    _list_result,
    _single_result,
    _upstream_error,
    _validation_error,
)
from utils.resolver import looks_like_id


async def halo_list_fields(client, *, custom_only=None, raw=False) -> str:
    """List field definitions (``/FieldInfo``), values included."""
    try:
        params = _build_params(
            includevalues="true",
            iscustomfieldsetup=("true" if custom_only else None),
        )
        page = await client.get_all("/FieldInfo", params)
        return _list_result(page, FieldInfo, raw=raw)
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)


async def halo_get_field(client, *, field, raw=False) -> str:
    """Read one field definition by its numeric ``FieldInfo`` id."""
    if not looks_like_id(field):
        return _validation_error("field must be a numeric FieldInfo id")
    try:
        res = await client.get(
            f"/FieldInfo/{field}", _build_params(getlookupvalues="true")
        )
        return _single_result(res, FieldInfo, raw=raw)
    except Exception as exc:  # noqa: BLE001 - uniform upstream surfacing
        return _upstream_error(exc)
