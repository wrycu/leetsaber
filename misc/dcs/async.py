import configparser
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine, MetaData, select, Table
import os
import requests
from bs4 import BeautifulSoup as bs
import io
import hashlib
import datetime


class MissionParser:
    def __init__(self, save_dir=None, last_download_id=None):
        pass

    def __loaddict__(self, fname, mizfile, reserved_files):
        reserved_files.append(fname)
        with mizfile.open(fname) as mfile:
            data = mfile.read()
            data = data.decode()
            import lua
            return lua.loads(data)

    def __load_assets__(self, file_contents):
        import zipfile
        with zipfile.ZipFile(file_contents) as miz:
            reserved_files = []
            try:
                mission_dict = self.__loaddict__('mission', miz, reserved_files)
            except SyntaxError:
                return {}
        return mission_dict

    def get_file_metadata(self, file_contents):
        # load assets
        try:
            mission_dict = self.__load_assets__(file_contents)
        except Exception:
            print(f"Bad mission: {file_contents}")
            return None

        if not mission_dict:
            print(f"Bad mission: {file_contents}")
            return None

        units = {}
        for col_name in ["blue", "red"]:
            if col_name in mission_dict['mission']["coalition"]:
                units[col_name] = {
                    'aircraft': {},
                    'slot_count': 0,
                }
                for x, country in mission_dict['mission']["coalition"][col_name]['country'].items():
                    for category_name, category_data in country.items():
                        if category_name not in ['helicopter', 'vehicle', 'plane']:
                            continue
                        for x, group in category_data['group'].items():
                            for x, unit in group['units'].items():
                                try:
                                    skill_level = unit['skill']
                                except KeyError:
                                    skill_level = 'Average'
                                if skill_level == 'Client':
                                    if unit['type'] not in units[col_name]['aircraft']:
                                        units[col_name]['aircraft'][unit['type']] = 0
                                    units[col_name]['aircraft'][unit['type']] += 1
                                    units[col_name]['slot_count'] += 1

        start_time_day = int(mission_dict['mission']["start_time"] % 86400)
        hour = int(start_time_day / 3600)
        minutes = int(start_time_day / 60) - hour * 60

        data = {
            'map': mission_dict['mission']['theatre'],
            'time': "{:02d}:{:02d}".format(hour, minutes),
            'format': mission_dict['mission']['version'],
            'factions': units,
        }

        return data

    def parse_mission(self, mission_name):
        raw_data = {
            'factions': {
                'blue': {
                    'slot_count': 0,
                    'aircraft': {},
                },
                'red': {
                    'slot_count': 0,
                    'aircraft': {},
                },
            },
            'map': 'unknown',
            'time': 'unknown',
            'format': 'unknown',
        }

        try:
            data = self.get_file_metadata(mission_name)
            if not data:
                return raw_data
        except UnicodeDecodeError:
            print(f"Unable to parse {mission_name}: unicode error")
            return raw_data
        return data


