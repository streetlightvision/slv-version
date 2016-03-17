import pytest
from version import version_rpm, RPMVersion

@pytest.mark.parametrize("args, expected", [
    ((None, 42, 'el14'), '0.0.0-42.el14'),
    (('1.2.3-beta', 42, 'el14'), '1.2.3-0.42.b0.el14'),
    (('1.2.3-post', 42, 'el14'), '1.2.3-42.post0.el14'),
    (('1.2.3#1', 42, None), '1.3.0-0.42.a1'),
    (('1.2.3.dev1', 42, None), '1.2.3-42.dev1'),
    (('1.2.3.rc1.dev1', 42, None), '1.2.3-0.42.rc1.dev1'),
    (('1.2.3.post1', 42, None), '1.2.3-42.post1'),
    (('1.2.3.rc1.post1', 42, None), '1.2.3-0.42.rc1.post1'),
])
def test_rpm(args, expected):
    assert version_rpm(*args) == expected


@pytest.mark.parametrize("version, expected", [
    (RPMVersion('1.2.3'), RPMVersion('1.2.3')),
    (RPMVersion('1.2.3'), '1.2.3'),
    ('1.2.3', RPMVersion('1.2.3')),
])
def test_version(version, expected):
    assert version == expected
