from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Any, Optional


def load_xml(filepath: str) -> ET.Element:
    tree = ET.parse(filepath)
    return tree.getroot()


ROLE_MAPPING = {
 'father': 'husband',
 'mother': 'wife',
 'childref': 'natural_child',
}


class GrampsXML:

    def __init__(self, root: ET.Element) -> None:
        self.root = root
        self.namespace = root.tag.split('}')[0][1:]

    def _ntag(self, val: ET.Element) -> str:
        """Get tag without namespace (no-namespace tag)."""
        return val.tag.replace(f"{{{self.namespace}}}", "")

    def _todict(self, el: ET.Element) -> Dict[str, Any]:
        """Convert values in children of element into dictionary."""
        el_dict: Dict[str, Any] = {}
        for child in el:
            assert not isinstance(child, str)
            # if child has children, then recurse
            if len(child) != 0:
                el_dict[self._ntag(child)] = self._todict(child)
                continue
            # if ntag(child).endswith("ref"):
            #     continue
            value = child.text
            if value is None:
                if 'val' in child.attrib:
                    value = child.attrib['val']
                elif 'value' in child.attrib:
                    value = child.attrib['value']
            
            if len(child.attrib) == 0:
                el_dict[self._ntag(child)] = value
            else:
                el_dict[self._ntag(child)] = child.attrib
                if value is not None:
                    # strings starting with period or hyphen aren't legal XML tag names
                    el_dict[self._ntag(child)]['.value'] = value
        el_dict.update(el.attrib)
        return el_dict
    
    def _person_surname(self, person: Dict[str, Any]) -> Optional[str]:
        full_surname = None
        surname = person['name'].get('surname')
        if isinstance(surname, str):
            full_surname = surname
        elif isinstance(surname, dict):
            full_surname = (surname.get('prefix', '') + ' ' + surname.get('.value', '')).strip()
        return full_surname

    def get_last_updated_date(self) -> datetime:
        date = self.root.findall('./{*}header/{*}created')[0].attrib['date']
        return datetime.fromisoformat(date)

    def _get_person_family_links(self, person_id: str) -> List[List[str]]:
        """Get person's family links."""
        person = self.root.find(f"./{{*}}people/{{*}}person[@id='{person_id}']")
        assert person is not None
        person_handle = person.attrib['handle']

        family_hlinks = []
        for el in person.findall(f"./{{*}}childof"):
            family_hlinks.append(("child", el.attrib['hlink']))
        for el in person.findall(f"./{{*}}parentin"):
            family_hlinks.append(("parent", el.attrib['hlink']))

        family_links = []
        for family_type, hlink in family_hlinks:
            family = self.root.find(f"./{{*}}families/{{*}}family[@handle='{hlink}']")
            assert family is not None
            result = family.find(f"./*[@hlink='{person_handle}']")
            assert result is not None
            role = ROLE_MAPPING[self._ntag(result)]
            family_links.append([family.attrib['id'], role, family_type])
        return family_links

    def get_all_family_links(self) -> Dict[str, List[Any]]:
        """Get family links for everyone in database."""
        people = self.root.findall('./{*}people/{*}person')
        all_person_ids = [self._todict(person)['id'] for person in people]
        family_links = {}
        for person_id in all_person_ids:
            family_links[person_id] = self._get_person_family_links(person_id)
        return family_links

    def get_person_data(self, person_id: str) -> Dict[str, Any]:
        """Fetch details for a single person."""
        person_el = self.root.find(f"./{{*}}people/{{*}}person[@id='{person_id}']")
        assert person_el is not None
        person = self._todict(person_el)
        events = person_el.findall("./{*}eventref")
        birth = {}
        death = {}
        for eventref in events:
            hlink = eventref.attrib['hlink']
            event_el = self.root.find(f"./{{*}}events/{{*}}event[@handle='{hlink}']")
            assert event_el is not None
            event = self._todict(event_el)
            event_date = ''
            if 'dateval' in event:
                event_date = event['dateval']['val']
            place = ''
            if 'place' in event:
                place_hlink = event['place']['hlink']
                place_el = self.root.find(f"./{{*}}places/{{*}}placeobj[@handle='{place_hlink}']")
                assert place_el is not None
                place = self._todict(place_el)['pname']
            if event['type'] == 'Birth':
                birth = {
                    'date': event_date,
                    'place': place,
                }
            elif event['type'] == 'Death':
                death = {
                    'date': event_date,
                    'place': place,
                }
        obj = {
            'personId': person_id,
            'gender': person['gender'],
            'firstName': person['name'].get('first', ''),
            'lastName': self._person_surname(person),
            'suffix': '',
            'facts': {
                'birth': birth,
                'death': death,
            }
        }
        return obj

    def get_family_data(self, family_id: str) -> Dict[str, Any]:
        family_el = self.root.find(f"./{{*}}families/{{*}}family[@id='{family_id}']")
        if family_el is None:
            return {}
        father_el = family_el.find("./{*}father")
        mother_el = family_el.find("./{*}mother")
        children_els = family_el.findall("./{*}childref")

        member_els: List[ET.Element] = []
        if father_el is not None:
            member_els.append(father_el)
        if mother_el is not None:
            member_els.append(mother_el)
        member_els.extend(children_els)

        family_members = []
        for member_el in member_els:
            hlink = self._todict(member_el)['hlink']
            person_el = self.root.find(f"./{{*}}people/{{*}}person[@handle='{hlink}']")
            if person_el is None:
                print(f"Missing person referenced by family: {hlink}")
                continue
            person = self._todict(person_el)

            family_members.append({
                'personId': person['id'],
                'roleType': ROLE_MAPPING[self._ntag(member_el)],
                'gender': person['gender'],
                'firstName': person['name'].get('first', ''),
                'lastName': self._person_surname(person),
            })
        return {
            'familyId': family_id,
            'type': None,
            'date': None,
            'members': family_members
        }

    def get_facts(self, person_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        facts: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for person_id in person_ids:
            person_el = self.root.find(f"./{{*}}people/{{*}}person[@id='{person_id}']")
            events = person_el.findall("./{*}eventref")
            for eventref in events:
                hlink = eventref.attrib['hlink']
                event_el = self.root.find(f"./{{*}}events/{{*}}event[@handle='{hlink}']")
                assert event_el is not None
                event = self._todict(event_el)

                event_date = ''
                if 'dateval' in event:
                    event_date = event['dateval']['val']
                place = ''

                if 'place' in event:
                    place_hlink = event['place']['hlink']
                    place_el = self.root.find(f"./{{*}}places/{{*}}placeobj[@handle='{place_hlink}']")
                    assert place_el is not None
                    place = self._todict(place_el)['pname'].get('value', '')

                obj = {
                    'factId': event['id'],
                    'type': event['type'].lower(),
                    'subType': '',
                    'date': event_date,
                    'description': event.get('description', ''),
                    'place': place,
                }
                facts[person_id].append(obj)
        return facts


if __name__ == "__main__":
    tree = ET.parse('data/family2.gramps')
    root = tree.getroot()
    xml = GrampsXML(root)

    namespace = root.tag.split('}')[0][1:]
    print(namespace)
    print(xml._ntag(root))

    for child in root:
        print(xml._ntag(child))

    print(xml.get_last_updated_date())
    print(xml.get_person_data("I0000"))

    print(xml.get_family_data("F0000"))

    xml.get_all_family_links()
    exit()