def get_unit(unit, pretty_to_dcs):
    """
    Given a unit, get the mapping
    pydcs calls units one thing, while the spread sheets we're parsing for module ownership call them another
    As such, we need to be able to pivot between the two
    :param unit:
    :param pretty_to_dcs:
    :return:
    """
    pretty_dcs = {
        'FC-3 or 4': [
            # "FC3" refers to many modules
            'A-10A',
            'F-15C',
            'J-11A',
            'MiG-29K',
            'MiG-29S',
            'MiG-29G',
            'MiG-29A',
            'Su-25',
            'Su-25T',
            'Su-27',
            'Su-33',
        ],
        'A-10C': [
            'A-10C',
        ],
        'A-10C_2': [
            'A-10C II',
        ],
        'AJS37': [
            'AJS37',
        ],
        'AV-8B': [
            'AV8BNA',
        ],
        'Bf-109': [
            'Bf-109K-4',
        ],
        'CE2': [
            'Christen Eagle II',
        ],
        'C-101': [
            'C-101CC',
            'C-101EB',
        ],
        'F-5': [
            'F-5E-3',
            'F-5E',
        ],
        'F-14B': [
            'F-14B',
        ],
        'F-14A': [
            'F-14A',
        ],
        'F-16': [
            'F-16C bl.52d',
        ],
        'F/A-18C': [
            'FA-18C_hornet',
        ],
        'F-86': [
            'F-86F Sabre',
        ],
        'FW-190': [
            'FW-190D9',
        ],
        'Gazelle': [
            'SA342M',
        ],
        'Huey': [
            'UH-1H',
        ],
        'Ka-50': [
            'Ka-50',
        ],
        'L-39': [
            'L-39ZA',
            'L-39C',
        ],
        'M-2000': [
            'M-2000C',
        ],
        'Mi-8': [
            'Mi-8MT',
        ],
        'MiG-15': [
            'MiG-15bis',
        ],
        'MiG-19': [
            'MiG-19P',
        ],
        'MiG-21': [
            'MiG-21Bis',
        ],
        'P-51': [
            'TF-51D',
            'P-51D-30-NA',
            'P-51D',
        ],
        'Spitfire': [
            'SpitfireLFMkIX',
        ],
        'Yak-52': [
            'Yak-52',
        ],
        'Hawk': [
            'Hawk',
        ],
        'JF-17': [
            'JF-17',
        ],
        'Mig-23': [
            'MiG-23MLD',
        ],
        'Mi-24P': [
            'Mi-24P',
        ],
        'AH-64D': [
            'AH-64D_BLK_II',
        ],
        'P-47': [
            'P-47D-30',
            'P-47D-40',
            'P-47D-30bl1',
        ],
        'Mosquito': [
            'MosquitoFBMkVI',
        ],
        'A-4E': [
            'A-4E-C',
        ],
        'C-130': [
            'Hercules',
            'C-130FR',
            'AC_130',
        ],
        'F-22': [
            'F-22A',
        ],
        'UH-60': [
            'UH-60L',
        ],
        'F-15E': [
            'F-15E',
        ],
    }
    dcs_pretty = {
        'A-10A': 'FC-3 or 4',  # all FC3 modules map to FC3
        'F-15C': 'FC-3 or 4',
        'J-11A': 'FC-3 or 4',
        'MiG-29K': 'FC-3 or 4',
        'MiG-29S': 'FC-3 or 4',
        'MiG-29G': 'FC-3 or 4',
        'MiG-29A': 'FC-3 or 4',
        'Su-25': 'FC-3 or 4',
        'Su-25T': 'FC-3 or 4',
        'Su-27': 'FC-3 or 4',
        'Su-33': 'FC-3 or 4',
        'A-10C': 'A-10C',
        'AJS37': 'AJS37',
        'AV8BNA': 'AV-8B',
        'Bf-109K-4': 'Bf-109',
        'CE2': 'Christen Eagle II',
        'Christen Eagle II': 'Christen Eagle II',
        'C-101CC': 'C-101',
        'C-101EB': 'C-101',
        'F-5E-3': 'F-5',
        'F-5E': 'F-5',
        'F-14B': 'F-14B',
        'F-14A-135-GR': 'F-14A',
        'F-16C bl.52d': 'F-16',
        'FA-18C_hornet': 'F/A-18C',
        'F/A-18C': 'F/A-18C',
        'F-86F Sabre': 'F-86',
        'FW-190D9': 'FW-190',
        'FW-190A8': 'FW-190',
        'SA342M': 'Gazelle',
        'SA342Minigun': 'Gazelle',
        'SA342Mistral': 'Gazelle',
        'SA342L': 'Gazelle',
        'UH-1H': 'Huey',
        'Ka-50': 'Ka-50',
        'L-39ZA': 'L-39',
        'L-39C': 'L-39',
        'M-2000C': 'M-2000',
        'Mi-8MT': 'Mi-8',
        'MiG-15bis': 'MiG-15',
        'MiG-19P': 'MiG-19',
        'MiG-21Bis': 'MiG-21',
        'TF-51D': 'P-51',
        'P-51D-30-NA': 'P-51',
        'P-51D': 'P-51',
        'SpitfireLFMkIX': 'Spitfire',
        'SpitfireLFMkIXCW': 'Spitfire',
        'Yak-52': 'Yak-52',
        'Hawk': 'Hawk',
        'T-45': 'Hawk',
        'JF-17': 'JF-17',
        'MiG-23MLD': 'Mig-23',
        'F-16C_50': 'F-16',
        'A-10C_2': 'A-10C II',
        'A-10C II': 'A-10C II',
        'P-47D-30': 'P-47',
        'P-47D-40': 'P-47',
        'P-47D-30bl1': 'P-47',
        'I-16': 'I-16',
        'Mirage 2000-5': 'M-2000',
        'MQ9_PREDATOR': 'CA',
        'Mi-24P': 'Mi-24P',
        'AH-64D_BLK_II': 'AH-64D',
        'MosquitoFBMkVI': 'Mosquito',
        # mod aircraft
        'A-4E-C': 'A-4E',
        'Hercules': 'C-130',
        'C-130FR': 'C-130',
        'AC_130': 'C-130',
        'F-22A': 'F-22',
        'UH-60L': 'UH-60',
        'F-15E': 'F-15E',
    }
    if pretty_to_dcs:
        return pretty_dcs[unit]
    else:
        return dcs_pretty[unit]


