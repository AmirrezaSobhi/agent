import re
from pathlib import Path
import pytest
from tools.release_sync.github_release_sync import run_from_environment, SyncError
from tests.test_ci_topology import _job_block

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('channel',[None,'internal','PUBLIC','unknown'])
def test_internal_tag_cannot_reach_github_credentials_or_network(monkeypatch,channel):
    env={'CI_COMMIT_TAG':'v0.1.5','CI_COMMIT_SHA':'a'*40,'CI_COMMIT_REF_PROTECTED':'true',
         'CI_PROJECT_ID':'1','CI_PROJECT_PATH':'root/agent','CI_PIPELINE_SOURCE':'push'}
    monkeypatch.delenv('MT5_RELEASE_CHANNEL',raising=False)
    for key,value in env.items():monkeypatch.setenv(key,value)
    if channel is not None:monkeypatch.setenv('MT5_RELEASE_CHANNEL',channel)
    with pytest.raises(SyncError,match='public release channel'):run_from_environment()


def test_ci_internal_default_and_immutable_installer_dependency_graph():
    source=(ROOT/'.gitlab-ci.yml').read_text()
    assert "MT5_RELEASE_CHANNEL: 'internal'" in source
    for name in ('release:github-sync','release:github-reconcile'):
        assert '$MT5_RELEASE_CHANNEL == "public"' in _job_block(source,name)
    publisher=_job_block(source,'release:gitlab-publish')
    for name in ('package:windows','installer:build','installer:verify'):
        assert f'job: {name}\n      artifacts: true' in publisher
    assert 'when: manual' in publisher and 'allow_failure: false' in publisher
    for name in ('installer:build','installer:verify','worker:build'):
        assert '$CI_COMMIT_BRANCH == "develop"' not in _job_block(source,name)
