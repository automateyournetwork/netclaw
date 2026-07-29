"""Read-only knowledge-base tools for the Halo MCP server (069).

Exposes Halo's KB articles (``/api/KBArticle``): a search-filtered list (summary
fields only) and a by-id detail read that includes the article body. Each core
function follows the shared convention (see ``tools/_common.py``).
"""

from models.responses import KBArticle
from tools._common import (
    _build_params,
    _list_result,
    _single_result,
    _upstream_error,
    _validation_error,
)
from utils.resolver import looks_like_id


async def halo_list_kb_articles(client, *, search=None, raw=False) -> str:
    """List KB articles, optionally filtered by a search term."""
    try:
        page = await client.get_all("/KBArticle", _build_params(search=search))
        return _list_result(page, KBArticle, raw=raw)
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)


async def halo_get_kb_article(client, *, article, raw=False) -> str:
    """Get a single KB article by numeric id, including its body."""
    if not looks_like_id(article):
        return _validation_error("article must be a numeric KB article id.")

    try:
        res = await client.get(f"/KBArticle/{article}", None)
        return _single_result(res, KBArticle, raw=raw, from_kwargs={"include_body": True})
    except Exception as exc:  # noqa: BLE001 - surface any client failure uniformly
        return _upstream_error(exc)
