#!/usr/bin/env python3
"""
Quality Agent
- Analysoi koodin laatua
- Etsii bugit ja ongelmat (AST-heuristiikat)
- Ehdottaa parannuksia
- Tarkistaa PEP8 (ruff/pycodestyle fallback)

Noudattaa repo-standardeja:
- Python 3.10+
- asyncio, ei blokkaavia kutsuja kuumissa poluissa
- logging + RotatingFileHandler (JSON)
- Aikavyöhyke: Europe/Helsinki
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from zoneinfo import ZoneInfo

HELSINKI_TZ = ZoneInfo("Europe/Helsinki")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(getattr(record, "extra"), dict):
            payload.update(getattr(record, "extra"))
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(log_path: str = "quality_agent.log", *, level: int = logging.INFO) -> None:
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    file_h = RotatingFileHandler(p, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    stream_h = logging.StreamHandler(sys.stdout)
    fmt = JsonFormatter()
    file_h.setFormatter(fmt)
    stream_h.setFormatter(fmt)
    logging.basicConfig(level=level, handlers=[file_h, stream_h], force=True)


logger = logging.getLogger(__name__)


# --------------------------- Data models ---------------------------
@dataclass
class Pep8Issue:
    path: str
    line: int
    col: int
    code: str
    message: str


@dataclass
class AstIssue:
    path: str
    line: int
    type: str
    message: str


@dataclass
class ImprovementSuggestion:
    path: str
    line: Optional[int]
    suggestion: str


@dataclass
class QualityReport:
    scanned_files: int
    pep8_issues: List[Pep8Issue]
    ast_issues: List[AstIssue]
    suggestions: List[ImprovementSuggestion]
    stats: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scanned_files": self.scanned_files,
            "pep8_issues": [asdict(i) for i in self.pep8_issues],
            "ast_issues": [asdict(i) for i in self.ast_issues],
            "suggestions": [asdict(s) for s in self.suggestions],
            "stats": self.stats,
            "timestamp": self.timestamp,
        }


# --------------------------- Utils ---------------------------
def _list_python_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for p in root.iterdir():
        if p.name.startswith('.'):
            continue
        if p.is_dir():
            # Only scan top-level .py files and sources/ tests/ by default to be fast
            if p.name in {"sources", "tests"}:
                for sub in p.rglob("*.py"):
                    files.append(sub)
            continue
        if p.suffix == ".py":
            files.append(p)
    return files


async def _run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a subprocess command asynchronously, return (rc, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out_b, err_b = await proc.communicate()
    return proc.returncode, out_b.decode("utf-8", "replace"), err_b.decode("utf-8", "replace")


# --------------------------- PEP8 checkers ---------------------------
PEP8_RUFF_PATTERN = re.compile(r"^(?P<path>.*?):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[A-Z]\d{3,4})\s+(?P<message>.*)$")
PEP8_PYCODESTYLE_PATTERN = re.compile(r"^(?P<path>.*?):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>\w\d{3})\s+(?P<message>.*)$")


async def run_pep8_checks(files: List[Path]) -> List[Pep8Issue]:
    if not files:
        return []

    # Prefer ruff if available
    ruff_bin = os.getenv("RUFF_BIN", "ruff")
    try:
        rc, out, err = await _run_cmd([ruff_bin, "check", "--quiet", *[str(f) for f in files]])
        if rc in (0, 1):  # 1 means issues found
            issues: List[Pep8Issue] = []
            for line in out.splitlines():
                m = PEP8_RUFF_PATTERN.match(line.strip())
                if m:
                    issues.append(
                        Pep8Issue(
                            path=m.group("path"),
                            line=int(m.group("line")),
                            col=int(m.group("col")),
                            code=m.group("code"),
                            message=m.group("message"),
                        )
                    )
            return issues
        else:
            logger.warning("ruff returned rc=%s: %s", rc, err.strip())
    except FileNotFoundError:
        logger.info("ruff not found; falling back to pycodestyle")

    # Fallback to pycodestyle
    pycodestyle_bin = os.getenv("PYCODESTYLE_BIN", "pycodestyle")
    try:
        rc, out, err = await _run_cmd([pycodestyle_bin, *[str(f) for f in files]])
        if rc in (0, 1):
            issues = []
            for line in out.splitlines():
                m = PEP8_PYCODESTYLE_PATTERN.match(line.strip())
                if m:
                    issues.append(
                        Pep8Issue(
                            path=m.group("path"),
                            line=int(m.group("line")),
                            col=int(m.group("col")),
                            code=m.group("code"),
                            message=m.group("message"),
                        )
                    )
            return issues
        else:
            logger.warning("pycodestyle returned rc=%s: %s", rc, err.strip())
            return []
    except FileNotFoundError:
        logger.warning("Neither ruff nor pycodestyle found; skipping PEP8 checks")
        return []


# --------------------------- AST Heuristics ---------------------------
import ast


class AstVisitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.issues: List[AstIssue] = []

    def report(self, node: ast.AST, type_: str, msg: str) -> None:
        line = getattr(node, "lineno", 1)
        self.issues.append(AstIssue(path=str(self.path), line=int(line), type=type_, message=msg))

    # Heuristic: bare except
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> Any:  # type: ignore[override]
        if node.type is None:
            self.report(node, "bare-except", "Bare except: catches all exceptions; specify Exception or narrower")
        self.generic_visit(node)

    # Heuristic: print in library code
    def visit_Call(self, node: ast.Call) -> Any:  # type: ignore[override]
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            self.report(node, "print-call", "Use logging instead of print in production code")
        self.generic_visit(node)

    # Heuristic: blocking time.sleep in async def
    def visit_Await(self, node: ast.Await) -> Any:  # type: ignore[override]
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # type: ignore[override]
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if n.func.value and isinstance(n.func.value, ast.Name) and n.func.value.id == "time" and n.func.attr == "sleep":
                    self.report(n, "blocking-sleep", "Use asyncio.sleep in async functions, not time.sleep")
        self.generic_visit(node)

    # Heuristic: wildcard import
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:  # type: ignore[override]
        for alias in node.names:
            if alias.name == "*":
                self.report(node, "wildcard-import", "Avoid wildcard imports; import explicitly")
        self.generic_visit(node)


def analyze_ast(files: List[Path]) -> List[AstIssue]:
    issues: List[AstIssue] = []
    for f in files:
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
            v = AstVisitor(f)
            v.visit(tree)
            issues.extend(v.issues)
        except SyntaxError as e:
            issues.append(AstIssue(path=str(f), line=getattr(e, "lineno", 1) or 1, type="syntax-error", message=str(e)))
        except Exception as e:
            issues.append(AstIssue(path=str(f), line=1, type="parse-error", message=str(e)))
    return issues


# --------------------------- Suggestions ---------------------------
def build_suggestions(pep8: List[Pep8Issue], ast_issues: List[AstIssue]) -> List[ImprovementSuggestion]:
    suggestions: List[ImprovementSuggestion] = []
    # Group by file
    by_file: Dict[str, List[str]] = {}
    for i in pep8:
        by_file.setdefault(i.path, []).append(i.code)
        if i.code.startswith("E5"):
            suggestions.append(ImprovementSuggestion(path=i.path, line=i.line, suggestion="Fix line length/formatting to meet PEP8"))
    for a in ast_issues:
        if a.type == "bare-except":
            suggestions.append(ImprovementSuggestion(path=a.path, line=a.line, suggestion="Replace bare except with explicit Exception or narrower"))
        elif a.type == "print-call":
            suggestions.append(ImprovementSuggestion(path=a.path, line=a.line, suggestion="Replace print with logging.getLogger(__name__).info/debug")
            )
        elif a.type == "blocking-sleep":
            suggestions.append(ImprovementSuggestion(path=a.path, line=a.line, suggestion="Use asyncio.sleep in async functions"))
        elif a.type == "wildcard-import":
            suggestions.append(ImprovementSuggestion(path=a.path, line=a.line, suggestion="Avoid 'from x import *'"))
        elif a.type in {"syntax-error", "parse-error"}:
            suggestions.append(ImprovementSuggestion(path=a.path, line=a.line, suggestion="Fix syntax/parse error"))
    # De-duplicate
    dedup: Dict[Tuple[str, Optional[int], str], ImprovementSuggestion] = {}
    for s in suggestions:
        dedup[(s.path, s.line, s.suggestion)] = s
    return list(dedup.values())


# --------------------------- Orchestrator ---------------------------
async def analyze_project(root: str | Path = ".") -> QualityReport:
    base = Path(root).resolve()
    files = _list_python_files(base)
    logger.info("scanning", extra={"extra": {"files": len(files)}})

    pep8_issues = await run_pep8_checks(files)

    # AST analysis can be CPU-bound; keep it synchronous but outside event loop blocking calls
    loop = asyncio.get_running_loop()
    ast_issues = await loop.run_in_executor(None, analyze_ast, files)

    suggestions = build_suggestions(pep8_issues, ast_issues)

    stats = {
        "pep8_issue_count": len(pep8_issues),
        "ast_issue_count": len(ast_issues),
        "suggestion_count": len(suggestions),
        "files": len(files),
    }

    report = QualityReport(
        scanned_files=len(files),
        pep8_issues=pep8_issues,
        ast_issues=ast_issues,
        suggestions=suggestions,
        stats=stats,
        timestamp=datetime.now(HELSINKI_TZ).isoformat(timespec="seconds"),
    )
    return report


async def main_async(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Quality Agent: code quality and PEP8 analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Project root (default=.)")
    parser.add_argument("--json-out", dest="json_out", default=None, help="Write JSON report to file")
    parser.add_argument("--fail-on", dest="fail_on", default="", help="Comma codes: pep8,ast to set nonzero exit")
    args = parser.parse_args(argv)

    setup_logging("quality_agent.log", level=logging.INFO)

    report = await analyze_project(args.path)

    # Console summary
    print("\nCode Quality Summary")
    print(f"  Files: {report.scanned_files}")
    print(f"  PEP8 issues: {report.stats['pep8_issue_count']}")
    print(f"  AST issues: {report.stats['ast_issue_count']}")
    print(f"  Suggestions: {report.stats['suggestion_count']}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSON report: {args.json_out}")

    # Determine exit code
    rc = 0
    fail_set = {s.strip() for s in args.fail_on.split(',') if s.strip()}
    if ("pep8" in fail_set and report.stats["pep8_issue_count"] > 0) or (
        "ast" in fail_set and report.stats["ast_issue_count"] > 0
    ):
        rc = 2

    logger.info("quality-report", extra={"extra": report.to_dict()})
    return rc


def main() -> None:
    try:
        rc = asyncio.run(main_async())
        # Do not use sys.exit inside async context; here it's safe after loop completes
        sys.exit(rc)
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()

