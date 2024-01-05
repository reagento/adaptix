# source: https://openlibrary.org/dev/docs/api/search
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, NewType, Optional, Sequence
from zipfile import ZipFile

from dirty_equals import IsList, IsStr

from adaptix import P, Retort, name_mapping, validator

PositiveInt = NewType('PositiveInt', int)
PositiveFloat = NewType('PositiveFloat', float)


class EbookAccessLevel(Enum):
    NO_EBOOK = 'no_ebook'
    UNCLASSIFIED = 'unclassified'
    PRINT_DISABLED = 'printdisabled'
    BORROWABLE = 'borrowable'
    PUBLIC = 'public'


@dataclass
class OLDoc:
    version: int

    key: str
    type: str

    ebook_access: EbookAccessLevel
    extra_data: Dict[str, Any]

    redirects: List[str] = field(default_factory=list)
    has_fulltext: bool = False
    title: Optional[str] = None
    title_suggest: Optional[str] = None
    title_sort: Optional[str] = None
    edition_count: PositiveInt = 0
    edition_keys: List[str] = field(default_factory=list)
    cover_edition_key: Optional[str] = None
    publish_dates: List[str] = field(default_factory=list)
    publish_years: List[PositiveInt] = field(default_factory=list)
    first_publish_year: Optional[PositiveInt] = None
    languages: List[str] = field(default_factory=list)
    number_of_pages_median: Optional[PositiveInt] = None
    lccn_list: List[str] = field(default_factory=list)
    ia_list: List[str] = field(default_factory=list)
    ia_box_ids: List[str] = field(default_factory=list)
    ia_loaded_ids: List[str] = field(default_factory=list)
    ia_collection: List[str] = field(default_factory=list)
    oclc_list: List[str] = field(default_factory=list)
    isbn_list: List[str] = field(default_factory=list)

    # Classifications
    lcc_list: List[str] = field(default_factory=list)
    lcc_sort: Optional[str] = None
    ddc_list: List[str] = field(default_factory=list)
    ddc_sort: Optional[str] = None
    contributors: List[str] = field(default_factory=list)
    publish_places: List[str] = field(default_factory=list)
    publishers: List[str] = field(default_factory=list)
    publisher_facets: List[str] = field(default_factory=list)
    first_sentences: List[str] = field(default_factory=list)
    author_keys: List[str] = field(default_factory=list)
    author_names: List[str] = field(default_factory=list)
    author_alternative_names: List[str] = field(default_factory=list)
    author_facets: List[str] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)
    subject_facets: List[str] = field(default_factory=list)
    subject_keys: List[str] = field(default_factory=list)
    places: List[str] = field(default_factory=list)
    place_facets: List[str] = field(default_factory=list)
    place_keys: List[str] = field(default_factory=list)
    time_list: List[str] = field(default_factory=list)
    time_facets: List[str] = field(default_factory=list)
    time_keys: List[str] = field(default_factory=list)

    # Ratings
    ratings_average: Optional[PositiveFloat] = None
    ratings_sortable: Optional[PositiveFloat] = None
    ratings_count: Optional[PositiveInt] = None
    ratings_count_1: Optional[PositiveInt] = None
    ratings_count_2: Optional[PositiveInt] = None
    ratings_count_3: Optional[PositiveInt] = None
    ratings_count_4: Optional[PositiveInt] = None
    ratings_count_5: Optional[PositiveInt] = None

    # Reading Log
    reading_log_count: Optional[PositiveInt] = None
    want_to_read_count: Optional[PositiveInt] = None
    currently_reading_count: Optional[PositiveInt] = None
    already_read_count: Optional[PositiveInt] = None

    seeds: List[str] = field(default_factory=list)


@dataclass
class OLSearchResponse:
    start: int
    num_found: int
    docs: List[OLDoc]
    num_found_exact: bool
    query: str
    offset: Optional[int]


def create_plural_stripper(*, exclude: Sequence[str] = (), suffixes: Iterable[str] = ('s', '_list')):
    pattern = '^(.*)(' + '|'.join(suffixes) + ')$'

    def plural_stripper(shape, fld):
        return re.sub(pattern, lambda m: m[1], fld.id)

    return (
        P[pattern] & (~P[tuple(exclude)] if exclude else P.ANY),
        plural_stripper,
    )


retort = Retort(
    recipe=[
        name_mapping(
            OLSearchResponse,
            map={
                'query': 'q',
                'num_found_exact': 'numFoundExact',
            },
        ),
        name_mapping(
            OLDoc,
            map=[
                {
                    'reading_log_count': 'readinglog_count',
                    'version': '_version_',
                },
                create_plural_stripper(exclude=['redirects', 'ebook_access']),
            ],
            omit_default=~P['has_fulltext', 'edition_count'],
            extra_in='extra_data',
            extra_out='extra_data',
        ),
        validator(
            PositiveInt,
            lambda x: x >= 0,
        ),
        validator(
            PositiveFloat,
            lambda x: x >= 0,
        ),
    ],
)