def download_mission(url):
    """
    Grab the mission contents (in memory)
    :param url:
        Download URL
    :return:
        Mission as contents
    """
    reply = requests.get(
        url,
    )
    return io.BytesIO(reply.content)


def get_mission_metadata(mission_id):
    """
    Lookup metadata about the mission on the ED website
    :param mission_id:
    :return:
    """
    # look up the details page
    reply = requests.get('https://www.digitalcombatsimulator.com/en/files/{}/'.format(mission_id))
    reply.raise_for_status()
    soup = bs(reply.text, 'html.parser')
    entries = bs.findAll(soup, attrs={'class': 'date'})

    # look up the download path
    url = bs.findAll(soup, attrs={'class': ['btn', 'download']}, string='Download')[0].attrs['href']
    name = url.split('/')[-1]
    # make a basic attempt at sanitization
    name = name.replace('...', '.')
    name = name.replace('..', '.')

    data = {
        'date': entries[0].text.split('-')[-1][1:].rstrip(' '),
        'id': mission_id,
        'download_path': 'https://www.digitalcombatsimulator.com/{}'.format(url),
        'name': name,
    }
    return data


def insert_or_update_mission(db_obj, known_modules, mission_data):
    # try to insert the mission
    try:
        m_id = db_obj['missions'].insert({
            'name': mission_data['name'],
            'map': mission_data['map'],
            'start_time': mission_data['start_time'],
            'playable_factions': mission_data['playable_factions'],
            'format': mission_data['format'],
            'digest': mission_data['digest'],
            'path': mission_data['path'],
            'ed_upload_date': datetime.datetime.strptime(mission_data['ed_upload_date'], '%m/%d/%Y %H:%M:%S'),
            'ed_id': mission_data['ed_id'],
        }).execute().inserted_primary_key[0]
    except IntegrityError:
        db_obj['missions'].update(
            db_obj['missions'].c.digest == mission_data['digest'],
            {
                'name': mission_data['name'],
                'map': mission_data['map'],
                'start_time': mission_data['start_time'],
                'playable_factions': mission_data['playable_factions'],
                'format': mission_data['format'],
                'digest': mission_data['digest'],
                'path': mission_data['path'],
                'ed_upload_date': datetime.datetime.strptime(mission_data['ed_upload_date'], '%m/%d/%Y %H:%M:%S'),
                'ed_id': mission_data['ed_id'],
            },
        ).execute()
        m_id = db_obj['missions'].select(
            db_obj['missions'].c.id
        ).where(
            db_obj['missions'].c.digest == mission_data['digest']
        ).execute().fetchone().id

    mission_data['id'] = m_id

    add_modules(db_obj, known_modules, mission_data)


def add_modules(db_obj, known_modules, mission_data):
    """
    For a given mission, add all of the modules to the DB
    :param module_table:
    :param mission_data:
    :return:
        N/A
    """
    module_list = {}
    data = []
    for faction in mission_data['factions'].values():
        for aircraft, a_data in faction['aircraft'].items():
            decoded_aircraft = get_unit(aircraft, False)
            if decoded_aircraft not in module_list:
                module_list[decoded_aircraft] = 0
            module_list[decoded_aircraft] += a_data

    for aircraft, count in module_list.items():
        data.append({
            'mission_id': mission_data['id'],
            'module_id': known_modules[aircraft],
            'module_count': count,
        })
    if data:
        db_obj['map'].insert(data).execute()


def mission_hash(mission_path):
    """
    Calculate the hex digest of a given file
    :param mission_path:
        path to mission file
    :return:
        STR of hex digest (MD5 for speed)
    """
    m = hashlib.md5()
    m.update(mission_path.getbuffer())
    return m.hexdigest()


def process_mission(db_obj, known_modules, mission_id):
    metadata = get_mission_metadata(mission_id)
    mission_contents = download_mission(metadata['download_path'])
    # TODO: re-implement digest check to avoid re-processing the same mission >1 time
    parser = MissionParser()
    parsed = parser.parse_mission(mission_contents)

    # massage the data into the DB format
    playable_factions = 0
    if parsed['factions']['blue']['slot_count'] > 0:
        playable_factions += 1
    if parsed['factions']['red']['slot_count'] > 0:
        playable_factions += 1
    if parsed['time'] == 'unknown':
        # we sometimes fail to parse the time, but we expect the time to be 5 characters reeee
        parsed['time'] = 'unkwn'

    digest = mission_hash(mission_contents)

    mission_data = {
        'ed_upload_date': metadata['date'],
        'ed_id': metadata['id'],
        'name': metadata['name'],
        'map': parsed['map'],
        'start_time': parsed['time'],
        'playable_factions': playable_factions,
        'format': parsed['format'],
        'digest': digest,
        'path': 'N/A - see ED site',
        'factions': parsed['factions'],
    }
    insert_or_update_mission(db_obj, known_modules, mission_data)


