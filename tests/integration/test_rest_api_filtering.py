import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypedDict, TypeVar, Union
from uuid import UUID

from adaptix import Chain, NameStyle, P, Retort, loader, name_mapping

# HTTP

BodyT = TypeVar("BodyT")
QueryT = TypeVar("QueryT")
PathT = TypeVar("PathT")


@dataclass
class _BaseHttpResponse(Generic[BodyT]):
    body: BodyT
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class HttpRawResponse(_BaseHttpResponse[str]):
    pass


@dataclass
class HttpResponse(_BaseHttpResponse[BodyT]):
    pass


@dataclass
class HttpRequestContext:
    account_id: str
    api_id: str
    identity: Dict[str, Any]
    path: str
    protocol: str
    request_id: str
    resource_id: str
    resource_path: str
    stage: str


@dataclass
class HttpRequest(Generic[BodyT, QueryT, PathT]):
    headers: Dict[str, str]
    http_method: str
    request_context: HttpRequestContext
    path: str
    resource: str

    body: BodyT
    path_parameters: PathT
    query_string_parameters: QueryT


## REST Base
NumberT = TypeVar("NumberT")


@dataclass
class MinMax(Generic[NumberT]):
    min_value: Optional[NumberT] = None
    max_value: Optional[NumberT] = None


MinMaxFloat = MinMax[float]
MinMaxInt = MinMax[int]
SimpleFilter = Union[None, List, MinMax, Dict[str, MinMaxFloat]]


@dataclass
class Order(Enum):
    asc = "asc"
    desc = "desc"


@dataclass
class PagingRequest:
    offset: int = 0
    limit: int = 20


## REST Concrete
class Stereochemistry(Enum):
    L = "L"
    D = "D"


class Contrast(Enum):
    BLANK = "BLANK"
    POSITIVE = "POSITIVE"
    COMPETITOR = "COMPETITOR"


class SortBy(Enum):
    number_aa = "number_aa"
    counts = "counts"
    id = "id"
    hit_id = "hit_id"
    hit_strength = "hit_strength"
    ic50_nm = "ic50_nm"
    phage_sample_group = "phage_sample_group"
    phage_library = "phage_library"
    cluster = "cluster"
    sequence = "sequence"

    total_aa = "total_aa"
    num_ali_hydro = "num_ali_hydro"
    num_aro_hydro = "num_aro_hydro"
    num_negative_charged = "num_negative_charged"
    num_arg_his = "num_arg_his"
    num_polar = "num_polar"
    active_from = "active_from"


@dataclass
class SortingParams:
    sort_by: SortBy = SortBy.active_from
    order: Order = Order.desc
    sort_key: Optional[str] = None


class SampleFilter(TypedDict, total=False):
    construct: List[UUID]
    stereochemistry: List[Stereochemistry]
    contrast: List[Contrast]
    protein_complex: List[UUID]
    concentration: Optional[MinMaxFloat]
    competitor: str
    screen: List[UUID]
    gene: List[UUID]


class FilterFields(TypedDict, total=False):
    id: Optional[List[UUID]]
    hit_id: Optional[List[str]]
    hit_strength: Optional[MinMaxFloat]
    ic50_nm: Optional[MinMaxFloat]
    phage_sample_group: Optional[List[UUID]]
    cluster: Optional[List[UUID]]
    sequence: Optional[List[str]]
    phage_library: Optional[List[UUID]]
    counts: Optional[Dict[UUID, MinMaxFloat]]
    samples: Optional[SampleFilter]
    sets: Optional[List[UUID]]
    total_aa: Optional[MinMaxInt]
    num_ali_hydro: Optional[MinMaxInt]
    num_aro_hydro: Optional[MinMaxInt]
    num_negative_charged: Optional[MinMaxInt]
    num_arg_his: Optional[MinMaxInt]
    num_polar: Optional[MinMaxInt]


@dataclass
class PhageHitsFilterRequest:
    filters: Optional[FilterFields] = None
    sort: SortingParams = SortingParams()
    pagination: PagingRequest = PagingRequest()


def process_json_body(data):
    if data is None:
        return None
    return json.loads(data)


def fix_empty_query(data):
    return data or {}


