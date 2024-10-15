from .util import get_source, unmagic_tester


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

    pytester = unmagic_tester()
    pytester.makeconftest(conftest)
    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s")
    result.assert_outcomes(passed=1)


def test_no_active_request_error():
    @get_source
    def conftest():
        import pytest
        from unmagic.scope import get_request

        calls = []

        def pytest_runtestloop():
            with pytest.raises(ValueError, match="no active request"):
                get_request()
            calls.append("run")

    @get_source
    def test_py():
        from conftest import calls

        def test():
            assert calls == ["run"]

    pytester = unmagic_tester()
    pytester.makeconftest(conftest)
    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s")
    result.assert_outcomes(passed=1)
