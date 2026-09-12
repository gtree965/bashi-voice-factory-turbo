"""Check staged changes using Git ignore rules and a local, untracked term list."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

# This script's own directory must be added explicitly: the interpreter this
# repository ships is an embeddable build whose ._pth file replaces sys.path, so
# a sibling module is not importable without it. Harmless under any other
# interpreter, and the guard module itself still spells no pattern literally.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_patterns import (  # noqa: E402
    AI_TOOL_NAMES, COMMIT_GUARD_EXTRA_AI_NAMES, EMPTY_TREE, EXPECTED_IDENTITY,
    RETIRED_HOSTS, SESSION_UUID, SHARED_MACHINE_RESIDUE, WINDOWS_USER_PATH,
)

TERMS_ENV = "BASHI_SENSITIVE_TERMS_FILE"
SCISSORS = "# ------------------------ >8 ------------------------"
MESSAGE_TOOL_NAMES = "|".join((AI_TOOL_NAMES, COMMIT_GUARD_EXTRA_AI_NAMES))
MESSAGE_TOOL_PATTERN = re.compile(MESSAGE_TOOL_NAMES, re.IGNORECASE)
TRACE_PATTERN = "|".join((
    AI_TOOL_NAMES, COMMIT_GUARD_EXTRA_AI_NAMES, SESSION_UUID, SHARED_MACHINE_RESIDUE,
    WINDOWS_USER_PATH, RETIRED_HOSTS,
))
TRACE_TEXT = re.compile(TRACE_PATTERN, re.IGNORECASE)
TRACE_BYTES = re.compile(TRACE_PATTERN.encode("ascii"), re.IGNORECASE)
TRACE_ALLOWLIST = frozenset((
    ".gitignore",
    "build_mac_linux_bundle.py",
    "test_tts_readback.py",
    "test_zh_tts_patch.py",
    "test_pre_commit_guard.py",
    "scripts/git-hooks/guard_patterns.py",
))

# An annotated tag carries its tagger on a header line of the tag object. The
# expected identity and the empty tree used for root commits come from the
# registry above.
TAGGER_LINE = re.compile(r"^(.*) <([^<>]*)> \d+ [+-]\d{4}$")

_CONTENT_ISSUES = {
    "ignored": "Ignored staged path: {path}. Unstage it; keep local-only files private.",
    "sensitive_path": "Local sensitive term in a staged path (path withheld).",
    "sensitive_binary": "Local sensitive term in staged binary content: {path}.",
    "residue_binary": "Disallowed residue in staged binary content: {path}.",
    "sensitive_lines": "Local sensitive term in added lines: {path}.",
    "residue_lines": "Disallowed residue in added lines: {path}.",
    "commit_ignored": "Ignored path in commit {commit}: {path}.",
    "commit_sensitive_path": "Local sensitive term in a path in commit {commit} (path withheld).",
    "commit_sensitive_binary": (
        "Local sensitive term in binary content added by commit {commit}: {path}."),
    "commit_residue_binary": (
        "Disallowed residue in binary content added by commit {commit}: {path}."),
    "commit_sensitive_lines": (
        "Local sensitive term in lines added by commit {commit}: {path}."),
    "commit_residue_lines": "Disallowed residue in lines added by commit {commit}: {path}.",
}


class GuardError(Exception):
    """An unavailable input must block rather than silently weaken the guard."""


def git(root: Path, *args: str, data: bytes | None = None,
        allowed: tuple[int, ...] = (0,)) -> bytes:
    # check-ignore consumes literal stdin paths itself and rejects pathspec magic.
    options = [] if args[0] == "check-ignore" else ["--literal-pathspecs"]
    result = subprocess.run(
        ["git", *options, "-C", str(root), *args],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "LC_ALL": "C"},
    )
    if result.returncode not in allowed:
        raise GuardError(f"Git {args[0]} failed (exit {result.returncode}); review the index.")
    return result.stdout


def decoded(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def load_terms(root: Path, path: Path | None = None) -> tuple[str, ...]:
    if path is None:
        override = os.environ.get(TERMS_ENV)
        git_dir = Path(os.fsdecode(git(root, "rev-parse", "--git-dir")).strip())
        if not git_dir.is_absolute():
            git_dir = root / git_dir
        path = Path(override) if override else git_dir / "info/bashi-sensitive-terms.txt"
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        lines = []
    terms = tuple(dict.fromkeys(
        line.strip().casefold() for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ))
    if not terms:
        raise GuardError(
            "Local term list is missing, unreadable or empty. Restore the UTF-8 "
            "backup to $(git rev-parse --git-dir)/info/bashi-sensitive-terms.txt "
            "(one term per line), then retry. Do not stage the list or bypass the hook."
        )
    return terms


def contains_term(text: str, terms: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(term in folded for term in terms)


def changed_paths(root: Path, diff_range: tuple[str, ...]) -> list[tuple[str, str | None]]:
    """Paths a comparison range touches, rename and copy sources kept."""
    fields = git(root, "diff", *diff_range, "--name-status", "-z",
                 "--diff-filter=ACMR", "--find-renames", "--find-copies").split(b"\0")
    changes = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        first = os.fsdecode(fields[i + 1])
        i += 2
        if status.startswith((b"R", b"C")):
            changes.append((os.fsdecode(fields[i]), first))
            i += 1
        else:
            changes.append((first, None))
    return changes


def staged_changes(root: Path) -> list[tuple[str, str | None]]:
    return changed_paths(root, ("--cached",))


def ignored_paths(root: Path, paths: list[str]) -> list[str]:
    if not paths:
        return []
    output = git(root, "check-ignore", "--no-index", "--stdin", "-z",
                 data=b"\0".join(os.fsencode(p) for p in paths) + b"\0",
                 allowed=(0, 1))
    return [os.fsdecode(p) for p in output.split(b"\0") if p]


def added_lines(patch: bytes) -> list[str]:
    """Read hunk additions, never headers/context or removed lines."""
    lines = []
    in_hunk = False
    for line in patch.splitlines():
        if line.startswith(b"diff --git "):
            in_hunk = False
        elif line.startswith(b"@@ "):
            in_hunk = True
        elif in_hunk and line.startswith(b"+"):
            lines.append(decoded(line[1:]))
    return lines


def scan_changes(root: Path, changes: list[tuple[str, str | None]], terms: tuple[str, ...],
                 diff_range: tuple[str, ...], blob_prefix: str,
                 commit: str | None = None) -> list[str]:
    """The three content gates, over whichever comparison range is given.

    ``diff_range`` says what the new content is compared against and
    ``blob_prefix`` locates that content, so one implementation serves both the
    index (``("--cached",)`` with ``":"``) and a single commit (``(parent,
    commit)`` with ``"<commit>:"``). ``commit`` only selects the wording; the
    checks themselves are identical.
    """
    prefix = "" if commit is None else "commit_"
    issues = []

    def note(kind: str, path: str = "") -> None:
        issues.append(_CONTENT_ISSUES[prefix + kind].format(path=path, commit=commit or ""))

    def display(path: str) -> str:
        return "<withheld path>" if contains_term(path, terms) else ascii(path)

    for path in ignored_paths(root, [path for path, _ in changes]):
        note("ignored", display(path))
    for path, old_path in changes:
        label = display(path)
        if contains_term(path, terms):
            note("sensitive_path")
        blob = git(root, "cat-file", "blob", blob_prefix + path)
        paths = [old_path, path] if old_path else [path]
        diff_args = ("diff", *diff_range, "--no-ext-diff", "--no-textconv",
                     "--find-renames", "--find-copies")
        stat = git(root, *diff_args, "--numstat", "-z", "--", *paths)
        binary = b"\0" in blob[:8000] or any(
            row.startswith(b"-\t-\t") for row in stat.split(b"\0")
        )
        if binary:
            if contains_term(decoded(blob), terms):
                note("sensitive_binary", label)
            if path not in TRACE_ALLOWLIST and TRACE_BYTES.search(blob):
                note("residue_binary", label)
        else:
            patch = git(root, *diff_args, "--no-color", "--unified=0", "--", *paths)
            additions = added_lines(patch)
            if any(contains_term(line, terms) for line in additions):
                note("sensitive_lines", label)
            if path not in TRACE_ALLOWLIST and any(TRACE_TEXT.search(line) for line in additions):
                note("residue_lines", label)
    return issues


def check_staged(root: Path, terms_path: Path | None = None) -> list[str]:
    terms = load_terms(root, terms_path)
    return scan_changes(root, staged_changes(root), terms, ("--cached",), ":")


def check_message(text: str, terms: tuple[str, ...], skip_comments: bool = True) -> list[str]:
    """Block agent names, attribution trailers and local terms in a message.

    Only those three classes are inspected. A message that retires an old
    download entry or quotes a local path is legitimate work and must stay
    committable, so the staged-change residue rules are deliberately not reused
    here. While editing, comment lines are not part of the message, and
    everything after the scissors marker is the diff that ``git commit -v``
    appends, so scanning skips the former and stops at the latter. Once a
    message is about to be published it is read verbatim instead
    (``skip_comments=False``): the comment lines are then real content, because
    ``-m`` never strips them, and scissors never appear.
    """
    issues = []
    for line in text.splitlines():
        if skip_comments and line.startswith("#"):
            if line.startswith(SCISSORS):
                break
            continue
        lowered = line.casefold()
        if MESSAGE_TOOL_PATTERN.search(line):
            issues.append("Agent name in commit message.")
        if "co-authored-by" in lowered:
            issues.append("Attribution trailer in commit message.")
        if any(term in lowered for term in terms):
            issues.append("Local sensitive term in commit message (value withheld).")
    return issues


def read_push_records(data: bytes | str) -> list[tuple[str, str, str, str]]:
    """Parse what Git writes to a pre-push hook: four fields per ref update."""
    if isinstance(data, bytes):
        data = decoded(data)
    records = []
    for line in data.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 4:
            raise GuardError("Unrecognised pre-push input; refusing to guess what to check.")
        records.append((fields[0], fields[1], fields[2], fields[3]))
    return records


def peeled_commit(root: Path, rev: str) -> str:
    return os.fsdecode(git(root, "rev-parse", "--verify", rev + "^{commit}")).strip()


def unpublished_commits(root: Path, tips: list[str]) -> list[str]:
    """Commits reachable from the tips that no remote has yet.

    The exclusion deliberately covers every remote, not the push target: when
    the target is a remote that has never been fetched, excluding only it would
    rescan all of history and block pushes over long-settled content.
    """
    if not tips:
        return []
    order, seen = [], set()
    for line in git(root, "rev-list", *tips, "--not", "--remotes").split(b"\n"):
        sha = os.fsdecode(line).strip()
        if sha and sha not in seen:
            seen.add(sha)
            order.append(sha)
    return order


def commit_details(root: Path, commit: str):
    """Author, committer and first parent of a commit."""
    fields = git(root, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%P",
                 commit).split(b"\0")
    if len(fields) < 5:
        raise GuardError(f"Cannot read the metadata of {commit[:8]}.")
    author, committer = (decoded(fields[0]).strip(), decoded(fields[1]).strip()), \
                        (decoded(fields[2]).strip(), decoded(fields[3]).strip())
    parents = decoded(fields[4]).split()
    return author, committer, (parents[0] if parents else None)


def tag_details(root: Path, tag_sha: str):
    """Name, tagger identity and message of an annotated tag object."""
    header, _, message = decoded(git(root, "cat-file", "-p", tag_sha)).partition("\n\n")
    name, identity = tag_sha[:8], None
    for line in header.splitlines():
        if line.startswith("tag "):
            name = line[len("tag "):].strip()
        elif line.startswith("tagger "):
            match = TAGGER_LINE.match(line[len("tagger "):].strip())
            identity = (match.group(1), match.group(2)) if match else ("", "")
    return name, identity, message


def check_commit(root: Path, commit: str, terms: tuple[str, ...],
                 identity: tuple[str, str] = EXPECTED_IDENTITY) -> list[str]:
    """Identity, message and content of one commit that is not public yet."""
    short = commit[:8]
    issues = []
    author, committer, parent = commit_details(root, commit)
    if author != identity:
        issues.append(f"Unexpected author on commit {short}.")
    if committer != identity:
        issues.append(f"Unexpected committer on commit {short}.")
    message = decoded(git(root, "show", "-s", "--format=%B", commit))
    issues.extend(f"{issue} (commit {short})"
                  for issue in check_message(message, terms, skip_comments=False))
    # Each commit is compared with its own first parent: a line that was added
    # and later deleted is invisible in an end-to-end diff but stays public in
    # the history that is being pushed.
    base = parent or EMPTY_TREE
    changes = changed_paths(root, (base, commit))
    issues.extend(scan_changes(root, changes, terms, (base, commit), commit + ":", short))
    return issues


def check_tag(root: Path, tag_sha: str, terms: tuple[str, ...],
              identity: tuple[str, str] = EXPECTED_IDENTITY) -> list[str]:
    """Identity and message of one annotated tag object that is not public yet."""
    name, tagger, message = tag_details(root, tag_sha)
    label = name if not contains_term(name, terms) else "<withheld tag>"
    issues = []
    if tagger != identity:
        issues.append(f"Unexpected tagger on annotated tag {label}.")
    issues.extend(f"{issue} (tag {label})"
                  for issue in check_message(message, terms, skip_comments=False))
    return issues


def check_pre_push(root: Path, records: list[tuple[str, str, str, str]],
                   terms_path: Path | None = None,
                   identity: tuple[str, str] = EXPECTED_IDENTITY) -> list[str]:
    """Gate everything a push would publish: identity, message and content.

    A deletion carries an all-zero local SHA and publishes nothing, so it is
    skipped. Lightweight tags have no tag object and are covered by the commit
    they point at; annotated tags are checked in their own right.
    """
    terms = load_terms(root, terms_path)
    tips, tags = [], []
    for _local_ref, local_sha, _remote_ref, _remote_sha in records:
        if not local_sha.strip("0"):
            continue
        if decoded(git(root, "cat-file", "-t", local_sha)).strip() == "tag":
            if local_sha not in tags:
                tags.append(local_sha)
                tips.append(peeled_commit(root, local_sha))
        elif local_sha not in tips:
            tips.append(local_sha)
    issues = []
    for tag_sha in tags:
        issues.extend(check_tag(root, tag_sha, terms, identity))
    for commit in unpublished_commits(root, tips):
        issues.extend(check_commit(root, commit, terms, identity))
    return issues


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        root = Path(os.fsdecode(git(Path.cwd(), "rev-parse", "--show-toplevel")).strip())
        if not args:
            issues = check_staged(root)
        elif args[0] == "--commit-msg" and len(args) == 2:
            message = Path(args[1]).read_text(encoding="utf-8", errors="replace")
            issues = check_message(message, load_terms(root))
        elif args[0] == "--pre-push" and len(args) in (2, 3):
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            issues = check_pre_push(root, read_push_records(stream.read()))
        else:
            print("[commit guard] usage: pre_commit_guard.py [--commit-msg <file>"
                  " | --pre-push <remote> [<url>]]", file=sys.stderr)
            return 1
    except (GuardError, OSError) as exc:
        print(f"[commit guard] BLOCKED: {exc}", file=sys.stderr)
        return 1
    if issues:
        print("[commit guard] BLOCKED:\n- " + "\n- ".join(issues), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
