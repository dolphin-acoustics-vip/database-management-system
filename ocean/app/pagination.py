# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

"""Searching, sorting and paging the lists shown on OCEAN's pages.

A route passes the full list to `paginate`, which reads the user's choices from the query
string and returns a `Page` for the template. The template shows it with the macros in
`templates/partials/ui.html` (`search_box`, `sortable_header` and `pagination`).

Lists are paged in Python, after they have been loaded, because most of them come from
`database_handler.create_system_time_request`, which also supports archive mode.

Several lists can share a page: give each a different `prefix`, so that, for example, the
query string `rec_page=2&sel_page=3` pages two lists independently.
"""

import math

PER_PAGE_OPTIONS = (25, 50, 100, 200, 500)


class Page:
    """One page of a list, with the search, sort and page choices that produced it."""

    def __init__(self, items, total, page, per_page, prefix, search, sort, direction, searchable, sortable):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.prefix = prefix
        self.search = search
        self.sort = sort
        self.direction = direction
        self.searchable = searchable
        self.sortable = sortable

    @property
    def pages(self):
        return max(1, math.ceil(self.total / self.per_page))

    @property
    def first_index(self):
        """The 1-based position of the first item on this page (0 if the list is empty)."""
        return (self.page - 1) * self.per_page + 1 if self.total else 0

    @property
    def last_index(self):
        return min(self.page * self.per_page, self.total)

    def arg(self, name):
        """The query string parameter for `name` (e.g. 'page' -> 'rec_page')."""
        return self.prefix + name

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __bool__(self):
        return self.total > 0


def _sort_key(value):
    """Sort None last, and text without regard to case."""
    if value is None: return (1, "")
    if isinstance(value, str): return (0, value.lower())
    return (0, value)


def paginate(items, args, prefix="", per_page=50, search=None, sort=None, default_sort=None, default_direction="asc"):
    """Search, sort and page `items` using the query string `args` (e.g. `flask.request.args`).

    :param items: the full list of items
    :param args: the query string parameters
    :param prefix: prefix for this list's query parameters (`q`, `sort`, `direction`, `page`, `per_page`)
    :param per_page: the default number of items per page
    :param search: functions returning the text of an item to search (the list is not searchable if None)
    :param sort: {column name: function returning the value of an item to sort by}
    :param default_sort: the column to sort by if the user has not chosen one (None keeps the list's order)
    :param default_direction: 'asc' or 'desc'
    :return: a `Page`
    """
    items = list(items)
    sort = sort or {}

    query = (args.get(prefix + "q") or "").strip() if search else ""
    if query:
        needle = query.lower()
        items = [item for item in items if any(needle in str(f(item) or "").lower() for f in search)]

    column = args.get(prefix + "sort")
    if column not in sort: column = default_sort
    direction = args.get(prefix + "direction")
    if direction not in ("asc", "desc"): direction = default_direction
    if column in sort:
        items.sort(key=lambda item: _sort_key(sort[column](item)), reverse=direction == "desc")

    try:
        per_page = int(args.get(prefix + "per_page", per_page))
    except (TypeError, ValueError):
        pass
    if per_page not in PER_PAGE_OPTIONS:
        per_page = min(PER_PAGE_OPTIONS, key=lambda option: abs(option - per_page))

    total = len(items)
    pages = max(1, math.ceil(total / per_page))
    try:
        page = int(args.get(prefix + "page", 1))
    except (TypeError, ValueError):
        page = 1
    page = min(max(page, 1), pages)

    start = (page - 1) * per_page
    return Page(items[start:start + per_page], total, page, per_page, prefix, query, column if column in sort else None,
                direction, searchable=bool(search), sortable=set(sort))
