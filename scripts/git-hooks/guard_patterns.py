"""Pattern registry for this repository's commit and push guards.

The guard module imports these constants and never spells them itself, so the
literals live in exactly one place - and the guard can never block its own
commit. Only what this repository needs is registered here: build-machine paths,
retired download entries, agent names, session UUIDs, and the identity every
published commit and annotated tag must carry.
"""

# A separator is a backslash or a forward slash. Built with chr(92) on purpose:
# a literal "\\" inside a character class does not survive every editing path,
# and when it collapses to "\/" the class silently means "slash only" -- which is
# how backslash-separated Windows paths slipped past an earlier version of this
# gate.
_SEP = "[" + chr(92) + chr(92) + "/]"

WINDOWS_USER_PATH = "[A-Za-z]:" + _SEP + "{1,2}Users" + _SEP
SHARED_MACHINE_RESIDUE = "OneDrive|scratchpad|" + _SEP + "Temp" + _SEP
RETIRED_HOSTS = r"markdownpanel-virtualhost|files\.fm"

# "copilot" carries a negative lookahead: "Snapdragon X Copilot+ PC" is a
# hardware product the project legitimately names, and must not be blocked.
AI_TOOL_NAMES = r"claude|codex|anthropic|chatgpt|openai|gemini|copilot(?!\+)"
SESSION_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Agent names the guards block in addition to the ones above. Kept separate so the
# residue pattern is assembled in one place. The product's own model name (Qwen)
# must never be added here.
COMMIT_GUARD_EXTRA_AI_NAMES = r"deepseek|codebuddy|qoder"

# A push publishes history that cannot be taken back, so every commit and
# annotated tag headed for a remote is checked against this identity.
EXPECTED_IDENTITY = ("Alex Li", "ncorecpu@gmail.com")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
