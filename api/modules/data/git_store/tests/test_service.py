"""
modules/data/git_store/tests/test_service.py
Unit tests for all eight public git_store operations.
"""
from pathlib import Path

import pytest

import modules.data.git_store as git_store


PROJECT = "test-proj-xyz"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repos_dir(tmp_path, monkeypatch):
    """Redirect git_store to a temp directory; isolated per test."""
    monkeypatch.setenv("GIT_REPOS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def initialized_repo(repos_dir):
    """An initialized repo with no extra files; returns project_id."""
    git_store.init_repo(PROJECT)
    return PROJECT


@pytest.fixture
def repo_with_file(initialized_repo):
    """Repo pre-loaded with 'spec.md'; returns (project_id, write_sha)."""
    sha = git_store.write_file(
        initialized_repo, "spec.md", "# Spec v1", "feat: add spec"
    )
    return initialized_repo, sha


# ---------------------------------------------------------------------------
# init_repo
# ---------------------------------------------------------------------------

def test_init_repo_creates_git_directory(repos_dir):
    git_store.init_repo(PROJECT)
    assert (repos_dir / PROJECT / ".git").is_dir(), \
        ".git directory must exist after init"


def test_init_repo_returns_sha(repos_dir):
    sha = git_store.init_repo(PROJECT)
    assert isinstance(sha, str) and len(sha) == 40, \
        f"Expected 40-char hex SHA, got {sha!r}"


def test_init_repo_head_is_valid(repos_dir):
    """HEAD must be resolvable immediately after init (no 'unborn HEAD' downstream)."""
    import pygit2
    git_store.init_repo(PROJECT)
    repo = pygit2.Repository(str(repos_dir / PROJECT))
    commit = repo.revparse_single("HEAD")
    assert str(commit.id), "HEAD must resolve to a valid commit OID"


def test_init_repo_creates_parent_dirs(tmp_path, monkeypatch):
    """init_repo must create the per-project directory if it does not exist."""
    monkeypatch.setenv("GIT_REPOS_DIR", str(tmp_path / "nested" / "base"))
    git_store.init_repo("brand-new")
    assert (tmp_path / "nested" / "base" / "brand-new" / ".git").is_dir()


def test_repos_base_falls_back_to_config_without_env(monkeypatch):
    """When neither env var is set, _repos_base falls back to config.PROJECTS_DIR."""
    monkeypatch.delenv("GIT_REPOS_DIR", raising=False)
    monkeypatch.delenv("PROJECTS_DIR", raising=False)
    from config import PROJECTS_DIR
    assert git_store.service._repos_base() == Path(PROJECTS_DIR)


def test_init_repo_falls_back_to_projects_dir(tmp_path, monkeypatch):
    """When GIT_REPOS_DIR is unset, PROJECTS_DIR is used."""
    monkeypatch.delenv("GIT_REPOS_DIR", raising=False)
    monkeypatch.setenv("PROJECTS_DIR", str(tmp_path))
    git_store.init_repo("fallback-proj")
    assert (tmp_path / "fallback-proj" / ".git").is_dir()


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_persists_content(initialized_repo):
    git_store.write_file(initialized_repo, "notes.md", "hello world", "add notes")
    content = git_store.read_file(initialized_repo, "notes.md")
    assert content == "hello world", f"Content mismatch: {content!r}"


def test_write_file_returns_40_char_sha(initialized_repo):
    sha = git_store.write_file(initialized_repo, "a.md", "A", "add a")
    assert len(sha) == 40, f"Expected 40-char SHA, got {sha!r}"


def test_write_file_commit_message_preserved(initialized_repo, repos_dir):
    import pygit2
    git_store.write_file(initialized_repo, "x.md", "X", "my: custom message")
    repo = pygit2.Repository(str(repos_dir / initialized_repo))
    assert repo.head.peel(pygit2.Commit).message.strip() == "my: custom message"


def test_write_file_twice_produces_two_additional_commits(initialized_repo, repos_dir):
    import pygit2
    git_store.write_file(initialized_repo, "f.md", "v1", "v1")
    git_store.write_file(initialized_repo, "f.md", "v2", "v2")
    repo = pygit2.Repository(str(repos_dir / initialized_repo))
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
    shas = [str(c.id) for c in walker]
    # init commit + 2 write commits = 3 total
    assert len(shas) == 3, f"Expected 3 commits, got {len(shas)}"


def test_write_file_overwrites_previous_content(initialized_repo):
    git_store.write_file(initialized_repo, "f.md", "first", "v1")
    git_store.write_file(initialized_repo, "f.md", "second", "v2")
    assert git_store.read_file(initialized_repo, "f.md") == "second"


def test_write_file_handles_unicode(initialized_repo):
    payload = "héllo — wörld\n日本語\n"
    git_store.write_file(initialized_repo, "u.md", payload, "unicode")
    assert git_store.read_file(initialized_repo, "u.md") == payload


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def test_read_file_at_head(repo_with_file):
    project_id, _ = repo_with_file
    content = git_store.read_file(project_id, "spec.md")
    assert content == "# Spec v1"


def test_read_file_at_specific_sha(initialized_repo):
    sha1 = git_store.write_file(initialized_repo, "doc.md", "version one", "v1")
    git_store.write_file(initialized_repo, "doc.md", "version two", "v2")
    content_at_sha1 = git_store.read_file(initialized_repo, "doc.md", ref=sha1)
    assert content_at_sha1 == "version one", \
        f"Expected v1 content at sha1, got {content_at_sha1!r}"


def test_read_file_missing_raises_key_error(initialized_repo):
    with pytest.raises(KeyError):
        git_store.read_file(initialized_repo, "does-not-exist.md")


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

def test_list_files_empty_after_init(initialized_repo):
    assert git_store.list_files(initialized_repo) == []


def test_list_files_returns_written_filenames(initialized_repo):
    git_store.write_file(initialized_repo, "alpha.md", "a", "add alpha")
    git_store.write_file(initialized_repo, "beta.md", "b", "add beta")
    files = git_store.list_files(initialized_repo)
    assert files == ["alpha.md", "beta.md"], f"Unexpected listing: {files}"


def test_list_files_excludes_deleted_file(initialized_repo):
    git_store.write_file(initialized_repo, "keep.md", "keep", "add keep")
    git_store.write_file(initialized_repo, "drop.md", "drop", "add drop")
    git_store.delete_file(initialized_repo, "drop.md", "remove drop")
    files = git_store.list_files(initialized_repo)
    assert "drop.md" not in files, f"Deleted file still listed: {files}"
    assert "keep.md" in files


def test_list_files_at_specific_ref(initialized_repo):
    """list_files at an older ref shows the tree as it was."""
    sha_a = git_store.write_file(initialized_repo, "first.md", "1", "v1")
    git_store.write_file(initialized_repo, "second.md", "2", "v2")
    files_at_a = git_store.list_files(initialized_repo, ref=sha_a)
    assert files_at_a == ["first.md"]


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

def test_get_history_includes_commit_touching_file(initialized_repo):
    git_store.write_file(initialized_repo, "story.md", "draft", "add story")
    history = git_store.get_history(initialized_repo, "story.md")
    assert len(history) == 1, f"Expected 1 history entry, got {len(history)}"
    assert "add story" in history[0]["message"]
    assert len(history[0]["sha"]) == 40
    assert isinstance(history[0]["timestamp"], int)


def test_get_history_excludes_unrelated_commits(initialized_repo):
    git_store.write_file(initialized_repo, "story.md", "v1", "add story")
    # The next commit does not touch story.md
    git_store.write_file(initialized_repo, "other.md", "x", "add other")
    history = git_store.get_history(initialized_repo, "story.md")
    assert len(history) == 1, \
        f"History for story.md should not include other.md commit; got {history}"


def test_get_history_respects_limit(initialized_repo):
    for i in range(5):
        git_store.write_file(initialized_repo, "log.md", f"v{i}", f"update {i}")
    history = git_store.get_history(initialized_repo, "log.md", limit=3)
    assert len(history) == 3, \
        f"Expected 3 entries with limit=3, got {len(history)}"


def test_get_history_returns_empty_for_missing_file(initialized_repo):
    git_store.write_file(initialized_repo, "real.md", "x", "add real")
    history = git_store.get_history(initialized_repo, "ghost.md")
    assert history == []


def test_get_history_includes_delete_commit(initialized_repo):
    """A delete commit also touches the file and must appear in history."""
    git_store.write_file(initialized_repo, "ephemeral.md", "x", "add")
    git_store.delete_file(initialized_repo, "ephemeral.md", "remove")
    history = git_store.get_history(initialized_repo, "ephemeral.md")
    assert len(history) == 2, \
        f"Expected add + delete in history, got {history}"


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------

def test_get_diff_returns_unified_patch(initialized_repo):
    sha_a = git_store.write_file(initialized_repo, "readme.md", "line one\n", "v1")
    sha_b = git_store.write_file(
        initialized_repo, "readme.md", "line one\nline two\n", "v2"
    )
    diff = git_store.get_diff(initialized_repo, "readme.md", sha_a, sha_b)
    assert "+line two" in diff, f"Expected addition in diff, got:\n{diff}"


def test_get_diff_empty_for_untouched_file(initialized_repo):
    sha_a = git_store.write_file(initialized_repo, "a.md", "aaa", "add a")
    sha_b = git_store.write_file(initialized_repo, "b.md", "bbb", "add b")
    # a.md was not changed between sha_a and sha_b
    diff = git_store.get_diff(initialized_repo, "a.md", sha_a, sha_b)
    assert diff == "", f"Expected empty diff for untouched file, got: {diff!r}"


# ---------------------------------------------------------------------------
# revert_file
# ---------------------------------------------------------------------------

def test_revert_file_restores_content_via_forward_commit(initialized_repo):
    sha_v1 = git_store.write_file(initialized_repo, "doc.md", "original\n", "v1")
    git_store.write_file(initialized_repo, "doc.md", "overwritten\n", "v2")
    git_store.revert_file(initialized_repo, "doc.md", sha_v1)
    current = git_store.read_file(initialized_repo, "doc.md")
    assert current == "original\n", \
        f"Revert did not restore content: {current!r}"


def test_revert_file_does_not_rewrite_history(initialized_repo, repos_dir):
    import pygit2
    sha_v1 = git_store.write_file(initialized_repo, "doc.md", "v1\n", "v1")
    git_store.write_file(initialized_repo, "doc.md", "v2\n", "v2")
    git_store.revert_file(initialized_repo, "doc.md", sha_v1)
    repo = pygit2.Repository(str(repos_dir / initialized_repo))
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
    count = sum(1 for _ in walker)
    # init + v1 + v2 + revert = 4 commits; history must not be rewritten shorter
    assert count == 4, f"Expected 4 commits after revert, got {count}"


def test_revert_file_returns_new_sha(initialized_repo):
    sha_v1 = git_store.write_file(initialized_repo, "d.md", "first\n", "v1")
    git_store.write_file(initialized_repo, "d.md", "second\n", "v2")
    revert_sha = git_store.revert_file(initialized_repo, "d.md", sha_v1)
    assert len(revert_sha) == 40 and revert_sha != sha_v1, \
        f"Revert should produce a new 40-char SHA distinct from the source, got {revert_sha!r}"


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------

def test_delete_file_removes_file_from_listing(initialized_repo):
    git_store.write_file(initialized_repo, "temp.md", "temp content", "add temp")
    git_store.delete_file(initialized_repo, "temp.md", "remove temp")
    files = git_store.list_files(initialized_repo)
    assert "temp.md" not in files, f"File still present after delete: {files}"


def test_delete_file_returns_sha(initialized_repo):
    git_store.write_file(initialized_repo, "d.md", "d", "add d")
    sha = git_store.delete_file(initialized_repo, "d.md", "del d")
    assert len(sha) == 40, f"Expected 40-char SHA from delete, got {sha!r}"


def test_delete_file_history_visible_at_old_ref(initialized_repo):
    """After delete, the file is gone at HEAD but readable at an earlier SHA."""
    sha_add = git_store.write_file(initialized_repo, "gone.md", "byebye", "add")
    git_store.delete_file(initialized_repo, "gone.md", "remove")
    with pytest.raises(KeyError):
        git_store.read_file(initialized_repo, "gone.md")
    assert git_store.read_file(initialized_repo, "gone.md", ref=sha_add) == "byebye"
