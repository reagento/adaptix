from datetime import datetime
from typing import List, Optional

from attr import define
from cattr import Converter
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override

from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan


@define
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


@define
class Label:
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
    color: str
    default: bool


@define
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


@define
class PullRequest:
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None


@define
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


@define
class GetRepoIssuesResponse:
    data: List[Issue]


converter = Converter(omit_if_default=True)
converter.register_structure_hook(
    datetime,
    lambda v, tp: datetime.fromisoformat(v),
)
converter.register_unstructure_hook(
    datetime,
    datetime.isoformat,
)
converter.register_unstructure_hook(
    Reactions,
    make_dict_unstructure_fn(
        Reactions,
        converter,
        plus_one=override(rename="+1"),
        minus_one=override(rename="-1"),
    ),
)
converter.register_structure_hook(
    Reactions,
    make_dict_structure_fn(
        Reactions,
        converter,
        plus_one=override(rename="+1"),
        minus_one=override(rename="-1"),
    ),
)


def test_loading():
    assert (
        converter.structure(create_dumped_response(), GetRepoIssuesResponse)
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


def test_dumping():
    assert (
        converter.unstructure(create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser))
        ==
        create_dumped_response()
    )


def bench_loading(detailed_validation: bool):
    bench_converter = converter.copy(detailed_validation=detailed_validation)

    data = create_dumped_response()
    return benchmark_plan(bench_converter.structure, data, GetRepoIssuesResponse)


def bench_dumping(detailed_validation: bool):
    bench_converter = converter.copy(detailed_validation=detailed_validation)

    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(bench_converter.unstructure, data, GetRepoIssuesResponse)
