from .util import get_source, unmagic_tester


def test_autouse_module_fixture():
    @get_source
    def test_py():
        from unmagic import autouse, fixture, get_request

        def test_one():
            pass

        def test_two():
            pass

        def test_three():
            pass

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("\n", " ".join(traces))

        @fixture
        def test_name():
            name = get_request().node.name.replace("test_", "")
            yield
            ss_tracer().append(name)

        autouse(test_name, __file__)

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " one two three"
    ])
    result.assert_outcomes(passed=3)


def test_autouse_package_fixture():
    @get_source
    def fix_py():
        from unmagic import fixture

        @fixture(scope="session")
        def ss_tracer():
            traces = []
            yield traces
            print("\n", " ".join(traces))

    @get_source
    def init_py():
        from unmagic import autouse, fixture, get_request
        from fix import ss_tracer

        @fixture(scope="package")
        def pkg_fix():
            name = get_request().node.nodeid.replace("/", ".")
            traces = ss_tracer()
            traces.append(f"{name}-a")
            yield
            traces.append(f"{name}-z")

        autouse(pkg_fix, __file__)

    @get_source
    def mod_py():
        from unmagic import fixture
        from fix import ss_tracer

        @fixture
        def modname():
            yield __name__.rsplit(".", 1)[-1].replace("test_mod", "m")

        def test_one():
            ss_tracer().append(f"{modname()}.t1")

        def test_two():
            ss_tracer().append(f"{modname()}.t2")

    pytester = unmagic_tester()
    (pytester.path / "pkg/sub").mkdir(parents=True)
    (pytester.path / "pkg/sub/__init__.py").write_text(init_py)
    (pytester.path / "pkg/sub/test_mod0.py").write_text(mod_py)

    (pytester.path / "pkg/__init__.py").write_text(init_py)
    (pytester.path / "pkg/test_mod1.py").write_text(mod_py)
    (pytester.path / "pkg/test_mod2.py").write_text(mod_py)

    (pytester.path / "pkg/up").mkdir()
    (pytester.path / "pkg/up/__init__.py").write_text(init_py)
    (pytester.path / "pkg/up/test_mod3.py").write_text(mod_py)

    (pytester.path / "test_mod4.py").write_text(mod_py)
    (pytester.path / "fix.py").write_text(fix_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " pkg-a"
        " pkg.sub-a m0.t1 m0.t2 pkg.sub-z"
        " m1.t1 m1.t2 m2.t1 m2.t2"
        " pkg.up-a m3.t1 m3.t2 pkg.up-z"
        " pkg-z"
        " m4.t1 m4.t2"
    ])
    result.assert_outcomes(passed=10)


def test_use_on_autouse_fixture():
    @get_source
    def test_py():
        import pytest
        from unmagic import fixture

        traces = []

        @fixture(scope="session")
        def trace():
            traces.append("tracing...")
            yield

        with pytest.raises(TypeError, match="Cannot apply @use to autouse"):
            @trace
            @fixture(autouse=True)
            def use_autouse():
                traces.append("autoused")
                yield

        def test():
            assert traces == ["autoused"]

    pytester = unmagic_tester()
    pytester.makepyfile(test_py)
    result = pytester.runpytest("-s")
    result.assert_outcomes(passed=1)


def test_autouse_conftest_fixture():

    @get_source
    def test_py():
        from conftest import ss_tracer

        def test_one():
            ss_tracer().append("t1")

        def test_two():
            ss_tracer().append("t2")

    pytester = unmagic_tester()
    pytester.makepyfile(conftest=plug_py, test_it=test_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([" a t1 z a t2 z"])
    result.assert_outcomes(passed=2)


def test_autouse_plugin_fixture():

    @get_source
    def test_py():
        from plug import ss_tracer

        def test_one():
            ss_tracer().append("t1")

        def test_two():
            ss_tracer().append("t2")

    pytester = unmagic_tester()
    pytester.makeini('[pytest]\npythonpath = .\n')
    pytester.makepyfile(plug=plug_py, test_it=test_py)

    result = pytester.runpytest("-s", "-pplug")
    result.stdout.fnmatch_lines([" a t1 z a t2 z"])
    result.assert_outcomes(passed=2)


def test_autouse_warns_in_runtest_phase():

    @get_source
    def test_py():
        from unmagic import autouse
        from conftest import ss_tracer, autofix

        def test_one():
            autouse(autofix, True)
            ss_tracer().append("t1")

    conftest = plug_py.replace("(autouse=True)", "")
    pytester = unmagic_tester()
    pytester.makepyfile(conftest=conftest, test_it=test_py)

    result = pytester.runpytest("-s")
    result.stdout.fnmatch_lines([
        " t1",
        "*UserWarning: autouse fixture registered while running tests*",
    ])
    result.assert_outcomes(passed=1)


@get_source
def plug_py():
    from unmagic import fixture

    @fixture(scope="session")
    def ss_tracer():
        traces = []
        yield traces
        print("\n", " ".join(traces))

    @fixture(autouse=True)
    def autofix():
        traces = ss_tracer()
        traces.append("a")
        yield
        traces.append("z")