def load_data():
    path = Path(__file__).parent / 'open_library_search.zip'
    with ZipFile(path).open('data.json') as f:
        return json.loads(f.read())


def test_load():
    data = load_data()
    data['docs'] = data['docs'][:1]
    loaded_response = retort.load(data, OLSearchResponse)
    assert loaded_response == OLSearchResponse(
        start=0,
        num_found=825,
        docs=[
            OLDoc(
                version=1780310972797288448,
                key='/works/OL27448W',
                type='work',
                ebook_access=EbookAccessLevel.BORROWABLE,
                extra_data={
                    'cover_i': 9255566,
                    'ebook_count_i': 16,
                    'ia_collection_s': IsStr,
                    'id_alibris_id': IsList(length=5),
                    'id_amazon': IsList(length=9),
                    'id_canadian_national_library_archive': ['20600075'],
                    'id_depósito_legal': IsList(length=4),
                    'id_goodreads': IsList(length=91),
                    'id_google': IsList(length=6),
                    'id_librarything': IsList(length=7),
                    'id_overdrive': [
                        '417C4314-2354-4092-96A7-DB3C12598E8A',
                        '2CCA69FD-FE09-4C2C-8C91-84D55F4AA425',
                    ],
                    'id_paperback_swap': [
                        '0618343997',
                        '0395974682',
                        '0618129022'
                    ],
                    'id_wikidata': [
                        'Q22122681',
                        'Q121942951'
                    ],
                    'last_modified_i': 1697836839,
                    'lending_edition_s': 'OL16355419M',
                    'lending_identifier_s': 'shinpanyubiwamon0005tolk',
                    'person': IsList(length=33),
                    'person_facet': IsList(length=33),
                    'person_key': IsList(length=33),
                    'printdisabled_s': IsStr,
                    'public_scan_b': False
                },
                redirects=[],
                has_fulltext=True,
                title='The Lord of the Rings',
                title_suggest='The Lord of the Rings',
                title_sort='The Lord of the Rings',
                edition_count=159,
                edition_keys=IsList(length=159),
                cover_edition_key='OL21058613M',
                publish_dates=IsList(length=99),
                publish_years=IsList(length=47),
                first_publish_year=1954,
                languages=IsList(length=14),
                number_of_pages_median=1193,
                lccn_list=IsList(length=15),
                ia_list=IsList(length=17),
                ia_box_ids=IsList(length=19),
                ia_loaded_ids=IsList(length=5),
                ia_collection=IsList(length=17),
                oclc_list=IsList(length=43),
                isbn_list=IsList(length=312),
                lcc_list=IsList(length=34),
                lcc_sort='PR-6039.00000000.O32 L617 1993',
                ddc_list=['823.91', '823.914', '823.912'],
                ddc_sort='823.914',
                contributors=IsList(length=11),
                publish_places=IsList(length=28),
                publishers=IsList(length=83),
                publisher_facets=IsList(length=83),
                first_sentences=IsList(length=1),
                author_keys=['OL26320A'],
                author_names=['J.R.R. Tolkien'],
                author_alternative_names=IsList(length=38),
                author_facets=['OL26320A J.R.R. Tolkien'],
                subjects=IsList(length=26),
                subject_facets=IsList(length=26),
                subject_keys=IsList(length=26),
                places=IsList(length=7),
                place_facets=IsList(length=7),
                place_keys=IsList(length=7),
                time_list=['The end of the third age'],
                time_facets=['The end of the third age'],
                time_keys=['the_end_of_the_third_age'],
                ratings_average=PositiveFloat(4.530303),
                ratings_sortable=PositiveFloat(4.2093663),
                ratings_count=PositiveInt(66),
                ratings_count_1=PositiveInt(2),
                ratings_count_2=PositiveInt(2),
                ratings_count_3=PositiveInt(6),
                ratings_count_4=PositiveInt(5),
                ratings_count_5=PositiveInt(51),
                reading_log_count=PositiveInt(1521),
                want_to_read_count=PositiveInt(1301),
                currently_reading_count=PositiveInt(101),
                already_read_count=PositiveInt(119),
                seeds=IsList(length=228),
            )
        ],
        num_found_exact=True,
        query='the lord of the rings',
        offset=None
    )


def test_load_and_dump_equality():
    data = load_data()
    loaded_response = retort.load(data, OLSearchResponse)
    dumped_response = retort.dump(loaded_response)

    data_to_compare = deepcopy(data)
    data_to_compare.pop('numFound')
    assert dumped_response == data_to_compare
