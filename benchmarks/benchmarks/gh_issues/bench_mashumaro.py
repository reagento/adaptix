from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig

from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan


@dataclass
class SimpleUser(DataClassDictMixin):
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

    class Config:
        omit_default = True


@dataclass
class Label(DataClassDictMixin):
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
    color: str
    default: bool


@dataclass
class Reactions(DataClassDictMixin):
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

    class Config(BaseConfig):
        aliases = {
            "plus_one": "+1",
            "minus_one": "-1",
        }
        serialize_by_alias = True


@dataclass
class PullRequest(DataClassDictMixin):
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None

    class Config(BaseConfig):
        omit_default = True


@dataclass
class Issue(DataClassDictMixin):
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

    class Config(BaseConfig):
        omit_default = True


@dataclass
class GetRepoIssuesResponse(DataClassDictMixin):
    data: List[Issue]


@dataclass
class SimpleUserLC(DataClassDictMixin):
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

    class Config:
        omit_default = True
        lazy_compilation = True


@dataclass
class LabelLC(DataClassDictMixin):
    id: int
    node_id: str
    url: str
    name: str
    description: Optional[str]
    color: str
    default: bool

    class Config:
        lazy_compilation = True


@dataclass
class ReactionsLC(DataClassDictMixin):
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

    class Config(BaseConfig):
        aliases = {
            "plus_one": "+1",
            "minus_one": "-1",
        }
        serialize_by_alias = True
        lazy_compilation = True


@dataclass
class PullRequestLC(DataClassDictMixin):
    diff_url: Optional[str]
    html_url: Optional[str]
    patch_url: Optional[str]
    url: Optional[str]
    merged_at: Optional[datetime] = None

    class Config:
        omit_default = True
        lazy_compilation = True


@dataclass
class IssueLC(DataClassDictMixin):
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
    user: Optional[SimpleUserLC]
    labels: List[LabelLC]
    assignee: Optional[SimpleUserLC]
    assignees: Optional[List[SimpleUserLC]]
    locked: bool
    active_lock_reason: Optional[str]
    comments: int
    closed_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    author_association: AuthorAssociation
    reactions: Optional[ReactionsLC] = None
    pull_request: Optional[PullRequestLC] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    timeline_url: Optional[str] = None
    body: Optional[str] = None

    class Config:
        omit_default = True
        lazy_compilation = True


@dataclass
class GetRepoIssuesResponseLC(DataClassDictMixin):
    data: List[IssueLC]

    class Config:
        lazy_compilation = True


def test_loading():
    assert (
        GetRepoIssuesResponse.from_dict(create_dumped_response())
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )
    assert (
        GetRepoIssuesResponseLC.from_dict(create_dumped_response())
        ==
        create_response(GetRepoIssuesResponseLC, IssueLC, ReactionsLC, PullRequestLC, LabelLC, SimpleUserLC)
    )


def test_dumping():
    assert (
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser).to_dict()
        ==
        create_dumped_response()
    )
    assert (
        create_response(GetRepoIssuesResponseLC, IssueLC, ReactionsLC, PullRequestLC, LabelLC, SimpleUserLC).to_dict()
        ==
        create_dumped_response()
    )


def bench_loading(lazy_compilation: bool):
    data = create_dumped_response()
    if lazy_compilation:
        GetRepoIssuesResponseLC.from_dict(data)
    loader = GetRepoIssuesResponseLC.from_dict if lazy_compilation else GetRepoIssuesResponse.from_dict
    return benchmark_plan(loader, data)


def bench_dumping(lazy_compilation: bool):
    if lazy_compilation:
        data = create_response(GetRepoIssuesResponseLC, IssueLC, ReactionsLC, PullRequestLC, LabelLC, SimpleUserLC)
        data.to_dict()
    else:
        data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(data.to_dict)
