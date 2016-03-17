import pytest
from version import version_maven


@pytest.mark.parametrize("args, expected", [
    ((None, 'master', 0), '0.0.0'),
    ((None, 'master', 1), '0.1.0-SNAPSHOT'),
    ((None, 'slv-42', 0), '0-SLV42-SNAPSHOT'),
    ((None, 'slv-42', 1), '0-SLV42-SNAPSHOT'),
    (('1.2.3', 'master', 0), '1.2.3'),
    (('1.2.3', 'master', 1), '1.3.0-SNAPSHOT'),
    (('1.2.3-rc1', 'master', 0), '1.2.3-RC1'),
    (('1.2.3-rc1', 'master', 1), '1.3.0-RC1-SNAPSHOT'),
    (('1.2.3-rc1.post1', 'master', 0), '1.2.3-RC1-POST1'),
    (('1.2.3-rc1.dev1', 'master', 0), '1.2.3-RC1-DEV1')
])
def test_maven(args, expected):
    assert version_maven(*args) == expected
