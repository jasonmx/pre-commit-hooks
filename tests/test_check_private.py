"""check-private: terms from the main checkout's gitignored files, matched in staged files and messages."""

import subprocess
from pathlib import Path

from pre_commit_hooks import check_private


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text)
    return path


def git_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_no_terms_files_means_no_terms(tmp_path):
    assert check_private.private_terms([tmp_path / ".private-terms", tmp_path / ".private-terms.rig"]) == {}


def test_terms_come_from_each_file_with_labels_and_comments(tmp_path):
    own = write(tmp_path, ".private-terms", "# names\nAcme Street\n\n")
    rig = write(
        tmp_path, ".private-terms.rig", "# Written by the rig\nlight.Kitchen\tlight.Kitchen\nabc.def\tHA_TOKEN\n"
    )
    assert check_private.private_terms([own, rig, tmp_path / "missing"]) == {
        "acme street": "Acme Street",
        "light.kitchen": "light.Kitchen",
        "abc.def": "HA_TOKEN",
    }


def test_main_checkout_of_a_linked_worktree_is_the_main_one(tmp_path):
    main = git_repo(tmp_path / "main")
    identity = ["-c", "user.name=test", "-c", "user.email=test@example.com"]
    subprocess.run(["git", "-C", str(main), *identity, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", str(tmp_path / "linked")], check=True)
    assert check_private.main_checkout(tmp_path / "linked").resolve() == main.resolve()
    assert check_private.main_checkout(main).resolve() == main.resolve()
    outside = tmp_path / "outside"
    outside.mkdir()
    assert check_private.main_checkout(outside) == outside


def test_find_reports_matches_case_insensitively_by_label(tmp_path):
    staged = write(tmp_path, "doc.md", "fine\nToken ABC.DEF here\n")
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe")
    hits = check_private.find([staged, binary, tmp_path / "deleted"], {"abc.def": "HA_TOKEN"})
    assert hits == [f"{staged}:2: HA_TOKEN"]


def test_main_passes_without_terms_files(tmp_path, monkeypatch):
    monkeypatch.chdir(git_repo(tmp_path / "repo"))
    assert check_private.main([str(write(tmp_path, "doc.md", "acme street"))]) == 0


def test_main_reads_the_default_files_and_reports_the_label_not_the_secret(tmp_path, monkeypatch, capsys):
    repo = git_repo(tmp_path / "repo")
    write(repo, ".private-terms.rig", "s3cret\tHA_TOKEN\n")
    monkeypatch.chdir(repo)
    assert check_private.main([str(write(tmp_path, "msg", "token S3CRET"))]) == 1
    out = capsys.readouterr().out
    assert "HA_TOKEN" in out
    assert "s3cret" not in out.lower()


def test_main_reads_only_the_named_terms_files(tmp_path, monkeypatch):
    repo = git_repo(tmp_path / "repo")
    write(repo, ".private-terms", "acme street\n")
    write(repo, "other-terms", "elm road\n")
    monkeypatch.chdir(repo)
    msg = write(tmp_path, "msg", "acme street")
    assert check_private.main(["--terms-file", "other-terms", str(msg)]) == 0
    assert check_private.main(["--terms-file", "other-terms", str(write(tmp_path, "m2", "Elm Road"))]) == 1


def test_main_refuses_when_a_terms_file_cant_be_read(tmp_path, monkeypatch, capsys):
    repo = git_repo(tmp_path / "repo")
    (repo / ".private-terms").write_bytes(b"\xff\xfe")
    monkeypatch.chdir(repo)
    assert check_private.main([str(write(tmp_path, "msg", "anything"))]) == 1
    assert "the commit is refused" in capsys.readouterr().out
