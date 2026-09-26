"""A private CAS is byte-addressed, physical, and fail-closed."""

from hashlib import sha256
import os

import pytest

from v5_2.data.private_cas import put_exact, read_exact, resolve_cas_root


def test_create_or_identical_uses_exact_byte_sha_and_fanout(tmp_path):
    payload = b"approved immutable bytes\x00\xff"
    expected = sha256(payload).hexdigest()
    assert put_exact(tmp_path, payload) == expected
    object_path = tmp_path / "sha256" / expected[:2] / expected
    assert object_path.read_bytes() == payload
    assert put_exact(tmp_path, payload) == expected
    assert read_exact(tmp_path, expected, len(payload)) == payload


def test_missing_wrong_size_or_same_size_tamper_fails_closed(tmp_path):
    payload = b"abc"
    digest = sha256(payload).hexdigest()
    with pytest.raises(ValueError, match="PRIVATE_CORPUS_UNAVAILABLE"):
        read_exact(tmp_path, digest, 3)
    put_exact(tmp_path, payload)
    with pytest.raises(ValueError, match="size"):
        read_exact(tmp_path, digest, 2)
    (tmp_path / "sha256" / digest[:2] / digest).write_bytes(b"xyz")
    with pytest.raises(ValueError, match="hash"):
        read_exact(tmp_path, digest, 3)
    with pytest.raises(ValueError, match="hash"):
        put_exact(tmp_path, payload)


def test_linked_object_is_rejected_even_when_bytes_match(tmp_path):
    payload = b"physical only"
    digest = put_exact(tmp_path, payload)
    object_path = tmp_path / "sha256" / digest[:2] / digest
    os.link(object_path, tmp_path / "second-link")
    with pytest.raises(ValueError, match="link"):
        read_exact(tmp_path, digest, len(payload))


def test_formal_root_requires_explicit_environment(tmp_path):
    environment = {"LOCALAPPDATA": str(tmp_path)}
    assert resolve_cas_root(environment) == tmp_path / "V5_2" / "private-cas"
    with pytest.raises(ValueError, match="PRIVATE_CORPUS_UNAVAILABLE"):
        resolve_cas_root(environment, require_explicit=True)
    environment["V5_2_PRIVATE_CAS_ROOT"] = str(tmp_path / "mounted")
    assert resolve_cas_root(environment, require_explicit=True) == tmp_path / "mounted"
