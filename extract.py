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
import sqlite3 as sql
from datetime import datetime
from typing import Dict, List, Set
from collections import defaultdict

import click

from ftb_format import *


family_json_div_size = 100
person_json_div_size = 1000
fact_json_div_size = 1000





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
        if int(id) >= range[1]:
            yield range, mini_dict
            mini_dict = {}
            range = [range[1], range[1] + divs]
        mini_dict[id] = data_dict[id]


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
        # print(rng_str, min(split_data_dict.keys()), max(split_data_dict.keys()))
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
    db = FTBDB(cursor)

    last_updated = db.get_last_updated_date()
    metadata = {
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        # "source": source_file
        "source_updated_at": last_updated.isoformat(),
    }
    print("Metadata:", metadata)

    print("Extracting family-link data...")
    links = db.get_all_family_links()
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
        lambda person_id: db.get_person_data(person_id),
        person_json_div_size, metadata
    )

    person_search = []
    for person_id, person in people_data.items():
        person_title = f'{person["firstName"]} {person["lastName"]}'
        person_search.append([person_id, person_title])
    with open(f'data/person-search.json', 'w') as outfile:
        json.dump(person_search, outfile)

    family_data = generate_split_json('data/families/families-', family_ids,
        lambda family_id: db.get_family_data(family_id),
        family_json_div_size, metadata
    )

    facts = db.get_facts(people_ids)    
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
