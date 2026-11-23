import re


_SENSITIVE_LINE = re.compile(
    r"\b(?:[\w-]*(?:token|password|passwd|secret|api[_ -]?key)|pwd|authorization|"
    r"(?:set-)?cookie|connection[_ -]?string)\b[\"']?\s*[:=]"
    r"|\bBearer\s+\S+"
    r"|\b[a-z][a-z0-9+.-]*://[^\s/]+@",
    re.IGNORECASE,
)


def redact_journal(text, token):
    lines = []
    for line in text.splitlines(keepends=True):
        if _SENSITIVE_LINE.search(line) or (token and token in line):
            lines.append("[REDACTED]\n" if line.endswith("\n") else "[REDACTED]")
        else:
            lines.append(line)
    return "".join(lines)
