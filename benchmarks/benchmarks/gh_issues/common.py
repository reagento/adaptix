import json
from datetime import datetime
from enum import Enum
from functools import partial
from pathlib import Path
from zipfile import ZipFile


class IssueState(str, Enum):
    OPEN = 'open'
    CLOSED = 'closed'


class StateReason(str, Enum):
    COMPLETED = 'completed'
    REOPENED = 'reopened'
    NOT_PLANNED = 'not_planned'


class AuthorAssociation(str, Enum):
    COLLABORATOR = 'COLLABORATOR'
    CONTRIBUTOR = 'CONTRIBUTOR'
    FIRST_TIMER = 'FIRST_TIMER'
    FIRST_TIME_CONTRIBUTOR = 'FIRST_TIME_CONTRIBUTOR'
    MANNEQUIN = 'MANNEQUIN'
    MEMBER = 'MEMBER'
    NONE = 'NONE'
    OWNER = 'OWNER'


def _load_dumped_issues() -> list:
    path = Path(__file__).parent / 'data.zip'
    with ZipFile(path).open('data.json') as f:
        return json.loads(f.read())


def create_dumped_response():  # noqa: CCR001
    dumped_issues = _load_dumped_issues()
    for issue in dumped_issues:
        issue.pop('milestone', None)
        issue.pop('performed_via_github_app', None)
        issue.pop('draft', None)

        if issue['closed_at'] is not None:
            issue['closed_at'] = issue['closed_at'][:-1]
        if issue['created_at'] is not None:
            issue['created_at'] = issue['created_at'][:-1]
        if issue['updated_at'] is not None:
            issue['updated_at'] = issue['updated_at'][:-1]
        if issue.get('pull_request') is not None:
            if issue['pull_request'].get('merged_at') is not None:
                issue['pull_request']['merged_at'] = issue['pull_request']['merged_at'][:-1]
            else:
                issue['pull_request'].pop('merged_at', None)

    return {'data': dumped_issues}


def parse_datetime(data):
    return datetime.fromisoformat(data[:-1])


def _get_processed(data, key, processor):
    result = data.get(key)
    if result is not None:
        return processor(result)
    return result


def _create_user(user_cls: type, data):
    return user_cls(
        login=data['login'],
        id=data['id'],
        node_id=data['node_id'],
        avatar_url=data['avatar_url'],
        gravatar_id=data['gravatar_id'],
        url=data['url'],
        html_url=data['html_url'],
        followers_url=data['followers_url'],
        following_url=data['following_url'],
        gists_url=data['gists_url'],
        starred_url=data['starred_url'],
        subscriptions_url=data['subscriptions_url'],
        organizations_url=data['organizations_url'],
        repos_url=data['repos_url'],
        events_url=data['events_url'],
        received_events_url=data['received_events_url'],
        type=data['type'],
        site_admin=data['site_admin'],
        name=data.get('name'),
        email=data.get('email'),
        starred_at=_get_processed(data, 'starred_at', datetime.fromisoformat),
    )


def _create_label(label_cls: type, data):
    return label_cls(
        id=data['id'],
        node_id=data['node_id'],
        url=data['url'],
        name=data['name'],
        description=data['description'],
        color=data['color'],
        default=data['default'],
    )


def _create_reactions(reactions_cls: type, data):
    return reactions_cls(
        url=data['url'],
        total_count=data['total_count'],
        plus_one=data['+1'],
        minus_one=data['-1'],
        laugh=data['laugh'],
        confused=data['confused'],
        heart=data['heart'],
        hooray=data['hooray'],
        eyes=data['eyes'],
        rocket=data['rocket'],
    )


def _create_pull_request(pull_request_cls: type, data):
    return pull_request_cls(
        diff_url=data['diff_url'],
        html_url=data['html_url'],
        patch_url=data['patch_url'],
        url=data['url'],
        merged_at=_get_processed(data, 'merged_at', parse_datetime),
    )


def create_response(
    response_cls: type,
    issue_cls: type,
    reactions_cls: type,
    pull_request_cls: type,
    label_cls: type,
    user_cls: type,
):
    dumped_issues = _load_dumped_issues()
    return response_cls(
        data=[
            issue_cls(
                id=data['id'],
                node_id=data['node_id'],
                url=data['url'],
                repository_url=data['repository_url'],
                labels_url=data['labels_url'],
                comments_url=data['comments_url'],
                events_url=data['events_url'],
                html_url=data['html_url'],
                number=data['number'],
                state=IssueState(data['state']),
                state_reason=_get_processed(data, 'state_reason', StateReason),
                title=data['title'],
                user=_get_processed(data, 'user', partial(_create_user, user_cls)),
                labels=[
                    _create_label(label_cls, el)
                    for el in data['labels']
                ],
                assignee=_get_processed(data, 'assignee', partial(_create_user, user_cls)),
                assignees=_get_processed(data, 'assignees', lambda lst: [_create_user(user_cls, el) for el in lst]),
                locked=data['locked'],
                active_lock_reason=data['active_lock_reason'],
                comments=data['comments'],
                reactions=_get_processed(data, 'reactions', partial(_create_reactions, reactions_cls)),
                pull_request=_get_processed(data, 'pull_request', partial(_create_pull_request, pull_request_cls)),
                closed_at=_get_processed(data, 'closed_at', parse_datetime),
                created_at=_get_processed(data, 'created_at', parse_datetime),
                updated_at=_get_processed(data, 'updated_at', parse_datetime),
                author_association=AuthorAssociation(data['author_association']),
                body_html=data.get('body_html'),
                body_text=data.get('body_text'),
                timeline_url=data.get('timeline_url'),
                body=data.get('body'),
            )
            for data in dumped_issues
        ],
    )
