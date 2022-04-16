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
from collections import defaultdict

import click

from ftb_format import *


def get_person_data(cursor, person_id):
    """Fetch details for a single person."""
    cursor.execute(QRY_PERSON_DETAILS, (person_id,))
    row = cursor.fetchone()
    row = list(row)
    row[2] = choose_lang_longest(row[2])
    row[3] = choose_lang_longest(row[3])
    row[5] = sorted_date_to_iso_8601(choose_date_longest_valid(row[5]))
    row[6] = sorted_date_to_iso_8601(choose_date_longest_valid(row[6]))
    obj = row_to_object(row, {
        'personId': 0,
        'gender': 1,
        'firstName': 2,
        'lastName': 3,
        'suffix': 4,
        'dateOfBirth': 5,
        'dateOfDeath': 6,
    })
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


def get_all_family_links(cursor):
    """Get family links for everyone in database."""
    cursor.execute(QRY_ALL_PERSON_IDS)
    result = cursor.fetchall()
    all_person_ids = [row[0] for row in result]
    family_links = {}
    for person_id in all_person_ids:
        family_links[person_id] = get_person_family_links(cursor, person_id)
    return family_links


def get_persons_in_family_links(family_links):
    """Extract all person ids used in family links object."""
    return list(family_links.keys())


def get_families_in_family_links(family_links):
    """Extract all family ids used in family links object."""
    all_families = []
    for _, families in family_links.items():
        for family in families:
            all_families.append(family[0])
    return all_families


def list_all_people(cursor):
    cursor.execute(_QRY_ALL_PEOPLE, [])
    result = cursor.fetchall()
    for row in result:
        # id, gender, name, surname, suffix, alive, privacy = tuple(row)
        print(row)


def list_person(cursor, person_id):
    cursor.execute(_QRY_PERSON_DETAIL, (person_id,))
    print(cursor.fetchone())


def detail_person(cursor, person_id):
    print('Person')
    list_person(cursor, person_id)

    print('Person: facts')
    cursor.execute(_QRY_PERSON_FACTS, (person_id,))
    result = cursor.fetchall()
    for row in result:
        print(row)

    print('Person: Family links')
    cursor.execute(_QRY_FAMILY_LINKS, (person_id,))
    result = cursor.fetchall()
    family_ids = []
    for row in result:
        print(row)
        family_ids.append(row[1])

    print('Person: Family members')
    for family_id in family_ids:
        cursor.execute(_QRY_FAMILY_MEMBERS, (family_id,))
        result = cursor.fetchall()
        print(f'Family {family_id} members:')
        for row in result:
            print(individual_role_type[row[2]], end=": ")
            fam_person_id = row[1]
            list_person(cursor, fam_person_id)


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

    links = get_all_family_links(cursor)
    people = get_persons_in_family_links(links)
    families = get_families_in_family_links(links)

    with open('data/family-links.json', 'w') as outfile:
        json.dump(links, outfile)
    print(f'Generating {len(people)} persons...')
    for idx, person_id in enumerate(people):
        if idx % 100 == 0:
            print('*' if idx % 1000 == 0 else '.', end="", flush=True)
        person_data = get_person_data(cursor, person_id)
        # print(person_data)
        with open(f'data/people/{person_id}.json', 'w') as outfile:
            json.dump(person_data, outfile)
    print(f'\nGenerating {len(families)} families...')
    for idx, family_id in enumerate(families):
        if idx % 100 == 0:
            print('*' if idx % 1000 == 0 else '.', end="", flush=True)
        family_data = get_family_data(cursor, family_id)
        # print(family_data)
        with open(f'data/families/{family_id}.json', 'w') as outfile:
            json.dump(family_data, outfile)



if __name__ == '__main__':
    main()
