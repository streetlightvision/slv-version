import pytest
from version import parse_version


def test_version():
    a = '1.0.0#1-rc1'
    b = parse_version(a)
    c = parse_version(b)
    assert a != b
    assert b == c


def test_bad():
    with pytest.raises(ValueError):
        parse_version('foo')
