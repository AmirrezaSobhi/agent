"""Release metadata documentation links must work outside a repository Markdown page."""
from pathlib import Path
from urllib.parse import urlsplit
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://gitlab.local/root/agent/-/blob/main/"
PATHS = {
    "deployment/installer/README.md",
    "docs/evidence/v0.1.5/V0.1.5_FINAL_RELEASE_REPORT.md",
    "docs/architecture/CI_RUNTIME_SMOKE.md",
    "docs/releases/v0.1.5-release-unblock-runbook.md",
}


def canonical_documentation_link(url: str) -> bool:
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.netloc == "gitlab.local"
            and not parsed.query and not parsed.fragment and url.startswith(BASE)
            and url[len(BASE):] in PATHS)


def test_v015_release_documentation_links_are_canonical_and_exist():
    notes = (ROOT / "docs/releases/v0.1.5-release-notes.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", notes)
    assert set(links) == {BASE + path for path in PATHS}
    assert all(canonical_documentation_link(url) for url in links)
    assert all((ROOT / path).is_file() for path in PATHS)


@pytest.mark.parametrize("url", [
    "../../deployment/installer/README.md",
    "../evidence/v0.1.5/V0.1.5_FINAL_RELEASE_REPORT.md",
    "../architecture/CI_RUNTIME_SMOKE.md",
    "v0.1.5-release-unblock-runbook.md",
    "http://gitlab.local/root/agent/-/blob/main/deployment/installer/README.md",
    "https://external.invalid/root/agent/-/blob/main/deployment/installer/README.md",
    BASE + "../../deployment/installer/README.md",
])
def test_relative_or_non_internal_documentation_links_are_rejected(url):
    assert not canonical_documentation_link(url)
