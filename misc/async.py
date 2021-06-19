import configparser
from t_dcs import MissionParser
from gdrive import GDrive
from sqlalchemy import create_engine, MetaData, select, Table
import hashlib
import os


def download_missions(gdocs):
    """
    Given a google drive object, download missions in the provided folder
    :param gdocs:
    :return:
    """
    # 'ShackTac DCS/Missions' folder
    mission_folder_id = '1gstx6nmHFxXS10QWqEhyhnA84J72ay_I'
    return gdocs.download_zip(
        mission_folder_id
    ).content.decode('utf-8')


def mission_hash(mission_path):
    """
    Calculate the hex digest of a given file
    :param mission_path:
        path to mission file
    :return:
        STR of hex digest (MD5 for speed)
    """
    m = hashlib.md5()
    with open(mission_path, 'rb') as mission_file:
        m.update(mission_file.read())
    return m.hexdigest()


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
        'F-14': [
            'F-14B',
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
        'F-14B': 'F-14',
        'F-14A-135-GR': 'F-14',
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
        'A-10C_2': 'A-10C',
        'P-47D-30': 'P-47',
        'P-47D-40': 'P-47',
        'P-47D-30bl1': 'P-47',
        'I-16': 'I-16',
        'Mirage 2000-5': 'M-2000',
        'MQ9_PREDATOR': 'CA',
        # mod aircraft
        'A-4E-C': 'A-4E',
        'Hercules': 'C-130',
        'C-130FR': 'C-130',
        'AC_130': 'C-130',
        'F-22A': 'F-22',
    }
    if pretty_to_dcs:
        return pretty_dcs[unit]
    else:
        return dcs_pretty[unit]


def add_modules(mission_data, the_table):
    """
    For a given mission, add all of the modules to the DB
    :param mission_data:
    :param the_table:
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
            'mission_id': m_id,
            'module_id': existing_modules[aircraft],
            'module_count': count,
        })
    if data:
        the_table.insert(data).execute()


if __name__ == '__main__':
    """
    You may run this file directly to update the listing of missions
    (it was, in fact, intended to be run directly!)
    TODO: add parameters or something to make it not print as much to stdout
    """
    conf_obj = configparser.ConfigParser()
    conf_obj.read('../config.ini')
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

    mission_table = Table('missions', dcs_meta, autoload_with=engine)
    module_table = Table('modules', dcs_meta, autoload_with=engine)
    m_m_join_table = Table('mission_module_count', dcs_meta, autoload_with=engine)

    # select the existing missions so we can determine if each mission is new or not
    results = select([
        mission_table.c.name,
        mission_table.c.digest,
        mission_table.c.id,
    ]).execute().fetchall()
    # used to tell if a digest has changed for a given mission
    existing_missions = {x.name: x.digest for x in results}
    # used to determine the mission ID for a given digest
    existing_missions_ids = {x.digest: x.id for x in results}
    # select the supported modules
    results = select([
        module_table.c.id,
        module_table.c.name,
    ]).execute().fetchall()
    existing_modules = {x.name: x.id for x in results}

    parser = MissionParser()
    missions = parser.list_missions(conf['dcs']['mission_path'])
    for mission in missions:
        mission = str(mission)
        m_name = str(os.path.basename(mission))
        m_digest = mission_hash(mission)

        if m_name in existing_missions and existing_missions[m_name] == m_digest:
            # mission exists and is the same version
            print("skipped:", m_name, "due to same version already being parsed")
            continue
        # the mission is either new or is an updated version of an existing mission - parse basic attributes
        m_data = parser.parse_mission(mission)
        playable_factions = 0
        if m_data['factions']['blue']['slot_count'] > 0:
            playable_factions += 1
        if m_data['factions']['red']['slot_count'] > 0:
            playable_factions += 1
        if m_data['time'] == 'unknown':
            # we sometimes fail to parse the time, but we expect the time to be 5 characters reeee
            m_data['time'] = 'unkwn'

        if m_name in existing_missions and existing_missions[m_name] != m_digest:
            # mission exists but was updated (or some weird shit happened)
            print("updating:", m_name)
            # we don't know what changed, so just re-insert all data
            try:
                m_id = mission_table.update(
                    mission_table.c.id == existing_missions_ids[m_digest],
                    {
                        'name': m_name,
                        'map': m_data['map'],
                        'start_time': m_data['time'],
                        'playable_factions': playable_factions,
                        'format': m_data['format'],
                        'digest': m_digest,
                        'path': str(mission),
                    },
                ).execute()
            except KeyError:
                print("Something is up with {} / {} / {}".format(m_name, m_digest, str(mission)))
                continue

            # same as above - who knows what changed. delete the old information so we can re-add it
            m_m_join_table.delete().where(
                m_m_join_table.c.mission_id == existing_missions_ids[m_digest]
            ).execute()
        elif m_name not in existing_missions:
            # new mission! :)
            print("Inserting new mission:", m_name)

            m_id = mission_table.insert({
                'name': m_name,
                'map': m_data['map'],
                'start_time': m_data['time'],
                'playable_factions': playable_factions,
                'format': m_data['format'],
                'digest': m_digest,
                'path': str(mission),
            }).execute().inserted_primary_key[0]
            existing_missions[m_name] = m_digest
        add_modules(m_data, m_m_join_table)
