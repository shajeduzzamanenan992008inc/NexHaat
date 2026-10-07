from io import BytesIO
import stat
import zipfile

import pytest

from app.ai.builder.archives import ProjectArchiveError, inspect_project_archive


def _zip(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return output.getvalue()


def test_project_archive_returns_source_in_memory_and_skips_sensitive_or_generated_files():
    data = _zip([
        ("sample/app.py", "print('hello')"),
        ("sample/README.md", "# Project"),
        ("sample/.env", "SECRET=value"),
        ("sample/node_modules/pkg/index.js", "ignored()"),
        ("sample/image.png", b"\x89PNG\r\n\x1a\n"),
    ])

    assert inspect_project_archive(data) == [
        ("sample/app.py", "print('hello')"),
        ("sample/README.md", "# Project"),
    ]


@pytest.mark.parametrize("name", ["../escape.py", "/absolute.py", "C:/drive.py", "folder\\..\\escape.py"])
def test_project_archive_rejects_traversal_and_platform_paths(name):
    data = _zip([(name, "bad")])
    if "\\" in name:
        data = data.replace(name.replace("\\", "/").encode(), name.encode())
    with pytest.raises(ProjectArchiveError, match="unsafe file path"):
        inspect_project_archive(data)


def test_project_archive_rejects_symbolic_links():
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        item = zipfile.ZipInfo("project/link.py")
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(item, "../../outside.py")

    with pytest.raises(ProjectArchiveError, match="symbolic links"):
        inspect_project_archive(output.getvalue())


def test_project_archive_rejects_expansion_abuse_and_oversized_files():
    bomb = _zip([("project/source.py", "A" * 100_000)])
    with pytest.raises(ProjectArchiveError, match="compression ratio"):
        inspect_project_archive(bomb)

    too_large = _zip([("project/source.py", "x" * (4 * 1024 * 1024 + 1))])
    with pytest.raises(ProjectArchiveError, match="per-file"):
        inspect_project_archive(too_large)


def test_project_archive_rejects_invalid_and_oversized_uploads():
    with pytest.raises(ProjectArchiveError, match="valid ZIP"):
        inspect_project_archive(b"not zip")
    with pytest.raises(ProjectArchiveError, match="upload limit"):
        inspect_project_archive(b"x" * (20 * 1024 * 1024 + 1))
