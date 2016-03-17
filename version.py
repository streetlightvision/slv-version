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


class Version(object):

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            other = str(other)
        if isinstance(other, str):
            return str(self) == other
        raise ValueError('Not comparable')


class RPMVersion(Version):

    def __init__(self, release, build=None):
        self.release = release
        self.build = build

    def __str__(self):
        if self.build:
            return '%s-%s' % (self.release, self.build)
        return '%s' % self.release

    def __repr__(self):
        return '<RPMVersion(%r, build=%r)>' % (self.release, self.build)


class MavenVersion(Version):

    def __init__(self, release, qualifiers=None, snapshot=None):
        self.release = release
        self.qualifiers = qualifiers or []
        self.snapshot = snapshot

    def __str__(self):
        parts = []
        parts.append('%s' % self.release)
        for q in self.qualifiers:
            parts.append('%s' % q)

        if self.snapshot:
            parts.append('SNAPSHOT')
        return ('-'.join(p for p in parts)).upper()

    def __repr__(self):
        return '<MavenVersion(%r, build=%r)>' % (self.release, self.build)


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
    release, parts = '', []

    # Release segment
    release = ".".join(str(x) for x in version._version.release)

    # build parts
    if version._version.pre is not None:
        parts.append("0.{0}.".format(build))
    else:
        parts.append("{0}".format(build))

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
    return RPMVersion(release, "".join(parts))


def version_maven(closest_tag, branch, distance):
    if branch != 'master':
        return MavenVersion('0', [branch.replace('-', '')], snapshot=True)

    version = parse_version(closest_tag or '0.0.0')
    release, parts, snapshot = '', [], False

    # Release segment
    if distance:
        release = increment_release(version)
    else:
        release = ".".join(str(x) for x in version._version.release)

    # Pre-release
    if version._version.pre is not None:
        parts.append("".join(str(x) for x in version._version.pre))

    # Post-release
    if version._version.post is not None:
        parts.append("post{0}".format(version._version.post[1]))

    # Development release
    if version._version.dev is not None:
        parts.append("dev{0}".format(version._version.dev[1]))

    snapshot = True if distance else False
    return MavenVersion(release, parts, snapshot=snapshot)


def prepare_arg(value):
    return '' if value is None else str(value)


def format_default(version, arguments):
    return str(version)


def format_rpm_args(version, arguments):
    response = [
        '%s=%s' % (arguments.arg_release.upper(), prepare_arg(version.release)),
        '%s=%s' % (arguments.arg_build.upper(), prepare_arg(version.build))
    ]
    return '\n'.join(response)


def format_git_args(version, arguments):
    response = []
    for key, value in version.__dict__.items():
        response.append('GIT_%s=%s' % (key.upper(), prepare_arg(value)))
    return '\n'.join(sorted(response))


def format_git_json(repository, arguments):
    return json.dumps(repository.__dict__, indent=arguments.indent)


def convert_rpm(repository, arguments):
    return version_rpm(repository.closest_tag,
                       arguments.build,
                       arguments.distribution)


def convert_maven(repository, arguments):
    return version_maven(repository.closest_tag,
                         repository.branch,
                         repository.distance)


def convert_repo(repository, arguments):
    return repository


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.set_defaults(format=format_default)
    parser.add_argument('--directory')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_a = subparsers.add_parser('rpm', help='rpm version')
    parser_a.set_defaults(parser=convert_rpm, type='rpm')
    parser_a.add_argument('--build', default='${BUILD_NUMBER}',
                          help='set build placeholder. default %(default)s')
    parser_a.add_argument('--distribution',
                          help='set distribution')
    parser_a.add_argument('--render-args', dest='format',
                          action='store_const', const=format_rpm_args,
                          default=format_default)
    parser_a.add_argument('--arg-release', default='RPM_RELEASE')
    parser_a.add_argument('--arg-build', default='RPM_BUILD')

    parser_b = subparsers.add_parser('maven', help='maven version')
    parser_b.set_defaults(parser=convert_maven, type='maven')

    parser_c = subparsers.add_parser('git', help='git attributes')
    parser_c.set_defaults(parser=convert_repo, type='git')
    parser_c.add_argument('--json-indent', dest='indent', type=int, default=2)
    parser_c.add_argument('--render-args', dest='format',
                          action='store_const', const=format_git_args,
                          default=format_git_json)

    args = parser.parse_args(args)
    return args, parser


def main(args=None):
    args, parser = parse_args(args)
    try:
        repository = audit_git(args.directory)
        response = args.parser(repository, args)
        response = args.format(response, args)
        print('%s' % response)
    except Exception as error:
        parser.error(error)


if __name__ == '__main__':
    main()
