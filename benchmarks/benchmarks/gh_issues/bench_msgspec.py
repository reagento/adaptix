from datetime import datetime
from functools import partial
from typing import List, Optional

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


class Label(msgspec.Struct):
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
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
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None


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


class GetRepoIssuesResponse(msgspec.Struct):
    data: List[Issue]


class SimpleUserNoGC(msgspec.Struct, omit_defaults=True, gc=False):
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


class LabelNoGC(msgspec.Struct, gc=False):
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
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
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None


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
    state_reason: Optional[StateReason]
    title: str
    user: Optional[SimpleUserNoGC]
    labels: List[LabelNoGC]
    assignee: Optional[SimpleUserNoGC]
    assignees: Optional[List[SimpleUserNoGC]]
    locked: bool
    active_lock_reason: Optional[str]
    comments: int
    closed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    author_association: AuthorAssociation
    reactions: Optional[ReactionsNoGC] = None
    pull_request: Optional[PullRequestNoGC] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    timeline_url: Optional[str] = None
    body: Optional[str] = None


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
            GetRepoIssuesResponse,
            Issue,
            Reactions,
            PullRequest,
            Label,
            SimpleUser,
        )
    else:
        data = create_response(
            GetRepoIssuesResponseNoGC,
            IssueNoGC,
            ReactionsNoGC,
            PullRequestNoGC,
            LabelNoGC,
            SimpleUserNoGC,
        )
    return benchmark_plan(msgspec.to_builtins, data)
