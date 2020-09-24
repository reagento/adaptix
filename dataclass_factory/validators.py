# field_parser -> validator(field_parser(pre_validator))
#
#
from dataclasses import dataclass
from typing import Optional, List

from .common import Parser, T


def combine_parser_validators(
    pre_validator: Optional[Parser], parser: Parser[T], validator: Optional[Parser[T]]
):
    if validator is None and pre_validator is None:
        return parser
    elif validator is None:
        def pre_validating_parser(data) -> T:
            return parser(pre_validator(data))

        return pre_validating_parser
    elif pre_validator is None:
        def post_validating_parser(data) -> T:
            return validator(parser(data))

        return post_validating_parser
    else:
        def pre_post_validating_parser(data):
            return validator(parser(pre_validator(data)))

        return pre_post_validating_parser


@dataclass
class ValidatorInfo:
    pre_parse: bool
    field: Optional[str]


def validate(*fields: Optional[str], pre: bool = False):
    def dec(func):
        try:
            vi = func._dataclass_factory_validate_info
        except AttributeError:
            func._dataclass_factory_validate_info = vi = []
        for fieldname in fields:
            vi.append(ValidatorInfo(field=fieldname, pre_parse=pre))
        return func

    if not fields:
        fields = [None]
    return dec


def fill_validators(func, infos: List[ValidatorInfo], pre, post):
    for info in infos:
        if info.pre_parse:
            pre.setdefault(info.field, []).append(func)
        else:
            post.setdefault(info.field, []).append(func)


def prepare_validators(class_):
    pre = {}
    post = {}

    for x in dir(class_):
        atr = getattr(class_, x)
        try:
            fill_validators(atr, atr._dataclass_factory_validate_info, pre, post)
        except AttributeError:
            pass

    return pre, post
