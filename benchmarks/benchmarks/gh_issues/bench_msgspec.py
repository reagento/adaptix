from datetime import datetime
from functools import partial
from typing import List

import msgspec
import pytest

from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan

reactions_rename = {"plus_one": "+1", "minus_one": "-1"}


class SimpleUser(msgspec.Struct, omit_defaults=True):
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


class Label(msgspec.Struct):
    id: int
    node_id: str
    url: str
    name: str
    description: str | None
    color: str
    default: bool


class Reactions(msgspec.Struct, rename=reactions_rename):
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


class PullRequest(msgspec.Struct, omit_defaults=True):
    diff_url: str | None
    html_url: str | None
    patch_url: str | None
    url: str | None
    merged_at: datetime | None = None


class Issue(msgspec.Struct, omit_defaults=True):
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


class GetRepoIssuesResponse(msgspec.Struct):
    data: List[Issue]


class SimpleUserNoGC(msgspec.Struct, omit_defaults=True, gc=False):
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


class LabelNoGC(msgspec.Struct, gc=False):
    id: int
    node_id: str
    url: str
    name: str
    description: str | None
    color: str
    default: bool


class ReactionsNoGC(msgspec.Struct, rename=reactions_rename, gc=False):
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


class PullRequestNoGC(msgspec.Struct, omit_defaults=True, gc=False):
    diff_url: str | None
    html_url: str | None
    patch_url: str | None
    url: str | None
    merged_at: datetime | None = None


class IssueNoGC(msgspec.Struct, omit_defaults=True, gc=False):
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
    user: SimpleUserNoGC | None
    labels: List[LabelNoGC]
    assignee: SimpleUserNoGC | None
    assignees: List[SimpleUserNoGC] | None
    locked: bool
    active_lock_reason: str | None
    comments: int
    closed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    author_association: AuthorAssociation
    reactions: ReactionsNoGC | None = None
    pull_request: PullRequestNoGC | None = None
    body_html: str | None = None
    body_text: str | None = None
    timeline_url: str | None = None
    body: str | None = None


class GetRepoIssuesResponseNoGC(msgspec.Struct, gc=False):
    data: List[IssueNoGC]



@pytest.mark.parametrize("strict", [False, True])
def test_loading(strict):
    assert (
        msgspec.convert(create_dumped_response(), GetRepoIssuesResponse, strict=strict)
        ==
        create_response(
            GetRepoIssuesResponse,
            Issue,
            Reactions,
            PullRequest,
            Label,
            SimpleUser,
        )
    )
    assert (
        msgspec.convert(create_dumped_response(), GetRepoIssuesResponseNoGC, strict=strict)
        ==
        create_response(
            GetRepoIssuesResponseNoGC,
            IssueNoGC,
            ReactionsNoGC,
            PullRequestNoGC,
            LabelNoGC,
            SimpleUserNoGC,
        )
    )


def test_dumping():
    assert (
        msgspec.to_builtins(
            create_response(
                GetRepoIssuesResponse,
                Issue,
                Reactions,
                PullRequest,
                Label,
                SimpleUser,
            ),
        )
        ==
        create_dumped_response()
    )
    assert (
        msgspec.to_builtins(
            create_response(
                GetRepoIssuesResponseNoGC,
                IssueNoGC,
                ReactionsNoGC,
                PullRequestNoGC,
                LabelNoGC,
                SimpleUserNoGC,
            ),
        )
        ==
        create_dumped_response()
    )


def bench_loading(no_gc: bool, strict: bool):
    data = create_dumped_response()
    return benchmark_plan(
        partial(msgspec.convert, strict=strict),
        data,
        GetRepoIssuesResponseNoGC if no_gc else GetRepoIssuesResponse,
    )


def bench_dumping(no_gc: bool):
    if no_gc:
        data = create_response(
            GetRepoIssuesResponseNoGC,
            IssueNoGC,
            ReactionsNoGC,
            PullRequestNoGC,
            LabelNoGC,
            SimpleUserNoGC,
        )
    else:
        data = create_response(
            GetRepoIssuesResponse,
            Issue,
            Reactions,
            PullRequest,
            Label,
            SimpleUser,
        )
    return benchmark_plan(msgspec.to_builtins, data)


@pytest.mark.parametrize("no_gc", [False, True])
def test_dumping_benchmark_gc_configuration(no_gc):
    plan = bench_dumping(no_gc)
    response = plan.args[0]
    assert type(response).__struct_config__.gc is not no_gc
    assert all(type(issue).__struct_config__.gc is not no_gc for issue in response.data)
    assert plan.func(*plan.args) == create_dumped_response()
