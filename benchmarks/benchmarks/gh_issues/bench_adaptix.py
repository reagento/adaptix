from dataclasses import dataclass
from datetime import datetime
from typing import List

import pytest

from adaptix import CodeGenBackend, DebugTrail, Retort, name_mapping
from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.bench_api import benchmark_plan


@dataclass
class SimpleUser:
    login: str
    id: int
    node_id: str
    avatar_url: str
    gravatar_id: str | None
    url: str
    html_url: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str
    site_admin: bool
    name: str | None = None
    email: str | None = None
    starred_at: datetime | None = None


@dataclass
class Label:
    id: int
    node_id: str
    url: str
    name: str
    description: str | None
    color: str
    default: bool


@dataclass
class Reactions:
    url: str
    total_count: int
    plus_one: int
    minus_one: int
    laugh: int
    confused: int
    heart: int
    hooray: int
    eyes: int
    rocket: int


@dataclass
class PullRequest:
    diff_url: str | None
    html_url: str | None
    patch_url: str | None
    url: str | None
    merged_at: datetime | None = None


@dataclass
class Issue:
    id: int
    node_id: str
    url: str
    repository_url: str
    labels_url: str
    comments_url: str
    events_url: str
    html_url: str
    number: int
    state: IssueState
    state_reason: StateReason | None
    title: str
    user: SimpleUser | None
    labels: List[Label]
    assignee: SimpleUser | None
    assignees: List[SimpleUser] | None
    locked: bool
    active_lock_reason: str | None
    comments: int
    closed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    author_association: AuthorAssociation
    reactions: Reactions | None = None
    pull_request: PullRequest | None = None
    body_html: str | None = None
    body_text: str | None = None
    timeline_url: str | None = None
    body: str | None = None


@dataclass
class GetRepoIssuesResponse:
    data: List[Issue]


retort = Retort(
    recipe=[
        name_mapping(
            Reactions,
            map={
                "plus_one": "+1",
                "minus_one": "-1",
            },
        ),
        name_mapping(
            omit_default=True,
        ),
    ],
)


@pytest.mark.parametrize("codegen_backend", list(CodeGenBackend))
def test_loading(codegen_backend):
    if codegen_backend == CodeGenBackend.X86_64 and skip_native(benchmark_env_spec()):
        pytest.skip("Native code generation is unsupported on this platform")
    assert (
        retort.replace(codegen_backend=codegen_backend).load(create_dumped_response(), GetRepoIssuesResponse)
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


@pytest.mark.parametrize("codegen_backend", list(CodeGenBackend))
def test_dumping(codegen_backend):
    if codegen_backend == CodeGenBackend.X86_64 and skip_native(benchmark_env_spec()):
        pytest.skip("Native code generation is unsupported on this platform")
    assert (
        retort.replace(codegen_backend=codegen_backend).dump(
            create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser),
        )
        ==
        create_dumped_response()
    )


def bench_loading(strict_coercion: bool, debug_trail: str, codegen_backend: str):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail(debug_trail),
        codegen_backend=CodeGenBackend(codegen_backend),
    ).get_loader(GetRepoIssuesResponse)

    data = create_dumped_response()
    return benchmark_plan(loader, data)


def bench_dumping(debug_trail: str, codegen_backend: str):
    dumper = retort.replace(
        debug_trail=DebugTrail(debug_trail),
        codegen_backend=CodeGenBackend(codegen_backend),
    ).get_dumper(GetRepoIssuesResponse)

    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(dumper, data)
