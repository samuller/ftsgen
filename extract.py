#!/usr/bin/env python3
#
# TODO:
# - privacy/living
#  - imd.is_alive
#  - imd.privacy_level (ifmd, ffmd, nmd)
#  - mimd.is_privatized

#

import os
import json
import pathlib
import os.path
import functools
import sqlite3 as sql
from datetime import datetime
from collections import defaultdict
from typing import Any, Dict, List, Set

import click

from ftb_format import *


family_json_div_size = 100
person_json_div_size = 1000
fact_json_div_size = 1000


def get_person_data(cursor, person_id):
    """Fetch details for a single person."""
    cursor.execute(QRY_PERSON_DETAILS, (person_id,))
    row = cursor.fetchone()
    row = list(row)
    row[2] = choose_lang_longest(row[2])
    row[3] = choose_lang_longest(row[3])
    row[5] = sorted_date_to_iso_8601(choose_date_longest_valid(row[5]))
    row[6] = sorted_date_to_iso_8601(choose_date_longest_valid(row[6]))
    row[7] = choose_lang_longest(row[7])
    row[8] = choose_lang_longest(row[8])
    obj = row_to_object(row, {
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


def choose_lang_longest(multi_lang_string):
    """Choose one string from a multi-lang string by preferring the longest string.
    
    Multi-lang strings are just under-score appended to one another."""
    if multi_lang_string is None:
        return ''
    multi = multi_lang_string.split('_')
    return functools.reduce(lambda a, b: a if len(a) >= len(b) else b, multi)


def choose_date_longest_valid(multi_fact_date):
    """Choose the longest valid valid from multiple facts.
    
    Multi-fact dates are just integers (YYYYMMDD) that are under-score appended to one another."""
    if multi_fact_date is None:
        return ''
    multi = multi_fact_date.split('_')
    # values longer than 8 are invalid (YYYYMMDD), e.g. 999999999 and -99999999
    return functools.reduce(lambda a, b: a if len(a) >= len(b) and len(a) <= 8 else b, multi)


def sorted_date_to_iso_8601(sorted_date):
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


def get_family_data(cursor, family_id):
    """Get data on family, including family members with enough detail for display."""
    cursor.execute(QRY_FAMILY_MEMBER_DETAILS, (family_id,))
    family_members = cursor.fetchall()
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


def get_person_family_links(cursor, person_id):
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
    cursor.execute(QRY_PERSON_FAMILY_IDS, (person_id,))
    result = cursor.fetchall()
    family_links = []
    for row in result:
        row = list(row)
        row[1] = individual_role_type[row[1]]
        family_links.append(row)
    return family_links


def get_all_family_links(cursor) -> Dict[int, List[Any]]:
    """Get family links for everyone in database."""
    cursor.execute(QRY_ALL_PERSON_IDS)
    result = cursor.fetchall()
    all_person_ids = [row[0] for row in result]
    family_links = {}
    for person_id in all_person_ids:
        family_links[person_id] = get_person_family_links(cursor, person_id)
    return family_links


def get_persons_in_family_links(family_links) -> List[int]:
    """Extract all person ids used in family links object."""
    return list(family_links.keys())


def get_families_in_family_links(family_links) -> Set[int]:
    """Extract all family ids used in family links object."""
    all_families = set()
    for _, families in family_links.items():
        for family in families:
            all_families.add(family[0])
    return all_families


def get_facts(cursor, person_ids):
    cursor.execute(QRY_ALL_FACTS, [])
    result = cursor.fetchall()
    facts = defaultdict(list)
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


def get_last_updated_date(cursor):
    cursor.execute(QRY_LAST_UPDATED, [])
    last_updated_timestamp = cursor.fetchone()[0]
    return datetime.utcfromtimestamp(last_updated_timestamp)


def list_all_people(cursor):
    cursor.execute(EXP_QRY_ALL_PEOPLE, [])
    result = cursor.fetchall()
    for row in result:
        # id, gender, name, surname, suffix, alive, privacy = tuple(row)
        print(row)


def list_person(cursor, person_id):
    cursor.execute(EXP_QRY_PERSON_DETAIL, (person_id,))
    print(cursor.fetchone())


def detail_person(cursor, person_id):
    print('Person')
    list_person(cursor, person_id)

    print('Person: facts')
    cursor.execute(EXP_QRY_PERSON_FACTS, (person_id,))
    result = cursor.fetchall()
    for row in result:
        print(row)


def split_dict_by_ids(data_dict, divs=1000):
    """A generator that splits a dictionary with ids as keys into separate smaller dicts.
    
    Parameters
    ----------
    data_dict
        A dictionary with integer ids as keys.
    divs
        Divisons, the maximum amount of ids to fit into a smaller dict.

    Yields
    ------
    A tuple containing the division range (e.g. [1000, 2000]) and the smaller dictionary.
    """
    # smaller dictionary in which some values were split
    mini_dict = {}
    # id ranges that smaller dict will contain (end value is non-inclusive)
    range = [0, divs]
    for id in sorted(data_dict.keys()):
        mini_dict[id] = data_dict[id]
        if int(id) >= range[1]-1:
            yield range, mini_dict
            mini_dict = {}
            range = [range[1], range[1] + divs]


def generate_split_json(filename_prefix, id_list, get_data_func, div_size, metadata=None):
    """Generate a dictionary with ids as keys which is then split and used to generate JSON files.
    
    Parameters
    ----------
    filename_prefix
        Folder path and filename prefix.
    id_list
        List of ids that will be used as dictionary keys.
    get_data_func
        A function to generate the actual data values to be stored.
    div_size
        The size of the rough number of the ids per JSON file
    """
    print(f'\nGenerating {filename_prefix}xxx.json for {len(id_list)} ids...')
    data_dict = {}
    for idx, idval  in enumerate(id_list):
        if idx % 100 == 0:
            print('*' if idx % 1000 == 0 else '.', end="", flush=True)
        data_dict[idval] = get_data_func(idval)
        # print(data_dict[idval])

    for rng, split_data_dict in split_dict_by_ids(data_dict, divs=div_size):
        rng_str = f"{rng[0]}-{rng[1]}"
        split_data_dict["metadata"] = metadata
        with open(f'{filename_prefix}{rng_str}.json', 'w') as outfile:
            json.dump(split_data_dict, outfile)
    
    return data_dict


def get_direct_antecedents(person_id, family_links: Dict[int, List], families: Dict[int, Set], depth=1):
    # get "birth" family
    parent_family_ids = [link[0] for link in family_links[person_id] if "child" in link[1]]
    if len(parent_family_ids) != 1:
        return set()
    # get parents of family
    parents = {(depth, pid) for pid, role in families[parent_family_ids[0]] if not "child" in role}

    # recurse to get further antecedents
    grand_parents = set()
    for parent in parents:
        grand_parents = grand_parents.union(get_direct_antecedents(parent[1], family_links, families, depth+1))

    antecedents = parents.union(grand_parents)
    return antecedents


def get_antecedents(focus_person_id, family_links) -> Dict[int, List[int]]:
    """Antecedents are predecessors in a family line (for which the focus person is a descendant)."""
    families = defaultdict(set)
    for pid, links in family_links.items():
        for link in links:
            families[link[0]].add((pid, link[1]))

    dd = get_direct_antecedents(focus_person_id, family_links, families)
    dd = sorted(list(dd), key=lambda val: val[0])

    antecedents = defaultdict(list)
    for desc in dd:
        antecedents[desc[1]].append(desc[0])
    return antecedents


def generate_json(cursor, source_file=None):
    last_updated = get_last_updated_date(cursor)
    metadata = {
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        # "source": source_file
        "source_updated_at": last_updated.isoformat(),
    }
    print("Metadata:", metadata)

    print("Extracting family-link data...")
    links = get_all_family_links(cursor)
    people_ids = get_persons_in_family_links(links)
    family_ids = get_families_in_family_links(links)
    # get direct antecedents for a specific person
    focus_person_id = 1
    antecedents = get_antecedents(focus_person_id, links)

    print(f'Saving data/antecedents_{focus_person_id}.json for {len(antecedents)} ids...')
    with open(f'data/antecedents_{focus_person_id}.json', 'w') as outfile:
        antecedents["metadata"] = metadata
        json.dump(antecedents, outfile)

    print(f'Saving data/family-links.json for {len(links)} ids...')
    with open('data/family-links.json', 'w') as outfile:
        links["metadata"] = metadata
        json.dump(links, outfile)

    people_data = generate_split_json('data/people/people-', people_ids,
        lambda person_id: get_person_data(cursor, person_id),
        person_json_div_size, metadata
    )

    person_search = []
    for person_id, person in people_data.items():
        person_title = f'{person["firstName"]} {person["lastName"]}'
        person_search.append([person_id, person_title])
    with open(f'data/person-search.json', 'w') as outfile:
        json.dump(person_search, outfile)

    family_data = generate_split_json('data/families/families-', family_ids,
        lambda family_id: get_family_data(cursor, family_id),
        family_json_div_size, metadata
    )

    facts = get_facts(cursor, people_ids)    
    facts_data = generate_split_json('data/facts/facts-', sorted(facts.keys()),
        lambda fact_id: facts[fact_id],
        fact_json_div_size, metadata
    )


@click.command()
@click.argument('ftb_db_path', default=None, nargs=1, type=click.Path(exists=True, dir_okay=False))
@click.argument('media_path', default=None, nargs=-1, type=click.Path(exists=True, file_okay=False))
def main(ftb_db_path, media_path):
    sqlite_db_uri = pathlib.Path(os.path.realpath(ftb_db_path)).as_uri()
    # Open database in read-only mode
    sqlite_db_uri = sqlite_db_uri + '?mode=ro'
    conn = sql.connect(sqlite_db_uri, uri=True)
    # Ignore unicode decoding errors
    conn.text_factory = lambda b: b.decode(errors = 'ignore')
    cursor = conn.cursor()
    conn.row_factory = sql.Row

    # list_all_people(cursor)
    # detail_person(cursor, 19) # 16, 9510
    # if media_path:
    #     media_check_files(cursor, media_path[0])

    # print(get_person_data(cursor, 19))
    generate_json(cursor, os.path.basename(ftb_db_path))


if __name__ == '__main__':
    main()
