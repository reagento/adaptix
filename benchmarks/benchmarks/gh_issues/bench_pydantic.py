from datetime import datetime
from functools import partial
from typing import List, Optional

from pydantic import BaseModel, Field

from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan


class SimpleUser(BaseModel):
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


class Label(BaseModel):
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
    color: str
    default: bool


class Reactions(BaseModel):
    url: str
    total_count: int
    plus_one: int = Field(alias='+1')
    minus_one: int = Field(alias='-1')
    laugh: int
    confused: int
    heart: int
    hooray: int
    eyes: int
    rocket: int

    model_config = {
        'populate_by_name': True,
    }


class PullRequest(BaseModel):
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = Field(None, include=True)


class Issue(BaseModel):
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


class GetRepoIssuesResponse(BaseModel):
    data: List[Issue]


def test_loading():
    assert (
        GetRepoIssuesResponse.model_validate(create_dumped_response())
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


def test_dumping():
    assert (
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
        .model_dump(mode='json', by_alias=True, exclude_defaults=True)
        ==
        create_dumped_response()
    )


def bench_loading():
    data = create_dumped_response()
    return benchmark_plan(GetRepoIssuesResponse.model_validate, data)


def bench_dumping():
    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    dumper = GetRepoIssuesResponse.model_dump
    return benchmark_plan(partial(dumper, mode='json', by_alias=True), data)
