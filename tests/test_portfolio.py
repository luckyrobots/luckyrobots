"""Tests for the portfolio PR finder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from luckyrobots.cli import cli
from luckyrobots.portfolio.finder import PRScore, _score_pr, find_notable_prs

# ---------------------------------------------------------------------------
# Unit tests for the scoring logic
# ---------------------------------------------------------------------------


class TestScorePr:
    """Tests for _score_pr()."""

    def test_merged_pr_earns_highest_base_score(self):
        score, reasons = _score_pr(
            {
                "merged": True,
                "state": "closed",
                "description": "",
                "title": "",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert score >= 30
        assert "merged" in reasons

    def test_open_pr_earns_lower_base_score(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "open",
                "description": "",
                "title": "",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert score == 10
        assert "open" in reasons

    def test_long_description_adds_points(self):
        body = "x" * 100
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": body,
                "title": "",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert "has description" in reasons

    def test_many_changed_files_adds_points(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": "",
                "title": "",
                "changed_files": 15,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert any("files changed" in r for r in reasons)
        assert score >= 20

    def test_large_diff_adds_points(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": "",
                "title": "",
                "changed_files": 0,
                "additions": 300,
                "deletions": 200,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert any("lines changed" in r for r in reasons)

    def test_comments_add_points(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": "",
                "title": "",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 3,
                "review_comments": 3,
            }
        )
        assert any("comment" in r for r in reasons)

    def test_generic_title_does_not_earn_title_points(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": "",
                "title": "fix",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert "descriptive title" not in reasons

    def test_descriptive_title_earns_points(self):
        score, reasons = _score_pr(
            {
                "merged": False,
                "state": "closed",
                "description": "",
                "title": "Add sysid pipeline with MuJoCo optimizer",
                "changed_files": 0,
                "additions": 0,
                "deletions": 0,
                "comments": 0,
                "review_comments": 0,
            }
        )
        assert "descriptive title" in reasons


# ---------------------------------------------------------------------------
# Unit tests for PRScore dataclass
# ---------------------------------------------------------------------------


class TestPRScore:
    def _make(self, additions=10, deletions=5) -> PRScore:
        return PRScore(
            repo="luckyrobots/luckyrobots",
            number=42,
            title="Test PR",
            url="https://github.com/luckyrobots/luckyrobots/pull/42",
            state="closed",
            merged=True,
            description="desc",
            changed_files=3,
            additions=additions,
            deletions=deletions,
            comments=2,
            review_comments=1,
            score=50.0,
            reasons=["merged"],
        )

    def test_lines_changed(self):
        pr = self._make(additions=100, deletions=50)
        assert pr.lines_changed == 150


# ---------------------------------------------------------------------------
# Tests for find_notable_prs() with mocked HTTP
# ---------------------------------------------------------------------------


def _make_pr_dict(number: int, login: str = "ethanmclark1", merged_at=None) -> dict:
    return {
        "number": number,
        "user": {"login": login},
        "title": f"Feature PR #{number}",
        "html_url": f"https://github.com/luckyrobots/luckyrobots/pull/{number}",
        "state": "closed" if merged_at else "open",
        "merged_at": merged_at,
        "body": "A detailed description of the changes made in this pull request.",
        "changed_files": 8,
        "additions": 200,
        "deletions": 50,
        "comments": 4,
        "review_comments": 2,
    }


class TestFindNotablePrs:
    def test_returns_list_of_pr_scores(self):
        pr1 = _make_pr_dict(1, merged_at="2026-01-01T00:00:00Z")
        pr2 = _make_pr_dict(2, merged_at="2026-02-01T00:00:00Z")

        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            # First call returns list [pr1, pr2], subsequent return empty list (pagination end).
            # We also need to mock _fetch_pr_details calls.
            list_response = MagicMock()
            list_response.raise_for_status = MagicMock()
            list_response.json.side_effect = [[pr1, pr2], [], []]

            detail1 = MagicMock()
            detail1.raise_for_status = MagicMock()
            detail1.json.return_value = pr1

            detail2 = MagicMock()
            detail2.raise_for_status = MagicMock()
            detail2.json.return_value = pr2

            mock_get.side_effect = [
                list_response,  # list closed PRs page 1
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),  # page 2 empty
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),  # list open page 1
                detail1,  # detail PR #1
                detail2,  # detail PR #2
            ]

            results = find_notable_prs(
                username="ethanmclark1",
                repos=["luckyrobots/luckyrobots"],
                token=None,
                top_n=10,
            )

        assert len(results) >= 1
        assert all(isinstance(r, PRScore) for r in results)

    def test_top_n_limits_results(self):
        prs = [_make_pr_dict(i, merged_at="2026-01-01T00:00:00Z") for i in range(1, 6)]

        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            pages = [prs, []]
            detail_responses = [
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=pr))
                for pr in prs
            ]
            page_responses = [
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=p))
                for p in pages
            ]
            open_page = MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[]))
            mock_get.side_effect = page_responses + [open_page] + detail_responses

            results = find_notable_prs(
                username="ethanmclark1",
                repos=["luckyrobots/luckyrobots"],
                token=None,
                top_n=3,
            )

        assert len(results) <= 3

    def test_filters_by_username(self):
        pr_mine = _make_pr_dict(1, login="ethanmclark1", merged_at="2026-01-01T00:00:00Z")
        pr_other = _make_pr_dict(2, login="someone_else", merged_at="2026-01-01T00:00:00Z")

        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(
                    raise_for_status=MagicMock(),
                    json=MagicMock(return_value=[pr_mine, pr_other]),
                ),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=pr_mine)),
            ]

            results = find_notable_prs(
                username="ethanmclark1",
                repos=["luckyrobots/luckyrobots"],
                token=None,
            )

        assert all(r.number == 1 for r in results)


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestPortfolioCli:
    def test_portfolio_find_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["portfolio", "find", "--help"])
        assert result.exit_code == 0
        assert "USERNAME" in result.output

    def test_portfolio_find_no_results(self):
        runner = CliRunner()
        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                raise_for_status=MagicMock(), json=MagicMock(return_value=[])
            )
            result = runner.invoke(cli, ["portfolio", "find", "nonexistentuser123"])
        assert result.exit_code == 0
        assert "No notable pull requests found" in result.output

    def test_portfolio_find_outputs_results(self):
        pr = _make_pr_dict(42, login="testuser", merged_at="2026-01-01T00:00:00Z")
        runner = CliRunner()

        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[pr])),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=[])),
                MagicMock(raise_for_status=MagicMock(), json=MagicMock(return_value=pr)),
            ]
            result = runner.invoke(cli, ["portfolio", "find", "testuser"])

        assert result.exit_code == 0
        assert "#42" in result.output

    def test_portfolio_find_with_custom_repo(self):
        runner = CliRunner()
        with patch("luckyrobots.portfolio.finder.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                raise_for_status=MagicMock(), json=MagicMock(return_value=[])
            )
            result = runner.invoke(
                cli,
                ["portfolio", "find", "someuser", "--repo", "myorg/myrepo"],
            )
        assert result.exit_code == 0
        assert "myorg/myrepo" in result.output

    def test_portfolio_group_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["portfolio", "--help"])
        assert result.exit_code == 0
        assert "find" in result.output