retort = Retort(
    recipe=[
        name_mapping(HttpRequest, name_style=NameStyle.CAMEL),
        name_mapping(HttpRequestContext, name_style=NameStyle.CAMEL),
        loader(P[HttpRequest].body, process_json_body, Chain.FIRST),
        loader(P[HttpRequest].query_string_parameters, fix_empty_query, Chain.FIRST),
    ]
)

INPUT_DATA = {
    "body": "{\"sort\": {\"sortBy\": \"id\"}, \"filters\": {\"samples\": {\"concentration\": {\"min_value\": 1.2}, \"competitor\": \"abc\"}, \"hit_strength\": {\"min_value\": 20.0, \"max_value\": 50.0}}}",
    "headers": {
        "Accept": "*/*",
        "Content-Length": "26",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "127.0.0.1:3000",
        "User-Agent": "curl/7.68.0",
        "X-Forwarded-Port": "3000",
        "X-Forwarded-Proto": "http"
    },
    "httpMethod": "POST",
    "isBase64Encoded": False,
    "multiValueHeaders": {
        "Accept": [
            "*/*"
        ],
        "Content-Length": [
            "26"
        ],
        "Content-Type": [
            "application/x-www-form-urlencoded"
        ],
        "Host": [
            "127.0.0.1:3000"
        ],
        "User-Agent": [
            "curl/7.68.0"
        ],
        "X-Forwarded-Port": [
            "3000"
        ],
        "X-Forwarded-Proto": [
            "http"
        ]
    },
    "multiValueQueryStringParameters": None,
    "path": "/phagehits",
    "pathParameters": None,
    "queryStringParameters": None,
    "requestContext": {
        "accountId": "123456789012",
        "apiId": "1234567890",
        "domainName": "127.0.0.1:3000",
        "extendedRequestId": None,
        "httpMethod": "POST",
        "identity": {
            "accountId": None,
            "apiKey": None,
            "caller": None,
            "cognitoAuthenticationProvider": None,
            "cognitoAuthenticationType": None,
            "cognitoIdentityPoolId": None,
            "sourceIp": "127.0.0.1",
            "user": None,
            "userAgent": "Custom User Agent String",
            "userArn": None
        },
        "path": "/phagehits",
        "protocol": "HTTP/1.1",
        "requestId": "fc030cd1-4463-405d-8c7c-27111faa2d97",
        "requestTime": "20/Jan/2022:12:33:29 +0000",
        "requestTimeEpoch": 1642682009,
        "resourceId": "123456",
        "resourcePath": "/filter",
        "stage": "Prod"
    },
    "resource": "/filter",
    "stageVariables": None,
    "version": "1.0"
}


def test_phage_hits_filter_request():
    result = retort.load(
        INPUT_DATA,
        HttpRequest[PhageHitsFilterRequest, Any, Any],
    )
    assert result == HttpRequest(
        headers={
            'Accept': '*/*',
            'Content-Length': '26',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': '127.0.0.1:3000',
            'User-Agent': 'curl/7.68.0',
            'X-Forwarded-Port': '3000',
            'X-Forwarded-Proto': 'http'
        },
        http_method='POST',
        request_context=HttpRequestContext(
            account_id='123456789012',
            api_id='1234567890',
            identity={
                'accountId': None,
                'apiKey': None,
                'caller': None,
                'cognitoAuthenticationProvider': None,
                'cognitoAuthenticationType': None,
                'cognitoIdentityPoolId': None,
                'sourceIp': '127.0.0.1',
                'user': None,
                'userAgent': 'Custom User Agent String',
                'userArn': None,
            },
            path='/phagehits',
            protocol='HTTP/1.1',
            request_id='fc030cd1-4463-405d-8c7c-27111faa2d97',
            resource_id='123456',
            resource_path='/filter',
            stage='Prod',
        ),
        path='/phagehits',
        resource='/filter',
        body=PhageHitsFilterRequest(
            filters={
                'hit_strength': MinMax(min_value=20.0, max_value=50.0),
                'samples': {
                    'competitor': 'abc',
                    'concentration': MinMax(min_value=1.2, max_value=None)
                },
            },
            sort=SortingParams(
                sort_by=SortBy.active_from,
                order=Order.desc,
                sort_key=None,
            ),
            pagination=PagingRequest(offset=0, limit=20)
        ),
        path_parameters=None,
        query_string_parameters={},
    )
