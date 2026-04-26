#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# Color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


TODO_FILE = "project_todos.md"

# File extensions and their comment syntax
COMMENT_PATTERNS = {
    ".py": ("#", None),
    ".vhd": ("--", None),
    ".vhdl": ("--", None),
    ".v": ("//", None),
    ".sv": ("//", None),
    ".c": ("//", "/*"),
    ".h": ("//", "/*"),
    ".cpp": ("//", "/*"),
    ".tcl": ("#", None),
    ".do": ("#", None),
    ".md": (None, None),
}

# Directories to exclude (common virtual envs, build dirs, version control)
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "env",
    "virtualenv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    ".eggs",
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    "node_modules",
    "coverage_html_report",
    ".coverage",
    "htmlcov",
}

# Files to exclude
EXCLUDED_FILES = {
    "scan_todos.py",
    "project_todos.md",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
}


def should_exclude_path(path):
    """Check if path should be excluded from scanning"""
    parts = Path(path).parts

    # Check for excluded directories
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True

    # Check for excluded file patterns (simplified)
    filename = Path(path).name
    if filename in EXCLUDED_FILES:
        return True
    if filename.endswith(".pyc") or filename.endswith(".pyo"):
        return True

    return False


def find_todos(root_dir):
    todos = []
    todo_re = re.compile(r"TODO\(([^)]+)\):\s*(.+?)(?:\s+@(\w+))?$")

    for path in Path(root_dir).rglob("*"):
        # Skip excluded directories
        if should_exclude_path(path):
            continue

        if path.suffix not in COMMENT_PATTERNS:
            continue

        single, multi = COMMENT_PATTERNS[path.suffix]
        if not single:
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line_stripped = line.strip()
                    if not line_stripped.startswith(single):
                        continue

                    match = todo_re.search(line_stripped)
                    if match:
                        owner, desc, tag = match.groups()
                        # Extract context from line if present (like @medium that wasn't captured)
                        if not tag and "@" in desc:
                            parts = desc.split("@")
                            desc = parts[0].strip()
                            tag = (
                                parts[1].strip().split()[0] if len(parts) > 1 else None
                            )

                        todos.append(
                            {
                                "file": str(path),
                                "line": line_num,
                                "owner": owner.strip(),
                                "description": desc.strip(),
                                "tag": tag.strip() if tag else "unlabeled",
                            }
                        )
        except (IOError, OSError, UnicodeDecodeError):
            continue  # Skip files we can't read

    return todos


def print_colorized_todos(todos):
    """Print TODOs to terminal with color coding"""
    if not todos:
        print(f"{Colors.GREEN}✅ No TODOs found!{Colors.END}")
        return

    # Group by priority/tag
    by_priority = defaultdict(list)
    for todo in todos:
        by_priority[todo["tag"].lower()].append(todo)

    # Define priority colors
    priority_colors = {
        "high": Colors.RED,
        "medium": Colors.YELLOW,
        "low": Colors.GREEN,
        "unlabeled": Colors.BLUE,
    }

    # Print summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}📋 TODO Summary{Colors.END}")
    print(f"{'='*60}")

    for priority in ["high", "medium", "low", "unlabeled"]:
        if priority in by_priority:
            color = priority_colors.get(priority, Colors.CYAN)
            print(
                f"{color}{priority.upper()}: {len(by_priority[priority])} items{Colors.END}"
            )

    print(f"{'='*60}\n")

    # Print detailed TODOs
    for priority, todos_list in sorted(by_priority.items()):
        if not todos_list:
            continue

        color = priority_colors.get(priority, Colors.CYAN)
        print(f"{color}{Colors.BOLD}[{priority.upper()}]{Colors.END}")
        print(f"{'-'*50}")

        for todo in todos_list:
            # Color file path based on type
            if todo["file"].endswith(".vhd") or todo["file"].endswith(".vhdl"):
                file_color = Colors.CYAN
                lang = "VHDL"
            elif todo["file"].endswith(".py"):
                file_color = Colors.GREEN
                lang = "Python"
            else:
                file_color = Colors.BLUE
                lang = "Other"

            print(
                f"  {Colors.YELLOW}⚡{Colors.END} {file_color}{todo['owner']}{Colors.END}: {todo['description']}"
            )
            print(f"    📁 {file_color}{todo['file']}:{todo['line']}{Colors.END}")
            print(f"    🏷️  [{lang}]")
            print()


def update_todo_file(todos, todo_path=TODO_FILE):
    """Generate improved Markdown TODO file"""
    with open(todo_path, "w") as f:
        f.write("# Auto-generated TODO List\n\n")
        f.write(f"*Last scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(f"**Total TODOs:** {len(todos)}\n\n")
        f.write("---\n\n")

        if not todos:
            f.write("✨ No pending TODOs! Great job!\n")
            return

        # Group by tag for better organization
        by_tag = defaultdict(list)
        for t in todos:
            by_tag[t["tag"]].append(t)

        # Priority order
        priority_order = ["high", "medium", "low", "unlabeled"]

        for tag in priority_order:
            if tag not in by_tag:
                continue

            # Icon based on priority
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "unlabeled": "⚪"}.get(
                tag, "📝"
            )

            f.write(f"## {icon} {tag.upper()}\n\n")

            for item in by_tag[tag]:
                # Determine language for badge
                if item["file"].endswith((".vhd", ".vhdl")):
                    badge = "VHDL"
                elif item["file"].endswith(".py"):
                    badge = "Python"
                else:
                    badge = "Other"

                f.write(f"- [ ] `{badge}` **{item['owner']}**: {item['description']}\n")
                f.write(f"  - 📁 `{item['file']}:{item['line']}`\n\n")

            f.write("\n")

        # Add statistics table
        f.write("---\n\n")
        f.write("## Statistics\n\n")
        f.write("| Priority | Count |\n")
        f.write("|----------|-------|\n")
        for tag in priority_order:
            if tag in by_tag:
                f.write(f"| {tag.upper()} | {len(by_tag[tag])} |\n")


def quick_stats(todos):
    """Print quick statistics without full output"""
    if not todos:
        return

    by_tag = defaultdict(int)
    by_lang = defaultdict(int)

    for todo in todos:
        by_tag[todo["tag"]] += 1
        if todo["file"].endswith((".vhd", ".vhdl")):
            by_lang["VHDL"] += 1
        elif todo["file"].endswith(".py"):
            by_lang["Python"] += 1
        else:
            by_lang["Other"] += 1

    print(f"\n{Colors.BOLD}Quick Stats:{Colors.END}")
    print(
        f"  High: {by_tag.get('high', 0)} | Medium: {by_tag.get('medium', 0)} | Low: {by_tag.get('low', 0)}"
    )
    print(
        f"  VHDL: {by_lang.get('VHDL', 0)} | Python: {by_lang.get('Python', 0)} | Other: {by_lang.get('Other', 0)}"
    )


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."

    print(f"{Colors.CYAN}🔍 Scanning {root} for TODOs...{Colors.END}")
    todos = find_todos(root)

    if not todos:
        print(f"{Colors.GREEN}✅ No TODOs found!{Colors.END}")
        sys.exit(0)

    # Print colorized output to terminal
    print_colorized_todos(todos)
    quick_stats(todos)

    # Generate markdown file
    update_todo_file(todos)
    print(f"\n{Colors.GREEN}✅ Updated {TODO_FILE}{Colors.END}")
