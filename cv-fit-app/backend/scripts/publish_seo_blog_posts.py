"""
Generate SEO blog posts, commit them, and push the current branch.

This wrapper is intended for scheduled jobs. It keeps a daily state file so an
OpenClaw retry does not publish duplicate posts for the same date.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
LOGS_DIR = BACKEND_DIR / "logs"
STATE_PATH = LOGS_DIR / "seo-blog-publish-state.json"
LOCK_PATH = LOGS_DIR / "seo-blog-publish.lock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate, commit, and push SEO blog posts.")
    parser.add_argument("--min", type=int, default=2, help="Minimum posts to generate.")
    parser.add_argument("--max", type=int, default=4, help="Maximum posts to generate.")
    parser.add_argument("--count", type=int, help="Exact number of posts to generate.")
    parser.add_argument("--topic", action="append", default=[], help="Optional topic seed. Can be repeated.")
    parser.add_argument("--date", help="Publish date in YYYY-MM-DD. Defaults to Asia/Ho_Chi_Minh today.")
    parser.add_argument("--remote", default="origin", help="Git remote to push.")
    parser.add_argument("--branch", help="Git branch to push. Defaults to current branch.")
    parser.add_argument("--no-push", action="store_true", help="Commit but do not push.")
    parser.add_argument("--force", action="store_true", help="Ignore today's published state and run again.")
    return parser.parse_args()


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], PROJECT_DIR)
    return Path(result.stdout.strip())


def current_branch(repo_root: Path) -> str:
    result = run(["git", "branch", "--show-current"], repo_root)
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("Cannot publish from a detached HEAD.")
    return branch


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def write_state(state: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_generator_json(stdout: str) -> dict:
    marker = '{\n  "count"'
    start = stdout.rfind(marker)
    if start == -1:
        raise RuntimeError(f"Could not find generator JSON summary in stdout:\n{stdout}")
    return json.loads(stdout[start:])


def generator_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(BACKEND_DIR / "scripts" / "generate_seo_blog_posts.py"),
    ]
    if args.count is not None:
        cmd.extend(["--count", str(args.count)])
    else:
        cmd.extend(["--min", str(args.min), "--max", str(args.max)])
    if args.date:
        cmd.extend(["--date", args.date])
    for topic in args.topic:
        cmd.extend(["--topic", topic])
    return cmd


def stage_generated_posts(repo_root: Path, posts: list[dict[str, str]]) -> list[str]:
    files: list[str] = []
    for post in posts:
        slug = post.get("slug")
        if not slug:
            continue
        files.append(f"cv-fit-app/frontend/content/blog/{slug}.mdx")
        cover_path = post.get("coverPath")
        if cover_path:
            files.append(f"cv-fit-app/{cover_path}")
    if not files:
        raise RuntimeError("Generator returned no posts to stage.")

    run(["git", "add", *files], repo_root)
    return files


def has_staged_changes(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        text=True,
    )
    return result.returncode != 0


def main() -> int:
    args = parse_args()
    publish_date = args.date or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        state = load_state()
        if not args.force and state.get("date") == publish_date and state.get("status") == "published":
            print(json.dumps({"status": "skipped", "reason": "already_published", "state": state}, ensure_ascii=False, indent=2))
            return 0

        repo_root = git_root()
        branch = args.branch or current_branch(repo_root)
        started_at = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()
        write_state({"date": publish_date, "status": "running", "startedAt": started_at})

        generator = run(generator_command(args), BACKEND_DIR)
        if generator.stderr:
            print(generator.stderr, file=sys.stderr)
        print(generator.stdout)

        summary = extract_generator_json(generator.stdout)
        posts = summary.get("posts", [])
        files = stage_generated_posts(repo_root, posts)

        if not has_staged_changes(repo_root):
            write_state(
                {
                    "date": publish_date,
                    "status": "published",
                    "startedAt": started_at,
                    "finishedAt": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
                    "files": files,
                    "commit": None,
                    "note": "No staged changes after generation.",
                }
            )
            print(json.dumps({"status": "skipped", "reason": "no_changes", "files": files}, ensure_ascii=False, indent=2))
            return 0

        commit_message = f"chore: publish SEO blog posts {publish_date}"
        run(["git", "commit", "-m", commit_message], repo_root)
        commit_hash = run(["git", "rev-parse", "HEAD"], repo_root).stdout.strip()

        if not args.no_push:
            run(["git", "push", args.remote, branch], repo_root)

        final_state = {
            "date": publish_date,
            "status": "published",
            "startedAt": started_at,
            "finishedAt": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            "files": files,
            "commit": commit_hash,
            "pushed": not args.no_push,
            "remote": args.remote,
            "branch": branch,
        }
        write_state(final_state)
        print(json.dumps({"status": "published", **final_state}, ensure_ascii=False, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
