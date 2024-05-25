from unmagic import get_fixture_value

from .util import get_source


def test_no_active_session_error():
    @get_source
    def conftest():
        import pytest
        from unmagic.scope import get_active

        calls = []

        @pytest.hookimpl(tryfirst=True)
        def pytest_sessionstart(session):
            with pytest.raises(ValueError, match="no active pytest session"):
                print(get_active(session))
            calls.append("configure")

    @get_source
    def test_py():
        from conftest import calls

        def test():
            assert calls == ["configure"]

    pytester = get_fixture_value("pytester")
    pytester.makeconftest(conftest)
    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s", "-punmagic.scope")
    result.assert_outcomes(passed=1)


def test_no_active_request_error():
    @get_source
    def conftest():
        import pytest
        from unmagic import get_fixture_value

        calls = []

        def pytest_runtestloop():
            with pytest.raises(ValueError, match="no active pytest request"):
                get_fixture_value("request")
            calls.append("run")

    @get_source
    def test_py():
        from conftest import calls

        def test():
            assert calls == ["run"]

    pytester = get_fixture_value("pytester")
    pytester.makeconftest(conftest)
    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s", "-punmagic.scope")
    result.assert_outcomes(passed=1)
