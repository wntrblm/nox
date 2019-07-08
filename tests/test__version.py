from distutils.version import LooseVersion

import pytest

from nox import _version as _v


@pytest.mark.parametrize(
    "content,version",
    [
        ("needs_nox='1.0'\n", LooseVersion("1.0")),
        ('needs_nox="2.0"\n', LooseVersion("2.0")),
        ("needs_nox = '2019.1.2'  # some comment\n", LooseVersion("2019.1.2")),
        ("import nox\n\nneeds_nox = '3000'\n", LooseVersion("3000")),
    ],
)
def test_parse_needs_nox_parses_version_correctly(tmpdir, content, version):
    noxfile = tmpdir.join("noxfile.py")
    noxfile.write(content)
    parsed = _v.parse_needs_nox(str(noxfile))
    assert parsed == version


@pytest.mark.parametrize(
    "content",
    [
        ("needs_nox=\"1.0'\n",),  # non-matching quotes, invalid python
        ('needs_nox="""1.0"""\n',),  # no support for triple quote
        ("# some comment\n",),
        ("import nox\n\n@nox.session\ndef foo(session):\n    pass\n",),
    ],
)
def test_parse_needs_nox_returns_none_when_no_needs_nox(tmpdir, content):
    noxfile = tmpdir.join("noxfile.py")
    noxfile.write(content)
    parsed = _v.parse_needs_nox(str(noxfile))
    assert parsed is None


def test_parse_needs_nox_returns_none_when_noxfile_does_not_exist():
    noxfile = "does/not/exist/noxfile.py"
    parsed = _v.parse_needs_nox(noxfile)
    assert parsed is None


def test_needs_nox_calls_parse_needs_nox_when_no_module(tmpdir):
    noxfile = tmpdir.join("noxfile.py")
    noxfile.write("needs_nox = '3.2.1'\n")
    parsed = _v.needs_nox(str(noxfile))
    assert parsed == LooseVersion("3.2.1")


def test_needs_nox_returns_version_from_module():
    class Module:
        needs_nox = "1.2.3"

    needed = _v.needs_nox("not/important/noxfile.py", Module)
    assert needed == LooseVersion("1.2.3")


def test_needs_nox_returns_none_when_provided_module_does_not_have_it():
    class Module:
        pass

    needed = _v.needs_nox("not/important/noxfile.py", Module)
    assert needed is None


def test_is_version_sufficient_returns_true_for_lower_version():
    assert _v.is_version_sufficient("noxfile.py", "1.1.1") is True


def test_is_version_sufficient_returns_false_for_higher_version():
    assert _v.is_version_sufficient("noxfile.py", "3001.1.1") is False
