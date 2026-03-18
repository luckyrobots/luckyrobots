"""CLI for luckyrobots portfolio PR discovery.

Registered as the ``portfolio`` subcommand of the top-level ``luckyrobots`` CLI.
Usage: ``luckyrobots portfolio find --user <github-username>``
"""

from __future__ import annotations

import click


@click.group("portfolio")
def portfolio():
    """Discover and rank GitHub PRs suitable for a portfolio."""
    pass


@portfolio.command("find")
@click.argument("username")
@click.option(
    "--repo",
    "repos",
    multiple=True,
    default=None,
    help=(
        "Repository to search in the form owner/repo.  "
        "Can be specified multiple times.  "
        "Defaults to luckyrobots/luckyrobots."
    ),
)
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub personal access token.")
@click.option("--top", default=10, type=int, show_default=True, help="Number of results to show.")
@click.option(
    "--include-open/--no-include-open",
    default=True,
    show_default=True,
    help="Include open pull requests in the search.",
)
@click.option(
    "--min-score",
    default=0.0,
    type=float,
    show_default=True,
    help="Minimum portfolio score to display.",
)
def find(username, repos, token, top, include_open, min_score):
    """Find notable pull requests by USERNAME for portfolio use.

    \b
    Examples:
      luckyrobots portfolio find ethanmclark1
      luckyrobots portfolio find ethanmclark1 --repo luckyrobots/luckyrobots --top 5
      luckyrobots portfolio find devrim --token ghp_xxx
    """
    from .finder import DEFAULT_REPOS, find_notable_prs

    repo_list = list(repos) if repos else DEFAULT_REPOS

    click.echo(
        f"Searching for notable PRs by {click.style(username, bold=True)} "
        f"in {len(repo_list)} repo(s)..."
    )
    for r in repo_list:
        click.echo(f"  • {r}")
    click.echo()

    try:
        results = find_notable_prs(
            username=username,
            repos=repo_list,
            token=token,
            top_n=top,
            include_open=include_open,
        )
    except Exception as exc:  # noqa: BLE001
        raise click.ClickException(str(exc)) from exc

    results = [pr for pr in results if pr.score >= min_score]

    if not results:
        click.echo("No notable pull requests found.")
        return

    click.echo(
        click.style(
            f"Top {len(results)} pull request(s) for {username}:\n",
            bold=True,
        )
    )
    for rank, pr in enumerate(results, start=1):
        state_label = (
            click.style("merged", fg="green")
            if pr.merged
            else (
                click.style("open", fg="cyan")
                if pr.state == "open"
                else click.style("closed", fg="red")
            )
        )
        click.echo(
            f"{rank:>2}. [{state_label}] "
            + click.style(f"#{pr.number}", bold=True)
            + f" — {pr.title}"
        )
        click.echo(f"     {pr.url}")
        click.echo(
            f"     Score: {pr.score:.0f}  |  "
            f"{pr.changed_files} files  |  "
            f"+{pr.additions}/-{pr.deletions} lines  |  "
            f"{pr.comments + pr.review_comments} comment(s)"
        )
        if pr.reasons:
            click.echo(f"     Highlights: {', '.join(pr.reasons)}")
        click.echo()
