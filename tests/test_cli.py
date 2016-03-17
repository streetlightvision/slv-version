import pytest
from version import parse_args


def test_maven():
    args, parser = parse_args(['maven'])
    assert args.type == 'maven'


def test_args2():
    args, parser = parse_args(['rpm'])
    assert args.type == 'rpm'


def test_args3():
    args, parser = parse_args(['git'])
    assert args.type == 'git'
