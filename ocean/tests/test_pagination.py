import os
from types import SimpleNamespace

import jinja2
import pytest

from ..app import pagination

ITEMS = [SimpleNamespace(name=name, size=size) for name, size in
         [("beta", 2), ("Alpha", None), ("gamma", 3), ("delta", 1)]]
SORT = {"name": lambda i: i.name, "size": lambda i: i.size}
SEARCH = [lambda i: i.name]


def names(page):
    return [item.name for item in page]


def test_pages_in_order_by_default():
    page = pagination.paginate(ITEMS, {}, per_page=25)
    assert names(page) == ["beta", "Alpha", "gamma", "delta"]
    assert (page.total, page.page, page.pages, page.first_index, page.last_index) == (4, 1, 1, 1, 4)


def test_sorts_case_insensitively_with_none_last():
    assert names(pagination.paginate(ITEMS, {"sort": "name"}, sort=SORT)) == ["Alpha", "beta", "delta", "gamma"]
    assert names(pagination.paginate(ITEMS, {"sort": "size"}, sort=SORT)) == ["delta", "beta", "gamma", "Alpha"]
    assert names(pagination.paginate(ITEMS, {"sort": "name", "direction": "desc"}, sort=SORT)) == ["gamma", "delta", "beta", "Alpha"]


def test_default_sort_and_unknown_sort_column():
    page = pagination.paginate(ITEMS, {"sort": "not-a-column"}, sort=SORT, default_sort="name")
    assert page.sort == "name"
    assert names(page) == ["Alpha", "beta", "delta", "gamma"]


def test_search_is_case_insensitive_and_counts_matches():
    page = pagination.paginate(ITEMS, {"q": "  A "}, search=SEARCH)
    assert page.search == "A"
    assert names(page) == ["beta", "Alpha", "gamma", "delta"]
    page = pagination.paginate(ITEMS, {"q": "ALP"}, search=SEARCH)
    assert names(page) == ["Alpha"] and page.total == 1


def test_search_ignored_when_list_is_not_searchable():
    page = pagination.paginate(ITEMS, {"q": "alp"})
    assert page.total == 4 and page.search == "" and not page.searchable


def test_pages_and_clamps_page_numbers():
    items = list(range(60))
    page = pagination.paginate(items, {"page": "2"}, per_page=25)
    assert list(page) == list(range(25, 50))
    assert (page.pages, page.first_index, page.last_index) == (3, 26, 50)
    assert list(pagination.paginate(items, {"page": "99"}, per_page=25)) == list(range(50, 60))
    assert list(pagination.paginate(items, {"page": "-1"}, per_page=25)) == list(range(25))
    assert list(pagination.paginate(items, {"page": "x"}, per_page=25)) == list(range(25))


def test_per_page_is_one_of_the_options():
    items = list(range(300))
    assert pagination.paginate(items, {"per_page": "100"}).per_page == 100
    assert pagination.paginate(items, {"per_page": "99999"}).per_page == 500
    assert pagination.paginate(items, {"per_page": "abc"}, per_page=50).per_page == 50
    assert pagination.paginate(items, {}, per_page=30).per_page == 25


def test_prefix_keeps_lists_independent():
    args = {"a_page": "2", "b_page": "3"}
    assert pagination.paginate(range(100), args, prefix="a_", per_page=25).page == 2
    assert pagination.paginate(range(100), args, prefix="b_", per_page=25).page == 3
    assert pagination.paginate(range(100), args, prefix="c_", per_page=25).page == 1


def test_empty_list():
    page = pagination.paginate([], {"page": "3"})
    assert not page
    assert (page.total, page.page, page.pages, page.first_index, page.last_index) == (0, 1, 1, 0, 0)


### Templates ###
# There are no browser tests, so at least check that every template compiles.

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "templates")


@pytest.mark.parametrize("template", sorted(
    os.path.relpath(os.path.join(root, f), TEMPLATES)
    for root, _, files in os.walk(TEMPLATES) for f in files if f.endswith(".html")))
def test_template_compiles(template):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES), extensions=["jinja2.ext.do"])
    env.get_template(template)
