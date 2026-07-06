import re
import time
import urllib.request
import urllib.parse
import urllib.error
import json

# Simple in-session cache — avoids duplicate API calls for the same exception
_cache: dict = {}

# GitHub unauthenticated rate limit: 10 req/min
_RATE_LIMIT_DELAY = 1.2  # seconds between requests to stay safe


def _build_query(exception_type: str, top_frame: str) -> str:
    """
    Build a focused GitHub issue search query.

    Strategy:
    - Always include exception type (most specific signal)
    - Include top frame method name if it looks like user code
      (skip generic names like 'main', 'run', 'execute')
    """
    GENERIC_FRAMES = {"main", "run", "execute", "start", "init", "call", "handle"}

    parts = [exception_type]

    if top_frame and top_frame.lower() not in GENERIC_FRAMES:
        # Strip class path — use only the method name
        method = top_frame.split(".")[-1].strip("()")
        if method and len(method) > 2:
            parts.append(method)

    return " ".join(parts)


def _fetch_issues(query: str) -> list:
    """
    Hit the GitHub Search Issues API and return raw results.
    Returns empty list on any error — never raises.
    """
    cache_key = query.lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    params = urllib.parse.urlencode({
        "q": query,
        "sort": "reactions",
        "order": "desc",
        "per_page": 10,
    })

    url = f"https://api.github.com/search/issues?{params}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "debuai-cli/0.1.1"
    })

    try:
        time.sleep(_RATE_LIMIT_DELAY)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("items", [])
            _cache[cache_key] = results
            return results

    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Rate limited
            return []
        return []
    except Exception:
        return []


def _score_issue(issue: dict, exception_type: str) -> int:
    """
    Score an issue by relevance.
    Higher = more relevant.
    """
    score = 0
    title = issue.get("title", "").lower()
    body  = (issue.get("body") or "").lower()
    et    = exception_type.lower()

    # Exception type in title is a strong signal
    if et in title:
        score += 10

    # Exception type in body
    if et in body:
        score += 3

    # Closed issues with lots of comments = likely resolved with a fix
    if issue.get("state") == "closed":
        score += 5

    # Comment count signals real discussion
    comments = issue.get("comments", 0)
    if comments >= 10:
        score += 4
    elif comments >= 3:
        score += 2
    elif comments < 2:
        score -= 3  # Too thin — likely noise

    return score


def search_github_issues(exception_type: str, top_frame: str) -> list:
    """
    Search GitHub for issues related to this exception.

    Args:
        exception_type: e.g. "ValueError", "NullPointerException"
        top_frame:      e.g. "parse_input", "OrderService.calculateTotal"

    Returns:
        List of up to 3 dicts, each with:
            title, url, state, comments, repo
    """
    if not exception_type or exception_type == "UnknownException":
        return []

    query   = _build_query(exception_type, top_frame)
    raw     = _fetch_issues(query)

    if not raw:
        return []

    # Score and filter
    scored = []
    for issue in raw:
        score = _score_issue(issue, exception_type)
        if score > 0:
            scored.append((score, issue))

    # Sort by score descending, take top 3
    scored.sort(key=lambda x: x[0], reverse=True)
    top3 = [issue for _, issue in scored[:3]]

    return [
        {
            "title":    issue.get("title", "Untitled"),
            "url":      issue.get("html_url", ""),
            "state":    issue.get("state", "unknown"),
            "comments": issue.get("comments", 0),
            "repo":     _extract_repo(issue.get("html_url", "")),
        }
        for issue in top3
    ]


def _extract_repo(url: str) -> str:
    """Extract 'owner/repo' from a GitHub issue URL."""
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/", url)
    return match.group(1) if match else "unknown/repo"