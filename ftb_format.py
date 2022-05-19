import functools
from sqlite3 import Cursor
from datetime import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

from ftb_queries import *


FamilyLinks = Dict[int, List[Any]]


def choose_lang_longest(multi_lang_string: str) -> str:
    """Choose one string from a multi-lang string by preferring the longest string.
    
    Multi-lang strings are just under-score appended to one another."""
    if multi_lang_string is None:
        return ''
    multi = multi_lang_string.split('_')
    return functools.reduce(lambda a, b: a if len(a) >= len(b) else b, multi)


def choose_date_longest_valid(multi_fact_date: str) -> str:
    """Choose the longest valid valid from multiple facts.
    
    Multi-fact dates are just integers (YYYYMMDD) that are under-score appended to one another."""
    if multi_fact_date is None:
        return ''
    multi = multi_fact_date.split('_')
    # values longer than 8 are invalid (YYYYMMDD), e.g. 999999999 and -99999999
    return functools.reduce(lambda a, b: a if len(a) >= len(b) and len(a) <= 8 else b, multi)


def sorted_date_to_iso_8601(sorted_date: str) -> Optional[str]:
    """Sorted-date's are in YYYYMMDD and we return YYYY-MM-DD format.
    
    Optional parts of sorted_date will contain zeros."""
    if len(sorted_date) == 8:
        year, month, day = sorted_date[0:4], sorted_date[4:6], sorted_date[6:8]
        if month in ['00', '99']:
            return f'{year}'
        if day in ['00', '99']:
            return f'{year}-{month}'
        return f'{year}-{month}-{day}'
    return None


class FTBDB:
    
    def __init__(self, cursor: Cursor) -> None:
        self.cursor = cursor

    def get_person_data(self, person_id: int) -> Dict[str, Any]:
        """Fetch details for a single person."""
        self.cursor.execute(QRY_PERSON_DETAILS, (person_id,))
        row = self.cursor.fetchone()
        row = list(row)
        row[2] = choose_lang_longest(row[2])
        row[3] = choose_lang_longest(row[3])
        row[5] = sorted_date_to_iso_8601(choose_date_longest_valid(row[5]))
        row[6] = sorted_date_to_iso_8601(choose_date_longest_valid(row[6]))
        row[7] = choose_lang_longest(row[7])
        row[8] = choose_lang_longest(row[8])
        obj: Dict[str, Any] = row_to_object(row, {
            'personId': 0,
            'gender': 1,
            'firstName': 2,
            'lastName': 3,
            'suffix': 4,
        })
        obj['facts'] = {
            'birth': {
                'date': row[5],
                'place': row[7],
            },
            'death': {
                'date': row[6],
                'place': row[8],
            },
        }
        return obj


    def get_family_data(self, family_id: int) -> Dict[str, Any]:
        """Get data on family, including family members with enough detail for display."""
        self.cursor.execute(QRY_FAMILY_MEMBER_DETAILS, (family_id,))
        family_members = self.cursor.fetchall()
        family_members = [list(mem) for mem in family_members]
        for member in family_members:
            member[1] = individual_role_type[member[1]]
            member[2] = choose_lang_longest(member[2])
            member[3] = choose_lang_longest(member[3])
        for idx in range(len(family_members)):
            family_members[idx] = row_to_object(family_members[idx], {
                'personId': 0,
                'roleType': 1,
                'firstName': 2,
                'lastName': 3,
                'gender': 4
            })
        return {
            'familyId': family_id,
            'type': None,
            'date': None,
            'members': family_members
        }


    def _get_person_family_links(self, person_id: int) -> List[str]:
        """Get person's family links.

        Parameters
        ----------
        cursor
            Cursor to an open database connection.
        person_id
            Id of person whose family links should be retrieved.

        Returns
        -------
        A list of rows containing [family_id, role_in_family, family_type] where:
        - `role_in_family` is an `individual_role_type`
        - `family_type` is either 'parent' or 'child' depending on their role in the family
        """
        self.cursor.execute(QRY_PERSON_FAMILY_IDS, (person_id,))
        result = self.cursor.fetchall()
        family_links = []
        for row in result:
            row = list(row)
            row[1] = individual_role_type[row[1]]
            family_links.append(row)
        return family_links


    def get_all_family_links(self) -> FamilyLinks:
        """Get family links for everyone in database."""
        self.cursor.execute(QRY_ALL_PERSON_IDS)
        result = self.cursor.fetchall()
        all_person_ids = [row[0] for row in result]
        family_links = {}
        for person_id in all_person_ids:
            family_links[person_id] = self._get_person_family_links(person_id)
        return family_links


    def get_facts(self, person_ids: List[int]) -> Dict[str, List[Dict[str, Any]]]:
        self.cursor.execute(QRY_ALL_FACTS, [])
        result = self.cursor.fetchall()
        facts: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for row in result:
            if row[0] not in person_ids:
                continue
            row = list(row)
            if row[2] in fact_type:
                row[2] = fact_type[row[2]]
            row[4] = sorted_date_to_iso_8601(str(row[4]))
            # override description with cause_of_death
            if not row[4] and row[2] == 'DEAT':
                row[4] = row[7]
            row[5] = choose_lang_longest(row[5])
            row[6] = choose_lang_longest(row[6])
            obj = row_to_object(row, {
                # 'personId': 0,
                'factId': 1,
                'type': 2,
                'subType': 3,
                'date': 4,
                'description': 5,
                'place': 6
            })
            # lack of all this data is likely a mistaken entry?
            if [row[3], row[4], row[5]] == ['', None, '']:
                continue
            facts[row[0]].append(obj)
        return facts


    def get_last_updated_date(self) -> datetime:
        self.cursor.execute(QRY_LAST_UPDATED, [])
        last_updated_timestamp = self.cursor.fetchone()[0]
        return datetime.utcfromtimestamp(last_updated_timestamp)


    def _list_all_people(self) -> None:
        self.cursor.execute(EXP_QRY_ALL_PEOPLE, [])
        result = self.cursor.fetchall()
        for row in result:
            # id, gender, name, surname, suffix, alive, privacy = tuple(row)
            print(row)


    def _list_person(self, person_id: int) -> None:
        self.cursor.execute(EXP_QRY_PERSON_DETAIL, (person_id,))
        print(self.cursor.fetchone())


    def _detail_person(self, person_id: int) -> None:
        print('Person')
        self._list_person(person_id)

        print('Person: facts')
        self.cursor.execute(EXP_QRY_PERSON_FACTS, (person_id,))
        result = self.cursor.fetchall()
        for row in result:
            print(row)
