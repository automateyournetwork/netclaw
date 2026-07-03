# Image and pagination guidance

## Images

Use `eve_list_images` first. Filter by `node_type` when possible.

## Pagination

Use `page` and `page_size` on list-heavy reads. Prefer bounded reads such as `page_size=25` or `50` instead of full inventory dumps.
