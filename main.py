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
import binascii
import sqlite3 as sql
from collections import Counter, defaultdict

import click

from ftb_format import *


def list_all_people(cursor):
    cursor.execute(QRY_ALL_PEOPLE, [])
    result = cursor.fetchall()
    for row in result:
        # id, gender, name, surname, suffix, alive, privacy = tuple(row)
        print(row)


def list_all_families(cursor):
    import re
    cursor.execute(QRY_FAMILY_LIST_VIEW, [])
    result = cursor.fetchall()
    all_values = defaultdict(int)

    for row in result:
        row = list(row)
        row[3] = individual_role_type[row[3]]
        row[7] = parse_date(row[7]) if row[7] else row[7]

        # all_values[binary[-1].encode('utf8')] += 1
        # if row[3] < len(family_main_data_status):
        #     row[3] = family_main_data_status[row[3]]
        print(row)           
    print(all_values)
    print(all_values.keys())


def list_person_families(cursor, person_id):
    cursor.execute(QRY_PERSON_FAMILIES, (person_id, person_id))
    result = cursor.fetchall()
    for row in result:
        row = list(row)
        print(row)


def get_person_data(cursor, person_id):
    cursor.execute(QRY_PERSON_DETAIL, (person_id,))
    row = cursor.fetchone()
    obj = row_to_object(row, {
        'id': 0,
        'gender': 1,
        'first_name': 2,
        'last_name': 3,
        'suffix': 4,
    })
    obj['date_of_birth'] = None
    obj['date_of_death'] = None
    return obj


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
        if role_is_child(row[1]):
            row.append('child')
        else:
            row.append('parent')
        row[1] = individual_role_type[row[1]]
        family_links.append(row)
    return family_links


def get_all_family_links(cursor):
    """Get family links for everyone in database."""
    cursor.execute(QRY_ALL_PERSON_IDS)
    result = cursor.fetchall()
    all_person_ids = [row[0] for row in result]
    family_links = {}
    # for person_id in all_person_ids:
    #     family_links[person_id] = get_person_family_links(cursor, person_id)
    family_links[20] = get_person_family_links(cursor, 20)
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


def list_person(cursor, person_id):
    cursor.execute(QRY_PERSON_DETAIL, (person_id,))
    print(cursor.fetchone())


def detail_person(cursor, person_id):
    print('Person')
    list_person(cursor, person_id)

    print('Person: facts')
    cursor.execute(QRY_PERSON_FACTS, (person_id,))
    result = cursor.fetchall()
    for row in result:
        print(row)

    print('Person: Family links')
    cursor.execute(QRY_FAMILY_LINKS, (person_id,))
    result = cursor.fetchall()
    family_ids = []
    for row in result:
        print(row)
        family_ids.append(row[1])

    print('Person: Family members')
    for family_id in family_ids:
        cursor.execute(QRY_FAMILY_MEMBERS, (family_id,))
        result = cursor.fetchall()
        print(family_id)
        for row in result:
            print(individual_role_type[row[2]], end=": ")
            fam_person_id = row[1]
            list_person(cursor, fam_person_id)


def query(cursor, query):
    cursor.execute(query, [])
    result = cursor.fetchall()
    for row in result:
        print(row)


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
    print('Persons:', people)
    print('Families:', families)

    with open('data/family_links.json', 'w') as outfile:
        json.dump(links, outfile)
    for person_id in people:
        person_data = get_person_data(cursor, person_id)
        # print(person_data)
        with open(f'data/people/{person_id}.json', 'w') as outfile:
            json.dump(person_data, outfile)
    # query(cursor, QRY_MEDIA)


if __name__ == '__main__':
    main()
