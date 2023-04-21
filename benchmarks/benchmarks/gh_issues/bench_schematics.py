from enum import EnumMeta

from schematics.models import Model
from schematics.types import BaseType, BooleanType, DateTimeType, IntType, ListType, ModelType, StringType

from benchmarks.gh_issues.common import (
    AuthorAssociation,
    IssueState,
    StateReason,
    create_dumped_response,
    create_response,
)
from benchmarks.pybench.bench_api import benchmark_plan


class EnumValueType(BaseType):
    def __init__(self, enum_cls: EnumMeta, **kwargs):
        self.enum_cls = enum_cls
        super().__init__(**kwargs)

    def to_native(self, value, context=None):
        return self.enum_cls(value)

    def to_primitive(self, value, context=None):
        return value.value


class SimpleUser(Model):
    login = StringType(required=True)
    id = IntType(required=True)
    node_id = StringType(required=True)
    avatar_url = StringType(required=True)
    gravatar_id = StringType()
    url = StringType(required=True)
    html_url = StringType(required=True)
    followers_url = StringType(required=True)
    following_url = StringType(required=True)
    gists_url = StringType(required=True)
    starred_url = StringType(required=True)
    subscriptions_url = StringType(required=True)
    organizations_url = StringType(required=True)
    repos_url = StringType(required=True)
    events_url = StringType(required=True)
    received_events_url = StringType(required=True)
    type = StringType(required=True)
    site_admin = BooleanType(required=True)
    name = StringType(serialize_when_none=False)
    email = StringType(serialize_when_none=False)
    starred_at = DateTimeType(serialize_when_none=False, serialized_format='%Y-%m-%dT%H:%M:%S')


class Label(Model):
    id = IntType(required=True)
    node_id = StringType(required=True)
    url = StringType(required=True)
    name = StringType(required=True)
    description = StringType()
    color = StringType(required=True)
    default = BooleanType(required=True)


class Reactions(Model):
    url = StringType(required=True)
    total_count = IntType(required=True)
    plus_one = IntType(required=True, serialized_name='+1')
    minus_one = IntType(required=True, serialized_name='-1')
    laugh = IntType(required=True)
    confused = IntType(required=True)
    heart = IntType(required=True)
    hooray = IntType(required=True)
    eyes = IntType(required=True)
    rocket = IntType(required=True)


class PullRequest(Model):
    diff_url = StringType()
    html_url = StringType()
    patch_url = StringType()
    url = StringType()
    merged_at = DateTimeType(serialize_when_none=False, serialized_format='%Y-%m-%dT%H:%M:%S')


class Issue(Model):
    id = IntType(required=True)
    node_id = StringType(required=True)
    url = StringType(required=True)
    repository_url = StringType(required=True)
    labels_url = StringType(required=True)
    comments_url = StringType(required=True)
    events_url = StringType(required=True)
    html_url = StringType(required=True)
    number = IntType(required=True)
    state = EnumValueType(IssueState, required=True)
    state_reason = EnumValueType(StateReason, required=True)
    title = StringType(required=True)
    user = ModelType(SimpleUser)
    labels = ListType(ModelType(Label, required=True), required=True)
    assignee = ModelType(SimpleUser)
    assignees = ListType(ModelType(SimpleUser, required=True))
    locked = BooleanType(required=True)
    active_lock_reason = StringType()
    comments = IntType(required=True)
    closed_at = DateTimeType(serialized_format='%Y-%m-%dT%H:%M:%S')
    created_at = DateTimeType(serialized_format='%Y-%m-%dT%H:%M:%S')
    updated_at = DateTimeType(serialized_format='%Y-%m-%dT%H:%M:%S')
    author_association = EnumValueType(AuthorAssociation, required=True)
    reactions = ModelType(Reactions, serialize_when_none=False)
    pull_request = ModelType(PullRequest, serialize_when_none=False)
    body_html = StringType(serialize_when_none=False)
    body_text = StringType(serialize_when_none=False)
    timeline_url = StringType(serialize_when_none=False)
    body = StringType(serialize_when_none=False)


class GetRepoIssuesResponse(Model):
    data = ListType(ModelType(Issue, required=True), required=True)


def maker(model):
    def wrapper(**kwargs):
        return model(kwargs)

    return wrapper


def test_loading():
    assert (
        GetRepoIssuesResponse(create_dumped_response())
        ==
        create_response(
            maker(GetRepoIssuesResponse),
            maker(Issue),
            maker(Reactions),
            maker(PullRequest),
            maker(Label),
            maker(SimpleUser),
        )
    )


def test_dumping():
    assert (
        create_response(
            maker(GetRepoIssuesResponse),
            maker(Issue),
            maker(Reactions),
            maker(PullRequest),
            maker(Label),
            maker(SimpleUser),
        ).to_primitive()
        ==
        create_dumped_response()
    )


def bench_loading():
    data = create_dumped_response()
    return benchmark_plan(GetRepoIssuesResponse, data)


def bench_dumping():
    data = create_response(
        maker(GetRepoIssuesResponse),
        maker(Issue),
        maker(Reactions),
        maker(PullRequest),
        maker(Label),
        maker(SimpleUser),
    )
    return benchmark_plan(GetRepoIssuesResponse.to_primitive, data)
