"""
Constants, queries and parsing functions specific to the FTB file format.

"""
import os
import re
import binascii
from sqlite3 import Cursor
from typing import List, Dict, Any


# 'foster_child'?
individual_role_type = ['unk', 'unk', 'husband', 'wife', 'unk', 'natural_child', 'adopted_child']
is_alive = ['unk', 'unk', 'no', 'yes']
item_type = ['unk', 'individual', 'family', 'individual_fact', 'family_fact',
             'unk', 'unk', 'unk', 'media/image/citation?']
fact_type = {
    'BIRT': 'birth', 'DEAT': 'death', 'BURI': 'burial', 'OCCU': 'occupation',
    'RELI': 'religion', 'CHR': 'christening', 'DSCR': 'description',
    'EMIG': 'emigration', 'EVEN': 'event', 'GRAD': 'graduation',
    'PROP': 'proposal', 'RESI': 'residence', 'WILL': 'will',
    'CHRA': 'christening (adult)'
}
# Source: https://www.cisowscy.com/kopia-strony-sqlite
data_language = {
    0: 'English',
    1: 'Hebrew',
    2: 'French',
    3: 'German',
    4: 'Italian',
    5: 'Spanish',
    6: 'Portuguese-Portugal',
    7: 'Russian',
    8: 'Dutch',
    9: 'Greek',
    10: 'Turkish',
    11: 'Yiddish',
    12: 'Portuguese-Brazil',
    13: 'Bokmål-Norwegian',
    14: 'Danish',
    15: 'Lithuanian',
    16: 'Polish',
    17: 'Swedish',
    18: 'Ukrainian',
    19: 'Hungarian',
    20: 'Czech',
    21: 'Finnish',
    22: 'Afrikaans',
    23: 'Slovenian',
    24: 'Slovak',
    25: 'Albanian',
    26: 'Catalan',
    27: 'Bosnian',
    28: 'Estonian',
    29: 'Latvian ',
    30: 'Croatian',
    31: 'Romanian',
    32: 'Bulgarian',
    33: 'Serbian',
    34: 'Arabic',
    35: 'Indonesian',
    36: 'Persian',
    37: 'Chinese: simplified',
    38: 'Japanese',
    39: 'Korean',
    40: 'Chinese: traditional',
}

family_main_data_status = ['unk', 'engaged', 'divorced', 'married', 'separated', 'widowed', 'life_partners']
# guesses
family_token_types = { 'MARR': 'married', 'DIV': 'divorced', 'ANUL': 'annulled', 'EVEN': 'event' }


QRY_ALL_PERSON_IDS = """
SELECT
    imd.individual_id as id
    -- imd.privacy_level
FROM individual_main_data imd
"""

EXP_QRY_PERSON_LIST_VIEW = """
SELECT
    imd.individual_id as id,
    imd.gender,
    ild.first_name,
    ild.last_name,
    ild.suffix,
    imd.is_alive,
    imd.privacy_level
FROM individual_main_data imd
LEFT JOIN individual_data_set ids
    ON ids.individual_id = imd.individual_id
LEFT JOIN individual_lang_data ild
    ON ild.individual_data_set_id = ids.individual_data_set_id
"""

EXP_QRY_ALL_PEOPLE = EXP_QRY_PERSON_LIST_VIEW + """
ORDER BY id
"""
EXP_QRY_PERSON_DETAIL = EXP_QRY_PERSON_LIST_VIEW + """
WHERE id = ?
"""

EXP_QRY_PERSON_FACTS = """
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

QRY_PERSON_FAMILY_IDS = """
SELECT
    fic.family_id,
    fic.individual_role_type
    -- Fields of possible interest for filtering private data
    -- ffmd.date,
    -- ffmd.privacy_level
FROM family_individual_connection fic
-- LEFT JOIN family_main_data fmd
--     ON fmd.family_id = fic.family_id
-- LEFT JOIN family_fact_main_data ffmd
--     ON ffmd.family_id = fmd.family_id
WHERE fic.individual_id = ? AND fic.delete_flag = 0
ORDER BY fic.family_id
"""


QRY_PERSON_DETAILS = """
SELECT
    imd.individual_id as person_id,
    imd.gender,
    group_concat(ild.first_name, '_') as first_name,
    group_concat(ild.last_name, '_') as last_name,
    ild.suffix,
    --group_concat(ifmd.token, '_') as facts,
    group_concat(fact_birt.sorted_date, '_') as birth_date,
    group_concat(fact_deat.sorted_date, '_') as death_date,
    group_concat(place_birt.place, '_') as birth_place,
    group_concat(place_deat.place, '_') as death_place,
    imd.is_alive,
    imd.privacy_level
FROM individual_main_data imd
LEFT JOIN individual_data_set ids
    ON ids.individual_id = imd.individual_id
    AND ids.delete_flag = 0
LEFT JOIN individual_lang_data ild
    ON ild.individual_data_set_id = ids.individual_data_set_id
