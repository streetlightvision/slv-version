import os.path
import pytest
import subprocess
import tempfile

here = os.path.dirname(os.path.abspath(__file__))


def shell(cmd, **kwargs):
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('stderr', subprocess.PIPE)
    proc = subprocess.Popen(cmd, **kwargs)
    stdout, stderr = proc.communicate()
    return stdout, stderr


def _repo(request, script):
    data_dir = tempfile.mkdtemp()
    shell(['sh', os.path.join(here, script)], cwd=data_dir)

    def fin():
        shell(['rm', '-rf', data_dir])
    request.addfinalizer(fin)

    return Repository(data_dir)


@pytest.fixture(scope='function')
def repository(request):
    return _repo(request, 'repo.sh')


@pytest.fixture(scope='function')
def fresh(request):
    return _repo(request, 'fresh.sh')


@pytest.fixture(scope='function')
def bare(request):
    return _repo(request, 'bare.sh')


@pytest.fixture(scope='function')
def nonrepo(request):
    return _repo(request, 'nonrepo.sh')


@pytest.fixture(scope='function')
def dirty(request):
    return _repo(request, 'dirty.sh')


class Repository(object):

    def __init__(self, repository_dir):
        self.repository_dir = repository_dir

    def __str__(self):
        return "%s" % self.repository_dir
