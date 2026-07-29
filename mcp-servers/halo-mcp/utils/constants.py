"""Constants and vocabulary notes for the Halo MCP server (069).

Halo's REST API uses internal names that differ from the product UI. Encoding
them here so the rest of the code (and future maintainers) aren't surprised:

    tickets        -> "Faults"
    ticket types   -> "Request Types"
                      (the LIST filter is ``requesttype_id``, but a ticket's own
                       field and the create payload use ``tickettype_id``)
    assets         -> "Devices"
    custom fields  -> defined by ``FieldInfo``; the same numeric id is used as
                      ``FieldInfo.id`` (definition), ``CustomField.id`` (value on
                      a ticket) and ``RequestTypeField.fieldid`` (placement on a
                      ticket type).

Every ``/api/*`` call requires ``Authorization: Bearer <token>``; the token is
obtained from the auth server (``<base>/auth/token``), which is a different path
from the resource API (``<base>/api``).
"""

# Path prefix for all resource endpoints (appended to HALO_BASE_URL by the client).
API_PREFIX = "/api"

# Auth-server token path (hosted default; appended to HALO_BASE_URL).
AUTH_TOKEN_PATH = "/auth/token"

# Default OAuth2 scope for a client-credentials application.
DEFAULT_SCOPE = "all"

# Default page size for paginated list endpoints (Halo's server cap is 100).
DEFAULT_PAGE_SIZE = 50

# Default cap on pages fetched per list call (truncation guard).
DEFAULT_MAX_PAGES = 20

# Default per-request timeout (seconds).
DEFAULT_TIMEOUT = 30