-- LEFT JOIN individual_fact_main_data ifmd
--     ON ifmd.individual_id = imd.individual_id
LEFT JOIN individual_fact_main_data fact_birt
    ON fact_birt.individual_id = imd.individual_id
    AND fact_birt.token = 'BIRT'
LEFT JOIN individual_fact_main_data fact_deat
    ON fact_deat.individual_id = imd.individual_id
    AND fact_deat.token = 'DEAT'
LEFT JOIN places_lang_data place_birt
    ON place_birt.place_id = fact_birt.place_id
LEFT JOIN places_lang_data place_deat
    ON place_deat.place_id = fact_deat.place_id
WHERE person_id = ? AND imd.delete_flag = 0
GROUP BY person_id
"""


# We return data in multiple languages appended together with underscores.
QRY_FAMILY_MEMBER_DETAILS = """
SELECT
    fic.individual_id as person_id,
    fic.individual_role_type as role_type,
    group_concat(ild.first_name, '_') as first_name,
    group_concat(ild.last_name, '_') as last_name,
    imd.gender
FROM family_main_data fmd
JOIN family_individual_connection fic
    ON fic.family_id = fmd.family_id
    AND fic.delete_flag = 0
LEFT JOIN individual_data_set ids
    ON ids.individual_id = fic.individual_id
    AND ids.delete_flag = 0
LEFT JOIN individual_lang_data ild
    ON ild.individual_data_set_id = ids.individual_data_set_id
LEFT JOIN individual_main_data imd
    ON imd.individual_id = fic.individual_id
    AND imd.delete_flag = 0
WHERE fmd.family_id = ? and fmd.delete_flag = 0
GROUP BY fic.individual_id
ORDER BY fic.individual_id
"""


QRY_ALL_PLACES = """
SELECT
    place_id,
    group_concat(pld.place, '_') as place
FROM places_lang_data pld
GROUP BY pld.place_id
"""


QRY_ALL_FACTS = """
SELECT DISTINCT
    ifmd.individual_id as person_id,
    ifmd.individual_fact_id as fact_id,
    ifmd.token,
    ifmd.fact_type,
    ifmd.sorted_date,
    group_concat(ifld.header, '_') as header,
    group_concat(place.place, '_') as place,
    ifld.cause_of_death
FROM individual_fact_main_data ifmd
LEFT JOIN individual_fact_lang_data ifld
    ON ifld.individual_fact_id = ifmd.individual_fact_id
LEFT JOIN places_lang_data place
    ON place.place_id = ifmd.place_id
WHERE ifmd.delete_flag = 0
GROUP BY fact_id
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

QRY_LAST_UPDATED = """select last_update from individual_main_data order by last_update desc limit 1"""


def row_to_object(row: List[str], mapping: Dict[str, int]) -> Dict[str, str]:
    object = {}
    for key, row_idx in mapping.items():
        object[key] = row[row_idx]
    return object


def role_is_child(role_type: int) -> bool:
    # We assume [4, 5, 6] = ['foster_child', 'natural_child', 'adopted_child']
    if role_type in [4, 5, 6]:
        return True
    return False


