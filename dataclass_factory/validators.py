# field_parser -> validator(field_parser(pre_validator))
#
#
from dataclasses import dataclass
from typing import List, Optional

from .common import Parser, T


def combine_parser_validators(
    pre_validators: List[Parser],
    parser: Parser[T],
    post_validators: List[Parser[T]],
):
    if not post_validators and not pre_validators:
        return parser
    else:
        def pre_post_validating_parser(data):
            for v in pre_validators:
                data = v(data)
            data = parser(data)
            for v in post_validators:
                data = v(data)
            return data

        return pre_post_validating_parser


@dataclass
class ValidatorInfo:
    pre_parse: bool
    field: Optional[str]


def validate(*fields: Optional[str], pre: bool = False):
    """
    Decorator to set a method as a data validator.
    Such method will be called during data parsing.

    Validator method receives data which must be validated
    and returns corrected data or raises ValueError

    :param fields: names of fields (as they are in target class)
                   which are processed by this validator.
                   None is treated as "any single field"
    :param pre: flag to call validator before parsing corresponding value
    """
    def dec(func):
        try:
            vi = func.dataclass_factory_validate_info
        except AttributeError:
            func.dataclass_factory_validate_info = vi = []
        for fieldname in fields:
            vi.append(ValidatorInfo(field=fieldname, pre_parse=pre))
        return func

    if not fields:
        fields = (None, )
    return dec


def fill_validators(func, infos: List[ValidatorInfo], pre, post):
    for info in infos:
        if info.pre_parse:
            pre.setdefault(info.field, []).append(func)
        else:
            post.setdefault(info.field, []).append(func)


def prepare_validators(object):
    pre = {}
    post = {}

    for x in dir(object):
        atr = getattr(object, x)
        try:
            fill_validators(atr, atr.dataclass_factory_validate_info, pre, post)
        except AttributeError:
            pass
    return pre, post
