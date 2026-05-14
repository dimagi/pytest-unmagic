"""pytest-django interop for unmagic fixtures.

This module is a no-op when pytest-django is not installed or not
loaded. It is imported unconditionally by `unmagic.fixtures`; all
behavior is gated on `is_pytest_django_loaded(config)`.
"""

# Name registered by pytest-django's pytest11 entry point
# (`pytest11 = django = pytest_django.plugin`).
_PYTEST_DJANGO_PLUGIN_NAME = "django"


def is_pytest_django_loaded(config):
    """Return True if pytest-django is registered with the pytest config."""
    return config.pluginmanager.hasplugin(_PYTEST_DJANGO_PLUGIN_NAME)


def inject_fixturenames(item, fixtures):
    """Surface @use'd pytest-fixture names on the test item.

    pytest-django decides at collection time whether to set up the
    test database by scanning each item's `fixturenames` (and
    django_db markers). Because unmagic resolves @use'd fixtures
    lazily via `getfixturevalue`, those names are absent from
    `fixturenames` at collection time.

    For every pytest-fixture name in the transitive @use graph of
    `fixtures`, append it to `item.fixturenames` if not already
    present. Unmagic-native fixtures (whose `_id` is a `_UnmagicID`,
    not a plain str) are skipped — pytest-django does not look for
    those names.
    """
    if not is_pytest_django_loaded(item.config):
        return
    names = item.fixturenames
    for fix in fixtures:
        fid = getattr(fix, "_id", None)
        if _is_pytest_fixture_id(fid) and fid not in names:
            names.append(fid)


def _is_pytest_fixture_id(fid):
    # PytestFixture stores a plain str as _id; UnmagicFixture stores a
    # _UnmagicID (str subclass with identity equality) which is
    # intentionally not what pytest-django looks for. `type(x) is str`
    # — not `isinstance` — is the discriminator.
    return type(fid) is str


# pytest-django fixture names whose resolution implies the test DB
# must already be set up for the session. These are the names
# pytest-django itself checks for at collection time (see
# pytest_django/plugin.py::_get_databases_for_test).
_DB_FIXTURE_NAMES = frozenset({
    "db",
    "transactional_db",
    "django_db_reset_sequences",
    "django_db_serialized_rollback",
    "live_server",
})


def guard_pytest_fixture_access(name, request):
    """Raise if a pytest-django DB fixture is resolved without
    declaration.

    Called from `PytestFixture._get_value` before delegating to
    `request.getfixturevalue`. If pytest-django is not loaded, or
    the fixture is not one of the DB-triggering ones, this is a
    no-op.

    The signal that DB setup was planned: either the name is in the
    test item's `fixturenames` (which `inject_fixturenames` arranges
    for any @use'd DB fixture), or the item carries a `django_db`
    marker. Absence of both means pytest-django did not invoke
    `setup_databases()` and using the fixture would either error
    inside pytest-django's blocker or fall through to the dev DB.

    Limitations:
    - This guard assumes ``request.node`` is the test item. For the
      `@use(...)` flow that is always the case, but if a future caller
      resolves ``PytestFixture`` from a non-test request, ``fixturenames``
      and ``get_closest_marker`` may not reflect the test's collection-time
      state.
    - Multi-database setups (``@pytest.mark.django_db(databases=[...])``)
      are not introspected. A ``django_db`` marker on the item, regardless
      of its ``databases`` list, is treated as evidence that DB setup was
      planned.
    """
    if name not in _DB_FIXTURE_NAMES:
        return
    if not is_pytest_django_loaded(request.config):
        return
    node = request.node
    if name in node.fixturenames:
        return
    if node.get_closest_marker("django_db") is not None:
        return
    raise RuntimeError(
        f"pytest-django fixture {name!r} was resolved, but "
        f"pytest-django did not set up the test database for this "
        f"session. Declare the dependency with @use({name!r}) on "
        f"the test or on a fixture in its @use chain, or apply "
        f"@pytest.mark.django_db to the test."
    )
