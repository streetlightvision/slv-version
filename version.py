#!/usr/bin/env python

"""
    Defines rpm and maven version from git tag, branch and other metadata

    the tag must be semver + release
"""

from __future__ import print_function
import argparse
import json
import re
import subprocess
import sys
from pkg_resources import parse_version as pv
from pkg_resources import SetuptoolsVersion


class Result:

    def __init__(self, proc, stdout, stderr):
        self.proc = proc
        self.stdout = stdout
        self.stderr = stderr

    @property
    def returncode(self):
        return self.proc.returncode


class Repository:

    def __init__(self, **opts):
        self.branch = None
        self.closest_tag = None
        self.dirty = None
        self.distance = None
        self.short = None

        for key, value in opts.items():
            setattr(self, key.replace('-', '_'), value)

    def __str__(self):
        attrs = ['%s=%r' % (key, value) for key, value in self.__dict__.items()]
        return '<%s(%s)>' % (self.__class__.__name__, ', '.join(sorted(attrs)))


def shell(*args, **kwargs):
    if isinstance(args[0], str):
        kwargs.setdefault('shell', True)
    kwargs.setdefault('stdout', subprocess.PIPE)
    kwargs.setdefault('stderr', subprocess.PIPE)

    proc = subprocess.Popen(*args, **kwargs)
    stdout, stderr = proc.communicate()
    if kwargs.get('stdout', None) == subprocess.PIPE:
        stdout = stdout.decode('utf-8').strip()
    if kwargs.get('stderr', None) == subprocess.PIPE:
        stderr = stderr.decode('utf-8').strip()
    result = Result(proc, stdout, stderr)
    return result


def audit_git(directory=None):
    result = shell('git config core.bare', cwd=directory)
    if 'true' in result.stdout:
        raise RuntimeError('Cannot work on a bare repository')
    elif result.returncode:
        raise RuntimeError(result.stderr or 'Some error occured')

    pieces = {key: value for key, value in git_attributes(directory)}
    return Repository(**pieces)


def git_attributes(directory=None):
    result = shell('git describe --tags --always --long --dirty', cwd=directory)
    description = result.stdout
    if description.endswith('-dirty'):
        description = description[:-6]
        yield 'dirty', True
    if '-g' in description:
        # in the format: TAG-DISTANCE-gSHORT
        a, b, c = description.rsplit('-', 2)
        yield 'closest-tag', a
        yield 'distance', int(b)
        yield 'short', c[1:]
    else:
        result = shell('git rev-list HEAD --count', cwd=directory)
        yield 'distance', int(result.stdout)
        yield 'short', description

    result = shell('git symbolic-ref --short HEAD', cwd=directory)
    yield 'branch', result.stdout


def parse_version(version):
    """
    >>> parse_version('foo')
    Traceback (most recent call last):
    ...
    Exception: Bad version foo
    >>> parse_version('0.0.0-foo')
    Traceback (most recent call last):
    ...
    Exception: Bad version 0.0.0-foo
    """
    if isinstance(version, SetuptoolsVersion):
        return version
    matches = re.match('(?P<release>(\d+(\.\d+)+))#(?P<remains>.+)?$', version)
    if matches:
        # 1.2.0#1-rc1 implies -> 1.3.0.a1.dev1
        release = matches.group('release')
        output = increment_release(release)

        remains = matches.group('remains')
        alpha, _, tail = remains.partition('-')
        if tail.startswith('rc'):
            tail = 'dev%s' % tail[2:]
        if alpha:
            output += '.a%s' % alpha
        if tail:
            output += '.%s' % tail
        version = output
    version = pv(version)
    if isinstance(version, SetuptoolsVersion):
        return version
    raise ValueError('Bad version %r' % version)

def increment_release(version):
    if isinstance(version, SetuptoolsVersion):
        release = version._version.release
    else:
        release = [int(elt) for elt in version.split('.')]
    major = release[0]
    minor = (release[1] if len(release) > 1 else 0) + 1
    return '%s.%s.0' % (major, minor)


def version_rpm(closest_tag, build, distribution=None):
    version = parse_version(closest_tag or '0.0.0')
    parts = []

    # Release segment
    parts.append(".".join(str(x) for x in version._version.release))

    # build parts
    if version._version.pre is not None:
        parts.append("-0.{0}.".format(build))
    else:
        parts.append("-{0}".format(build))

    # Pre-release
    if version._version.pre is not None:
        parts.append("".join(str(x) for x in version._version.pre))

    # Post-release
    if version._version.post is not None:
        parts.append(".post{0}".format(version._version.post[1]))

    # Development release
    if version._version.dev is not None:
        parts.append(".dev{0}".format(version._version.dev[1]))

    if distribution:
        parts.append(".{0}".format(distribution))

    return "".join(parts)


def version_maven(closest_tag, branch, distance):
    if branch != 'master':
        return '0-%s-SNAPSHOT' % branch.replace('-', '').upper()

    version = parse_version(closest_tag or '0.0.0')
    parts = []

    # Release segment
    if distance:
        parts.append(increment_release(version))
    else:
        parts.append(".".join(str(x) for x in version._version.release))

    # Pre-release
    if version._version.pre is not None:
        parts.append("".join(str(x) for x in version._version.pre))

    # Post-release
    if version._version.post is not None:
        parts.append("post{0}".format(version._version.post[1]))

    # Development release
    if version._version.dev is not None:
        parts.append("dev{0}".format(version._version.dev[1]))

    if distance:
        parts.append("SNAPSHOT")
    return ('-'.join(parts)).upper()


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_a = subparsers.add_parser('rpm', help='rpm version')
    parser_a.set_defaults(format=lambda r, a: version_rpm(r.closest_tag,
                                                          a.build,
                                                          a.distribution),
                          type='rpm')
    parser_a.add_argument('--build', default='${BUILD_NUMBER}')
    parser_a.add_argument('--distribution')

    parser_b = subparsers.add_parser('maven', help='maven version')
    parser_b.set_defaults(format=lambda r, a: version_maven(r.closest_tag,
                                                            r.branch,
                                                            r.distance),
                          type='maven')

    parser_c = subparsers.add_parser('git', help='git attributes')
    parser_c.set_defaults(format=lambda r, a: json.dumps(r.__dict__,
                                                         indent=a.indent),
                          type='git')
    parser_c.add_argument('--indent', type=int, default=2)

    args = parser.parse_args(args)
    return args, parser


def main(args=None):
    args, parser = parse_args(args)
    try:
        repository = audit_git(args.directory)
        response = args.format(repository, args)
        print(response)
    except Exception as error:
        parser.error(error)


if __name__ == '__main__':
    main()
