"""GitHub PR discovery and scoring for portfolio use.

Fetches pull requests authored by a given user across one or more
repositories and ranks them by how "notable" they are for showcasing
as portfolio work.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

# Default repositories to search when none are specified.
DEFAULT_REPOS = ["luckyrobots/luckyrobots"]

# Minimum description length (chars) to consider a PR well-described.
_MIN_DESCRIPTION_LEN = 80

# GitHub REST API base URL.
_GITHUB_API = "https://api.github.com"


@dataclass
class PRScore:
    """Scored pull request with portfolio metadata."""

    repo: str
    number: int
    title: str
    url: str
    state: str  # "open" | "closed"
    merged: bool
    description: str
    changed_files: int
    additions: int
    deletions: int
    comments: int
    review_comments: int
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def lines_changed(self) -> int:
        return self.additions + self.deletions


def _github_headers(token: str | None) -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_user_prs(
    repo: str,
    username: str,
    state: str,
    headers: dict,
    max_pages: int = 5,
) -> list[dict]:
    """Return raw PR dicts for *username* in *repo*."""
    results: list[dict] = []
    page = 1
    while page <= max_pages:
        url = f"{_GITHUB_API}/repos/{repo}/pulls"
        resp = requests.get(
            url,
            headers=headers,
            params={"state": state, "per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for pr in data:
            if pr.get("user", {}).get("login", "").lower() == username.lower():
                results.append(pr)
        page += 1
    return results


def _fetch_pr_details(repo: str, pr_number: int, headers: dict) -> dict:
    """Fetch full PR details (includes changed_files, additions, deletions)."""
    url = f"{_GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _score_pr(pr: dict) -> tuple[float, list[str]]:
    """Compute a portfolio score for a pull request dict.

    Returns *(score, reasons)* where *reasons* lists the positive traits.
    """
    score = 0.0
    reasons: list[str] = []

    # Merged PRs are more valuable than open/closed-unmerged ones.
    if pr.get("merged"):
        score += 30
        reasons.append("merged")
    elif pr.get("state") == "open":
        score += 10
        reasons.append("open")

    # Meaningful description.
    body = pr.get("description") or ""
    if len(body) >= _MIN_DESCRIPTION_LEN:
        score += 15
        reasons.append("has description")

    # Breadth: number of changed files.
    changed_files = pr.get("changed_files", 0)
    if changed_files >= 10:
        score += 20
        reasons.append(f"{changed_files} files changed")
    elif changed_files >= 5:
        score += 10
        reasons.append(f"{changed_files} files changed")
    elif changed_files >= 2:
        score += 5
        reasons.append(f"{changed_files} files changed")

    # Depth: lines changed.
    lines = (pr.get("additions") or 0) + (pr.get("deletions") or 0)
    if lines >= 500:
        score += 20
        reasons.append(f"{lines} lines changed")
    elif lines >= 100:
        score += 10
        reasons.append(f"{lines} lines changed")
    elif lines >= 30:
        score += 5
        reasons.append(f"{lines} lines changed")

    # Community engagement: comments and reviews.
    comments = (pr.get("comments") or 0) + (pr.get("review_comments") or 0)
    if comments >= 5:
        score += 15
        reasons.append(f"{comments} comments/reviews")
    elif comments >= 1:
        score += 5
        reasons.append(f"{comments} comment(s)/review(s)")

    # Informative title (not generic).
    title = pr.get("title", "")
    generic = {"update", "fix", "wip", "cleanup", "temp", "misc"}
    if title and title.lower().strip() not in generic and len(title) >= 10:
        score += 5
        reasons.append("descriptive title")

    return score, reasons


def find_notable_prs(
    username: str,
    repos: list[str] | None = None,
    token: str | None = None,
    top_n: int = 10,
    include_open: bool = True,
) -> list[PRScore]:
    """Find and rank notable pull requests by *username* across *repos*.

    Parameters
    ----------
    username:
        GitHub username to search for.
    repos:
        List of ``owner/repo`` strings.  Defaults to :data:`DEFAULT_REPOS`.
    token:
        Optional GitHub personal access token for higher rate limits.
    top_n:
        Return at most this many results (sorted by score, highest first).
    include_open:
        When ``True``, also include open PRs in results.

    Returns
    -------
    list[PRScore]
        Ranked list of scored pull requests.
    """
    if repos is None:
        repos = DEFAULT_REPOS

    headers = _github_headers(token)
    all_scored: list[PRScore] = []

    for repo in repos:
        states = ["closed"]
        if include_open:
            states.append("open")

        raw_prs: list[dict] = []
        for state in states:
            raw_prs.extend(_fetch_user_prs(repo, username, state, headers))

        # Deduplicate by PR number (open/closed may overlap in edge cases).
        seen: set[int] = set()
        for pr in raw_prs:
            number = pr["number"]
            if number in seen:
                continue
            seen.add(number)

            # Fetch full details for file / line counts.
            try:
                details = _fetch_pr_details(repo, number, headers)
            except requests.HTTPError:
                details = pr

            merged = bool(details.get("merged_at"))
            flat = {
                "merged": merged,
                "state": details.get("state", ""),
                "description": details.get("body") or "",
                "title": details.get("title", ""),
                "changed_files": details.get("changed_files", 0),
                "additions": details.get("additions", 0),
                "deletions": details.get("deletions", 0),
                "comments": details.get("comments", 0),
                "review_comments": details.get("review_comments", 0),
            }
            score, reasons = _score_pr(flat)

            all_scored.append(
                PRScore(
                    repo=repo,
                    number=number,
                    title=details.get("title", ""),
                    url=details.get("html_url", ""),
                    state=details.get("state", ""),
                    merged=merged,
                    description=flat["description"],
                    changed_files=flat["changed_files"],
                    additions=flat["additions"],
                    deletions=flat["deletions"],
                    comments=flat["comments"],
                    review_comments=flat["review_comments"],
                    score=score,
                    reasons=reasons,
                )
            )

    all_scored.sort(key=lambda p: p.score, reverse=True)
    return all_scored[:top_n]
