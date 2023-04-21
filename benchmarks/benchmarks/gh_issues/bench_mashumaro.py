from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

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
        omit_none = True


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

    SKIP_NONE = ['merged_at']

    def __post_serialize__(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        for key in self.SKIP_NONE:
            if data[key] is None:
                del data[key]
        return data


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

    SKIP_NONE = ['reactions', 'pull_request', 'body_html', 'body_text', 'timeline_url', 'body']

    def __post_serialize__(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        for key in self.SKIP_NONE:
            if data[key] is None:
                del data[key]
        return data


@dataclass
class GetRepoIssuesResponse(DataClassDictMixin):
    data: List[Issue]


def test_loading():
    assert (
        GetRepoIssuesResponse.from_dict(create_dumped_response())
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


def test_dumping():
    assert (
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser).to_dict()
        ==
        create_dumped_response()
    )


def bench_loading():
    data = create_dumped_response()
    return benchmark_plan(GetRepoIssuesResponse.from_dict, data)


def bench_dumping():
    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(GetRepoIssuesResponse.to_dict, data)