def parse_date(binary_date: str) -> str:
    date_format = {
        0: "empty",
        # '\n\x01': "unk",
        # '\n\x02': "unk",
        3: "YYY-only",
        4: "YYYY-only",
        # '\n\x05': "unk",
        # '\n\x06': "unk",
        7: "about/after YYY",
        8: "about/after YYYY",
        9: "fulldate (DD MMM YYY)",  # \t
        10: "fulldate 1 (DD MMM YYYY)",  # \n
        11: "fulldate 2 (DD MMM YYYY)",
        12: "about/after MM YYYY",
        13: "typo?",  # \r
        14: "before",
        15: "about DD MMM YYYY",
        18: "range (DD MMM YYYY - YYYY)",
        21: "free text 1",
        22: "free text 2",
        23: "free text 3",
        26: "free text - wrong field?",
        27: "free text - two dates?",
    }

    assert binary_date[0] == '\n'
    date_func_idx = ord(binary_date[1])
    date_func = None if date_func_idx not in date_format else date_format[date_func_idx]
    # "-" for valid and "/" for invalid value? (i.e. doesn't parse)
    match = re.search("\"[-/]", binary_date)
    assert match is not None
    find_datestr_end = match.start()
    datestr = binary_date[2:find_datestr_end]
    binary = binary_date[find_datestr_end:]  #.encode('utf8')

    # every second character is an increasing bit counter
    for idx, val in enumerate(binary):
        if idx / 2 > 15:
            # 16*8 = 128
            continue
        if idx % 2 == 0 and idx != 0 and ord(val) < 128:
            # print(idx, ord(val))
            assert ord(val) == 8*(idx/2), ord(val)

    assert binary[0] == '"', binary.encode('utf8')
    # parse_indicator = {'/': 'fail', '-': 'succeed'}[binary[1]]
    assert ord(binary[2]) == 8, binary.encode('utf8')
    assert ord(binary[3]) in [0, 1], binary.encode('utf8')
    assert ord(binary[4]) == 16, binary.encode('utf8')
    assert ord(binary[5]) in [0, 1, 2, 3], binary.encode('utf8')
    assert ord(binary[6]) == 24, binary.encode('utf8')
    assert ord(binary[7]) in [0, 1, 2], binary.encode('utf8')
    parse_status = ['invalid', None, 'valid'][ord(binary[7])]
    assert ord(binary[8]) == 32, binary.encode('utf8')  # ' '
    # parsed day of month: 0 -> unknown
    assert 0 <= ord(binary[9]) <= 31, binary.encode('utf8')
    # print(date_func_idx, ord(binary[9]), datestr)
    assert ord(binary[10]) == 40, binary.encode('utf8')  # '('
    # parsed month of year: 0 -> unknown
    # print(date_func, ord(binary[11]), datestr)
    assert 0 <= ord(binary[11]) <= 12, binary.encode('utf8')
    assert ord(binary[12]) == 48, binary.encode('utf8')  # '0'
    # year/century? 10.. = 7/8, 12.. = 9, 13.. = 10, 16.. = 12, 17.. = 15, 18.. = 14
    # assert ord(binary[13]) in [7, 8, 9, 10, 12, 13, 14, 15, 61], datestr.encode('utf8') + binary.encode('utf8')
    # assert 0 <= ord(binary[13]) <= 20, binary.encode('utf8')
    # Binary counter as string: (08@HPX=`hpx
    assert binary[14:35].encode('utf8') == b"8\x00@\x00H\x00P\x00X=`\x00h\x00p\x00x\x00\x01\x00\x01", binary[14:35].encode('utf8')
    assert ord(binary[35]) in [0, 1], binary.encode('utf8')
    assert ord(binary[36]) == 1, binary.encode('utf8')
    # print(binary[37:].encode('utf8'))
    # assert binary[37:].encode('utf8') in [
    #         b'\\', b'[',  b']',  b'N', b'O', b'P', b'Q', b'R', b'S', b'T', b'U', b'V', b'W',
    #         b'\xc9\x9c\\', b'\xd0\xb8P', b'\xde\xbeP', b'\xcc\xacQ', b'\xe2\xbd\x88Q',
    #         b'\xd6\x82R', b'\xdc\x9aR',
    #         b'\xc7\xadS', b'\xc4\x82S',
    #         b'\xd8\xa9T', b'\xd3\x82T',
    #         b'\xd4\x9bU', b'\xd4\xadU', b'\xcf\x95U',
    #         b'\xce\xa7W', b'\xd6\x9eW', b'\xd0\x83Z'
    #     ], binary[37:].encode('utf8')
    # 

    # assert 'I' <= binary[-1] <= '_' or ord(binary[-1]) == 3 or \
    #     '(' <= binary[-1] <= '<' or binary[-1] in ['$', '%', ':', ';', '>', '@', 'F'], binary.encode('utf8')

    # print(binary[37:].encode('utf8'))
    # assert binary[39] in ['U', 'V', 'R'] , binary.encode('utf8')

    # print(date_func_idx, ord(binary[9]), datestr)

    # if date_func is None:
    #     print(row[5][0:2].encode('utf8'), date[2:find_datestr_end])

    # print(date_func, datestr, len(datestr))
    # print(binary.encode('utf8'))
    # print(f"{datestr} => {(4+ord(binary[13]))*100:04}-{ord(binary[11]):02}-{ord(binary[9]):02}")
    return datestr


def media_crc32_from_file(filename: str, init:int = 0) -> int:
    # Calculate CRC32 as int. For hex string use: "%08x" % buf
    buf = open(filename,'rb').read()
    crc = (binascii.crc32(buf, init) & 0xffff_ffff)
    return crc


def media_check_files(cursor: Cursor, path: str) -> None:
    cursor.execute(QRY_MEDIA, [])
    result = cursor.fetchall()
    count_confirmed = 0
    count_missing = 0
    count_errors = 0
    for row in result:
        id, ftype, size, crc, width, height, ext, title, place = row
        media_filename = 'P{}_{}_{}.{}'.format(id, width, height, ext)
        media_path = os.path.join(path, media_filename)
        print(media_path)
        if os.path.isfile(media_path):
            # check file size
            size = int(size)
            actual_size = os.path.getsize(media_path)
            if actual_size != size:
                count_errors += 1
                print('Wrong size: {} != {} ({})'.format(
                    actual_size, size, media_path))
            # check CRC
            actual_crc = media_crc32_from_file(media_path)
            actual_crc = ~actual_crc & 0xffff_ffff
            crc = int(crc)
            if actual_crc != crc:
                count_errors += 1
                print('Wrong CRC: {} != {} ({})'.format(
                    actual_crc, crc, media_path))
            else:
                count_confirmed += 1
        else:
            count_missing += 1
    print('Confirmed: ' + str(count_confirmed))
    print('Errors: ' + str(count_errors))
    print('Missing: ' + str(count_missing))
