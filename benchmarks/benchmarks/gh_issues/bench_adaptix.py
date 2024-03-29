from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from adaptix import DebugTrail, Retort, name_mapping
from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan


@dataclass
class SimpleUser:
    login: str
    id: int
    node_id: str
    avatar_url: str
    gravatar_id: Optional[str]
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
    name: Optional[str] = None
    email: Optional[str] = None
    starred_at: Optional[datetime] = None


@dataclass
class Label:
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
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
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None


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
    state_reason: Optional[StateReason]
    title: str
    user: Optional[SimpleUser]
    labels: List[Label]
    assignee: Optional[SimpleUser]
    assignees: Optional[List[SimpleUser]]
    locked: bool
    active_lock_reason: Optional[str]
    comments: int
    closed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    author_association: AuthorAssociation
    reactions: Optional[Reactions] = None
    pull_request: Optional[PullRequest] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    timeline_url: Optional[str] = None
    body: Optional[str] = None


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


def test_loading():
    assert (
        retort.load(create_dumped_response(), GetRepoIssuesResponse)
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


def test_dumping():
    assert (
        retort.dump(create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser))
        ==
        create_dumped_response()
    )


def bench_loading(strict_coercion: bool, debug_trail: str):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail(debug_trail),
    ).get_loader(GetRepoIssuesResponse)

    data = create_dumped_response()
    return benchmark_plan(loader, data)


def bench_dumping(debug_trail: str):
    dumper = retort.replace(
        debug_trail=DebugTrail(debug_trail),
    ).get_dumper(GetRepoIssuesResponse)

    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(dumper, data)
