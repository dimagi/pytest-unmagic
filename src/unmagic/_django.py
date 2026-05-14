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