def find_missions(last_downloaded):
    """
    Given the last_downloaded ID, retrieve a list of IDs uploaded since
    :param last_downloaded:
        INT representing the ID of the mission last downloaded
    :return:
        A list of mission IDs to download
    """
    # get the number of pages
    reply = requests.get(
        'https://www.digitalcombatsimulator.com/en/files/filter/type-is-multiplayer/localization-is-english/sort-is-date_desc/apply/?PAGEN_1={}&PER_PAGE=100'.format(
            1,
        )
    )
    reply.raise_for_status()
    soup = bs(reply.text, 'html.parser')
    entries = bs.findAll(soup, attrs={'class': 'page-link'})[-2]
    num_pages = int(entries.text)
    page_size = 100
    detected_missions = []

    print("Found {} pages!".format(num_pages))

    for x in range(1, num_pages + 1):
        print("Now fetching missions from page {}".format(x))
        reply = requests.get(
            'https://www.digitalcombatsimulator.com/en/files/filter/type-is-multiplayer/localization-is-english/sort-is-date_desc/apply/?PAGEN_1={}&PER_PAGE={}'.format(
                x,
                page_size,
            )
        )
        reply.raise_for_status()
        new_missions, limit = extract_missions(reply.text, last_downloaded)
        detected_missions += new_missions
        if limit:
            break

    print("Found {} new missions!".format(len(detected_missions)))
    return detected_missions


def extract_missions(mission_list_page, last_downloaded):
    """
    Given a search page text object, return the mission IDs on the page if they're newer than the last downloaded mission
    :param mission_list_page:
        reply.text for a search for missions
    :param last_downloaded:
        ID of the mission last successfully downloaded
    :return:
    """
    missions = []
    soup = bs(mission_list_page, 'html.parser')
    entries = bs.findAll(soup, attrs={'class': 'download'})
    hit_limit = False
    for entry in entries:
        m_id = int(entry.attrs['data-id'])
        if m_id > last_downloaded:
            missions.append(m_id)
        else:
            hit_limit = True
            break
    return missions, hit_limit


def get_db_obj():
    conf_obj = configparser.ConfigParser()
    conf_obj.read('../../config.ini')
    conf = {
        'dcs': {
            'mission_path': conf_obj.get('dcs', 'mission_path'),
            'user': conf_obj.get('dcs', 'user'),
            'pass': conf_obj.get('dcs', 'pass'),
            'host': conf_obj.get('dcs', 'host'),
            'port': conf_obj.get('dcs', 'port'),
            'db': 'dcs',
        },
    }

    engine = create_engine(
        'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
            user=conf['dcs']['user'],
            password=conf['dcs']['pass'],
            host=conf['dcs']['host'],
            port=conf['dcs']['port'],
            db=conf['dcs']['db'],
        )
    )

    dcs_meta = MetaData(bind=engine)

    return {
        'missions': Table('missions', dcs_meta, autoload_with=engine),
        'modules': Table('modules', dcs_meta, autoload_with=engine),
        'map': Table('mission_module_count', dcs_meta, autoload_with=engine),
    }


def save_last_downloaded(last_downloaded_id):
    config_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir, os.pardir, 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_dir)

    config.set('dcs', 'last_downloaded', str(last_downloaded_id))
    with open(config_dir, 'w') as f:
        config.write(f)


def get_last_downloaded():
    config_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir, os.pardir, 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_dir)

    return int(config.get('dcs', 'last_downloaded'))


if __name__ == '__main__':
    # pull the DB object
    db_obj = get_db_obj()
    # read the modules once and pass them around

    results = select([
        db_obj['modules'].c.id,
        db_obj['modules'].c.name,
    ]).execute().fetchall()
    existing_modules = {x.name: x.id for x in results}

    # figure out which mission we last downloaded
    last_mission = get_last_downloaded()

    # process missions
    missions = sorted(find_missions(last_mission), reverse=True)
    for mission in missions:
        process_mission(db_obj, existing_modules, mission)

    if missions:
        save_last_downloaded(missions[-1])
