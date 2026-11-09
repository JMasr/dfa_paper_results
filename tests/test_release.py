"""Archive corruption, deterministic packaging and source boundary tests."""
import hashlib
import json
import zipfile
import pytest
from package_release import write_archive, verify_archive, selected_sources, ROOT, FILES, FOLDERS


def archive_members():
    data = b'run,metric\n1,0.5\n'
    manifest = {'sha256': {'runs.csv': hashlib.sha256(data).hexdigest()}}
    return {'runs.csv':data, 'RELEASE-MANIFEST.json':json.dumps(manifest).encode()}


def test_archive_is_deterministic_and_integrity_checked(tmp_path):
    first, second = tmp_path/'first.zip',tmp_path/'second.zip'
    members=archive_members()
    write_archive(first,members);write_archive(second,members)
    assert first.read_bytes()==second.read_bytes()
    assert verify_archive(first)==2
    members['runs.csv']=b'run,metric\n1,0.9\n'
    write_archive(second,members)
    with pytest.raises(ValueError,match='Corrupt'):verify_archive(second)


def test_unsafe_and_unlisted_archive_members_are_rejected(tmp_path):
    destination=tmp_path/'bad.zip';members=archive_members();members['../outside.csv']=b'x'
    write_archive(destination,members)
    with pytest.raises(ValueError,match='Unsafe'):verify_archive(destination)
    members=archive_members();members['extra.csv']=b'x';write_archive(destination,members)
    with pytest.raises(ValueError,match='inventory'):verify_archive(destination)


def test_release_boundary_rejects_symlinks_and_unexpected_files(tmp_path):
    for name in FILES:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test')
    for folder in FOLDERS:(tmp_path/folder).mkdir(parents=True,exist_ok=True)
    (tmp_path/'tools/certificate.key').write_text('placeholder')
    with pytest.raises(ValueError,match='Unexpected'):selected_sources(tmp_path)
    (tmp_path/'tools/certificate.key').unlink()
    (tmp_path/'tools/link.py').symlink_to(tmp_path/'README.md')
    with pytest.raises(ValueError,match='Unsafe'):selected_sources(tmp_path)


def test_local_release_excludes_environment_and_repository_internals():
    files=selected_sources()
    assert files
    for path in files:
        assert '.env' not in path.name
        assert '.git' not in path.relative_to(ROOT).parts
        assert '.venv' not in path.relative_to(ROOT).parts
