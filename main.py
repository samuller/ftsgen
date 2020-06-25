#!/usr/bin/env python3
#
# TODO:
# - privacy/living
#  - imd.is_alive
#  - imd.privacy_level (ifmd, ffmd, nmd)
#  - mimd.is_privatized

#

import sys
import pathlib
import os.path
import binascii
import sqlite3 as sql

import click

# 'foster_child'?
individual_role_type = ['unk', 'unk', 'husband', 'wife', 'unk', 'natural_child', 'adopted_child']
is_alive = ['unk', 'unk', 'no', 'yes']

QRY_PERSON_LIST_VIEW = """
SELECT
    imd.individual_id as id,
    imd.gender,
    ild.first_name,
    ild.last_name,
    ild.suffix,
    imd.is_alive,
    imd.privacy_level
FROM individual_main_data imd
JOIN individual_data_set ids
    ON ids.individual_id = imd.individual_id
JOIN individual_lang_data ild
    ON ild.individual_data_set_id = ids.individual_data_set_id
"""

QRY_ALL_PEOPLE = QRY_PERSON_LIST_VIEW + """
ORDER BY id
"""
QRY_PERSON_DETAIL = QRY_PERSON_LIST_VIEW + """
WHERE id = ?
"""
QRY_PERSON_FACTS = """
SELECT
    imd.individual_id as id,
    ifmd.token,
    ifmd.sorted_date,
    --ifmd.date,
    ifld.header,
    ifld.cause_of_death,
    pld.place,
    ifmd.privacy_level
FROM individual_main_data imd
LEFT JOIN individual_fact_main_data ifmd
    ON ifmd.individual_id = imd.individual_id
LEFT JOIN individual_fact_lang_data ifld
    ON ifld.individual_fact_id = ifmd.individual_fact_id
LEFT JOIN places_main_data pmd
    ON pmd.place_id = ifmd.place_id
LEFT JOIN places_lang_data pld
    ON pld.place_id = pmd.place_id
WHERE id = ?
"""

QRY_FAMILY_LINKS = """
SELECT DISTINCT
    fid.individual_id,
    fmd.family_id,
    ffmd.token,
    ffmd.sorted_date,
    -- ffmd.date,
    ffmd.place_id,
    pld.place,
    ffmd.privacy_level
FROM family_main_data fmd
LEFT JOIN family_fact_main_data ffmd
    ON ffmd.family_id = fmd.family_id
LEFT JOIN family_individual_connection fid
    ON fid.family_id = fmd.family_id
LEFT JOIN places_main_data pmd
    ON pmd.place_id = ffmd.place_id
LEFT JOIN places_lang_data pld
    ON pld.place_id = pmd.place_id
WHERE fid.individual_id = ?
"""

QRY_FAMILY_MEMBERS = """
SELECT
    fmd.family_id,
    fid.individual_id,
    fid.individual_role_type
FROM family_main_data fmd
LEFT JOIN family_individual_connection fid
    ON fid.family_id = fmd.family_id
WHERE fmd.family_id = ?
"""

QRY_MEDIA = """
SELECT
    mimd.media_item_id,
    mimd.item_type,
    mimd.file_size,
    mimd.file_crc,
    miai.width,
    miai.height,
    miai.extension,
    mild.title,
    pld.place
FROM media_item_main_data mimd
LEFT JOIN media_item_auxiliary_images miai
    ON miai.media_item_id = mimd.media_item_id
LEFT JOIN media_item_lang_data mild
    ON mild.media_item_id = mimd.media_item_id
LEFT JOIN places_main_data pmd
    ON mimd.place_id = pmd.place_id
LEFT JOIN places_lang_data pld
    ON pld.place_id = pmd.place_id
WHERE mimd.item_type = 1
"""

def list_all_people(cursor):
    cursor.execute(QRY_ALL_PEOPLE, [])
    result = cursor.fetchall()
    for row in result:
        id, gender, name, surname, suffix = tuple(row)
        print(id, gender, name, surname, suffix)


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


def crc32_from_file(filename, init=0):
    # Calculate CRC32 as int. For hex string use: "%08x" % buf
    buf = open(filename,'rb').read()
    buf = (binascii.crc32(buf, init) & 0xffff_ffff)
    return buf


def check_files(cursor, path):
    cursor.execute(QRY_MEDIA, [])
    result = cursor.fetchall()
    count_missing = 0
    count_errors = 0
    for row in result:
        id, ftype, size, crc, width, height, ext, title, place = row
        media_filename = 'P{}_{}_{}.{}'.format(id, width, height, ext)
        media_path = os.path.join(path, media_filename)

        if os.path.isfile(media_path):
            # check file size
            size = int(size)
            actual_size = os.path.getsize(media_path)
            if actual_size != size:
                count_errors += 1
                print('Wrong size: {} != {} ({})'.format(
                    actual_size, size, media_path))
            # check CRC
            actual_crc = crc32_from_file(media_path)
            actual_crc = ~actual_crc & 0xffff_ffff
            crc = int(crc)
            if actual_crc != crc:
                count_errors += 1
                print('Wrong CRC: {} != {} ({})'.format(
                    actual_crc, crc, media_path))
        else:
            count_missing += 1
    print('Errors: ' + str(count_errors))
    print('Missing: ' + str(count_missing))


def query(cursor, query):
    cursor.execute(query, [])
    result = cursor.fetchall()
    for row in result:
        print(row)


@click.command()
@click.argument('ftb_db_path', default=None, nargs=1, type=click.Path(exists=True, dir_okay=False))
@click.argument('media_path', default=None, nargs=-1, type=click.Path(exists=True, file_okay=False))
def main(ftb_db_path, media_path):
    sqlite_db_uri = pathlib.Path(ftb_db_path).as_uri()
    # Open database in read-only mode
    sqlite_db_uri = sqlite_db_uri + '?mode=ro'
    con = sql.connect(sqlite_db_uri, uri=True)
    cursor = con.cursor()
    con.row_factory = sql.Row

    # list_all_people(cursor)
    # detail_person(cursor, 16) # 16, 9510
    if media_path:
        check_files(cursor, media_path)
    # query(cursor, QRY_MEDIA)


if __name__ == '__main__':
    main()
