"""ガードレール改ざん検知（scripts/guardrail_check.py）のテスト。

PRの差分に「テストの削除・スキップ化・カバレッジ閾値の緩和・CI検査の無効化」があれば
CIを失敗させ、認証/CI等の保護対象ファイルの変更は警告として明示する。
"""

from scripts.guardrail_check import analyze


def make_diff(path: str, removed: list[str] = (), added: list[str] = (), deleted: bool = False):
    lines = [f"diff --git a/{path} b/{path}"]
    if deleted:
        lines.append("deleted file mode 100644")
    lines += [f"--- a/{path}", f"+++ {'/dev/null' if deleted else 'b/' + path}", "@@ -1 +1 @@"]
    lines += [f"-{x}" for x in removed] + [f"+{x}" for x in added]
    return "\n".join(lines) + "\n"


def errors(diff):
    return [f for f in analyze(diff) if f.level == "error"]


def warnings(diff):
    return [f for f in analyze(diff) if f.level == "warning"]


def test_clean_app_change_has_no_findings():
    assert analyze(make_diff("app/inventory/routes.py", added=["x = 1"])) == []


def test_deleted_test_file_is_error():
    found = errors(make_diff("tests/test_auth.py", deleted=True))
    assert len(found) == 1 and "削除" in found[0].message


def test_removed_test_function_is_error():
    diff = make_diff("tests/test_auth.py", removed=["def test_login_success(client):"])
    assert errors(diff)


def test_renamed_test_function_is_not_error():
    diff = make_diff(
        "tests/test_auth.py",
        removed=["def test_old_name(client):"],
        added=["def test_old_name(client):", "    assert True"],
    )
    assert errors(diff) == []


def test_adding_new_test_is_not_error():
    assert errors(make_diff("tests/test_new.py", added=["def test_new():", "    assert 1"])) == []


def test_skip_markers_are_errors():
    for line in (
        "@pytest.mark.skip",
        '@pytest.mark.skipif(True, reason="x")',
        "@pytest.mark.xfail",
        'pytest.skip("later")',
        "@unittest.skip('x')",
    ):
        assert errors(make_diff("tests/test_auth.py", added=[line])), line


def test_skip_marker_inside_string_literal_is_not_error():
    assert errors(make_diff("tests/test_x.py", added=['    "@pytest.mark.skip",'])) == []


def test_skip_via_pytestmark_is_error():
    assert errors(make_diff("tests/test_x.py", added=["pytestmark = pytest.mark.skip"]))


def test_coverage_threshold_lowered_is_error():
    diff = make_diff(
        "pyproject.toml",
        removed=['addopts = "--cov=app --cov-fail-under=80"'],
        added=['addopts = "--cov=app --cov-fail-under=50"'],
    )
    assert any("カバレッジ" in f.message for f in errors(diff))


def test_coverage_threshold_removed_is_error():
    diff = make_diff(
        "pyproject.toml",
        removed=['addopts = "--cov=app --cov-fail-under=80"'],
        added=['addopts = "--cov=app"'],
    )
    assert any("カバレッジ" in f.message for f in errors(diff))


def test_coverage_threshold_raised_is_not_error_but_warns():
    diff = make_diff(
        "pyproject.toml",
        removed=['addopts = "--cov-fail-under=80"'],
        added=['addopts = "--cov-fail-under=90"'],
    )
    assert errors(diff) == [] and warnings(diff)


def test_ci_check_disabled_is_error():
    path = ".github/workflows/ci.yml"
    assert errors(make_diff(path, added=["    continue-on-error: true"]))
    assert errors(make_diff(path, added=["      - run: pytest || true"]))


def test_ci_tool_step_removed_is_error():
    diff = make_diff(".github/workflows/ci.yml", removed=["      - run: bandit -r app"])
    assert any("bandit" in f.message for f in errors(diff))


def test_ci_tool_step_moved_is_not_error():
    diff = make_diff(
        ".github/workflows/ci.yml",
        removed=["      - run: bandit -r app"],
        added=["      - run: bandit -c pyproject.toml -r app -ll"],
    )
    assert errors(diff) == []


def test_protected_paths_warn():
    for path in (
        ".github/CODEOWNERS",
        ".github/workflows/ci.yml",
        "pyproject.toml",
        "tests/test_authz_matrix.py",
        "requirements.txt",
        "render.yaml",
        ".pre-commit-config.yaml",
        "scripts/guardrail_check.py",
        "app/authz.py",
        "app/crypto.py",
    ):
        assert warnings(make_diff(path, added=["# x"])), path


def test_suppression_comments_in_app_warn():
    assert warnings(make_diff("app/admin/routes.py", added=["x = eval(s)  # nosec"]))
    assert warnings(make_diff("app/admin/routes.py", added=["import os  # noqa: S101"]))


def test_multiple_files_are_all_checked():
    diff = make_diff("tests/test_a.py", deleted=True) + make_diff("pyproject.toml", added=["x = 1"])
    assert len(errors(diff)) == 1 and warnings(diff)
