"""ガードレール改ざん検知。PRの差分を解析し、テスト/CI/閾値の弱体化を検出する。

  error   : CIを失敗させる（テスト削除・skip化・カバレッジ閾値の緩和・検査の無効化）
  warning : 人間の注意を促す（認証・CI・依存など保護対象ファイルの変更）

使い方: python -m scripts.guardrail_check <base-ref>   例: origin/main
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass

PROTECTED = (
    ".github/",
    "scripts/",
    "pyproject.toml",
    "requirements",
    "render.yaml",
    ".pre-commit-config.yaml",
    "tests/conftest.py",
    "tests/test_authz_matrix.py",
    "app/authz.py",
    "app/crypto.py",
    "app/auth/",
    "app/config.py",
    "app/__init__.py",
)
SKIP_RE = re.compile(r"pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|unittest\.skip")
TEST_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)")
COV_RE = re.compile(r"--cov-fail-under[=\s]+(\d+)")
SUPPRESS_RE = re.compile(r"#\s*(nosec|noqa|type:\s*ignore)")
CI_DISABLE_RE = re.compile(r"continue-on-error:\s*true|\|\|\s*true")
CI_TOOLS = ("pytest", "ruff", "bandit", "pip-audit", "gitleaks", "actionlint", "codeql")


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    message: str


@dataclass
class FileDiff:
    path: str
    deleted: bool
    added: list[str]
    removed: list[str]


def parse(diff: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[-1]
            files.append(FileDiff(path, False, [], []))
        elif not files:
            continue
        elif line.startswith("deleted file mode"):
            files[-1].deleted = True
        elif line.startswith(("+++", "---")):
            continue
        elif line.startswith("+"):
            files[-1].added.append(line[1:])
        elif line.startswith("-"):
            files[-1].removed.append(line[1:])
    return files


def _test_names(lines: list[str]) -> set[str]:
    return {m.group(1) for line in lines if (m := TEST_DEF_RE.match(line))}


def _count_tools(lines: list[str]) -> dict[str, int]:
    text = "\n".join(lines).lower()
    return {tool: text.count(tool) for tool in CI_TOOLS}


def _check_tests(f: FileDiff) -> list[Finding]:
    out: list[Finding] = []
    if f.deleted:
        out.append(Finding("error", f.path, "テストファイルが削除されました"))
        return out
    gone = _test_names(f.removed) - _test_names(f.added)
    for name in sorted(gone):
        out.append(Finding("error", f.path, f"テスト関数 {name} が削除されました"))
    for line in f.added:
        code = re.split(r"[\"']", line, maxsplit=1)[0]  # 文字列リテラル内の記述は対象外
        if SKIP_RE.search(code):
            out.append(Finding("error", f.path, f"テストのskip/xfail化: {line.strip()}"))
    return out


def _check_pyproject(f: FileDiff) -> list[Finding]:
    old = [int(m.group(1)) for x in f.removed if (m := COV_RE.search(x))]
    new = [int(m.group(1)) for x in f.added if (m := COV_RE.search(x))]
    if old and (not new or min(new) < max(old)):
        shown = new[0] if new else "なし"
        return [
            Finding("error", f.path, f"カバレッジ閾値が緩和/削除されました: {old[0]} → {shown}")
        ]
    return []


def _check_workflow(f: FileDiff) -> list[Finding]:
    out: list[Finding] = []
    for line in f.added:
        if CI_DISABLE_RE.search(line):
            out.append(Finding("error", f.path, f"CI検査の無効化: {line.strip()}"))
    before, after = _count_tools(f.removed), _count_tools(f.added)
    for tool in CI_TOOLS:
        if before[tool] > after[tool]:
            out.append(Finding("error", f.path, f"CIの検査 {tool} が削除された可能性があります"))
    return out


def analyze(diff: str) -> list[Finding]:
    findings: list[Finding] = []
    for f in parse(diff):
        if f.path.startswith("tests/"):
            findings += _check_tests(f)
        if f.path == "pyproject.toml":
            findings += _check_pyproject(f)
        if f.path.startswith(".github/workflows/"):
            findings += _check_workflow(f)
        if f.path.startswith("app/") and any(SUPPRESS_RE.search(x) for x in f.added):
            findings.append(
                Finding("warning", f.path, "警告抑制コメント(nosec/noqa/type: ignore)の追加")
            )
        if f.path.startswith(PROTECTED):
            findings.append(
                Finding("warning", f.path, "保護対象ファイルが変更されました（要・人間レビュー）")
            )
    return findings


def render_summary(findings: list[Finding]) -> str:
    if not findings:
        return "## ✅ ガードレール改ざん検知: 問題なし\n"
    lines = ["## 🛡️ ガードレール改ざん検知\n", "| 区分 | ファイル | 内容 |", "|---|---|---|"]
    for f in sorted(findings, key=lambda x: (x.level != "error", x.path)):
        mark = "🔴 ERROR" if f.level == "error" else "🟡 WARNING"
        lines.append(f"| {mark} | `{f.path}` | {f.message} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    base = argv[1] if len(argv) > 1 else "origin/main"
    sys.stdout.reconfigure(encoding="utf-8")
    diff = subprocess.run(  # noqa: S603
        ["git", "diff", "-U0", "--no-renames", f"{base}...HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    findings = analyze(diff)
    for f in findings:
        print(f"::{f.level} file={f.path}::{f.message}")
    summary = render_summary(findings)
    print(summary)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(summary)
    return 1 if any(f.level == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
