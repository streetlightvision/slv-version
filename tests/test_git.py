import pytest
from version import audit_git, Repository


def test_git(repository):
    response = audit_git(repository.repository_dir)
    assert isinstance(response, Repository)
    assert str(response).startswith("<Repository(branch=")


def test_bare(bare):
    with pytest.raises(RuntimeError):
        response = audit_git(bare.repository_dir)


def test_nonrepo(nonrepo):
    with pytest.raises(RuntimeError):
        response = audit_git(nonrepo.repository_dir)


@pytest.mark.xfail(reason="works with recent git")
def test_dirty(dirty):
    response = audit_git(dirty.repository_dir)
    assert response.dirty is True


def test_fresh(fresh):
    response = audit_git(fresh.repository_dir)
    assert response.closest_tag is None
    assert response.distance
