from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from marshmallow import Schema, fields, post_dump, post_load

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


class SimpleUserSchema(Schema):
    login = fields.Str()
    id = fields.Int()
    node_id = fields.Str()
    avatar_url = fields.Str()
    gravatar_id = fields.Str(allow_none=True)
    url = fields.Str()
    html_url = fields.Str()
    followers_url = fields.Str()
    following_url = fields.Str()
    gists_url = fields.Str()
    starred_url = fields.Str()
    subscriptions_url = fields.Str()
    organizations_url = fields.Str()
    repos_url = fields.Str()
    events_url = fields.Str()
    received_events_url = fields.Str()
    type = fields.Str()
    site_admin = fields.Boolean()
    name = fields.Str(allow_none=True, load_default=None)
    email = fields.Str(allow_none=True, load_default=None)
    starred_at = fields.DateTime(allow_none=True, load_default=None)

    @post_load
    def _to_model(self, data, **kwargs):
        return SimpleUser(**data)

    SKIP_NONE = ['name', 'email', 'starred_at']

    @post_dump(pass_many=False)
    def _skip_default(self, data, **kwargs):
        for key in self.SKIP_NONE:
            if data[key] is None:
                del data[key]
        return data


class LabelSchema(Schema):
    id = fields.Int()
    node_id = fields.Str()
    url = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    color = fields.Str()
    default = fields.Bool()

    @post_load
    def _to_model(self, data, **kwargs):
        return Label(**data)


class ReactionsSchema(Schema):
    url = fields.Str()
    total_count = fields.Int()
    plus_one = fields.Int(data_key='+1')
    minus_one = fields.Int(data_key='-1')
    laugh = fields.Int()
    confused = fields.Int()
    heart = fields.Int()
    hooray = fields.Int()
    eyes = fields.Int()
    rocket = fields.Int()

    @post_load
    def _to_model(self, data, **kwargs):
        return Reactions(**data)


class PullRequestSchema(Schema):
    diff_url = fields.Str(allow_none=True)
    html_url = fields.Str(allow_none=True)
    patch_url = fields.Str(allow_none=True)
    url = fields.Str(allow_none=True)
    merged_at = fields.DateTime(allow_none=True, load_default=None)

    @post_load
    def _to_model(self, data, **kwargs):
        return PullRequest(**data)

    SKIP_NONE = ['merged_at']

    @post_dump(pass_many=False)
    def _skip_none(self, data, **kwargs):
        for key in self.SKIP_NONE:
            if data[key] is None:
                del data[key]
        return data


class IssueSchema(Schema):
    id = fields.Int()
    node_id = fields.Str()
    url = fields.Str()
    repository_url = fields.Str()
    labels_url = fields.Str()
    comments_url = fields.Str()
    events_url = fields.Str()
    html_url = fields.Str()
    number = fields.Int()
    state = fields.Enum(IssueState, by_value=True)
    state_reason = fields.Enum(StateReason, by_value=True, allow_none=True)
    title = fields.Str()
    user = fields.Nested(SimpleUserSchema(), allow_none=True)
    labels = fields.List(fields.Nested(LabelSchema()))
    assignee = fields.Nested(SimpleUserSchema(), allow_none=True)
    assignees = fields.List(fields.Nested(SimpleUserSchema()), allow_none=True)
    locked = fields.Bool()
    active_lock_reason = fields.Str(allow_none=True)
    comments = fields.Int()
    closed_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    updated_at = fields.DateTime(allow_none=True)
    author_association = fields.Enum(AuthorAssociation, by_value=True)
    reactions = fields.Nested(ReactionsSchema(), allow_none=True, load_default=None)
    pull_request = fields.Nested(PullRequestSchema(), allow_none=True, load_default=None)
    body_html = fields.Str(allow_none=True)
    body_text = fields.Str(allow_none=True)
    timeline_url = fields.Str(allow_none=True, load_default=None)
    body = fields.Str(allow_none=True)

    @post_load
    def _to_model(self, data, **kwargs):
        return Issue(**data)

    SKIP_NONE = ['reactions', 'pull_request', 'body_html', 'body_text', 'timeline_url', 'body']

    @post_dump(pass_many=False)
    def _skip_none(self, data, **kwargs):
        for key in self.SKIP_NONE:
            if data[key] is None:
                del data[key]
        return data


class GetRepoIssuesResponseSchema(Schema):
    data = fields.List(fields.Nested(IssueSchema()))

    @post_load
    def post(self, data, **kwargs):
        return GetRepoIssuesResponse(**data)


def test_loading():
    assert (
        GetRepoIssuesResponseSchema().load(create_dumped_response())
        ==
        create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    )


def test_dumping():
    assert (
        GetRepoIssuesResponseSchema().dump(
            create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
        )
        ==
        create_dumped_response()
    )


def bench_loading():
    data = create_dumped_response()
    return benchmark_plan(GetRepoIssuesResponseSchema().load, data)


def bench_dumping():
    data = create_response(GetRepoIssuesResponse, Issue, Reactions, PullRequest, Label, SimpleUser)
    return benchmark_plan(GetRepoIssuesResponseSchema().dump, data)
