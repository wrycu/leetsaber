from sqlalchemy import create_engine, MetaData, Table
from configparser import ConfigParser
from urllib.parse import quote_plus as url_quote
import os
from misc.t_dcs import ControlMapper
from misc.gdrive import GDrive

DEBUG = True
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CSRF_ENABLED = True
# TODO: Move to a config file
CSRF_SESSION_KEY = "TOP_SECRET"
SECRET_KEY = "ANOTHER_SECRET"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
config = ConfigParser()
config.read(os.path.join(BASE_DIR, os.pardir, 'config.ini'))
conf = {
    'mysql': {
        'user': config.get('mysql', 'user'),
        'pass': config.get('mysql', 'pass'),
        'host': config.get('mysql', 'host'),
        'port': config.get('mysql', 'port'),
        'stats': {
            'db': config.get('mysql', 'db'),
        },
        'armada': {
            'user': config.get('armada', 'user'),
            'pass': config.get('armada', 'pass'),
            'host': config.get('armada', 'host'),
            'port': config.get('armada', 'port'),
            'db': config.get('armada', 'db'),
        },
        'dcs': {
            'user': config.get('dcs', 'user'),
            'pass': config.get('dcs', 'pass'),
            'host': config.get('dcs', 'host'),
            'port': config.get('dcs', 'port'),
            'db': config.get('dcs', 'db'),
        },
    },
    'discord': {
        'email': config.get('discord', 'email'),
        'pass': config.get('discord', 'pass'),
    },
    'gdrive': {
        'access_token': config.get('google-drive', 'access_token'),
        'refresh_token': config.get('google-drive', 'refresh_token'),
        'client_id': config.get('google-drive', 'client_id'),
        'client_secret': config.get('google-drive', 'client_secret'),
    },
}
engine = create_engine(
    'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
        user=conf['mysql']['user'],
        password=url_quote(conf['mysql']['pass']),
        host=conf['mysql']['host'],
        port=conf['mysql']['port'],
        db=conf['mysql']['stats']['db'],
    )
)

STATS_DB_META = MetaData(bind=engine)
DISCORD_USER_TABLE = Table('users', STATS_DB_META, autoload_with=engine)
STATS_GAMES_TABLE = Table('games', STATS_DB_META, autoload_with=engine)
STATS_STATS_TABLE = Table('statistics', STATS_DB_META, autoload_with=engine)

#armada_engine = create_engine(
#    'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
#        user=conf['mysql']['armada']['user'],
#        password=conf['mysql']['armada']['pass'],
#        host=conf['mysql']['armada']['host'],
#        port=conf['mysql']['armada']['port'],
#        db=conf['mysql']['armada']['db'],
#    )
#)

dcs_engine = create_engine(
    'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
        user=conf['mysql']['dcs']['user'],
        password=url_quote(conf['mysql']['dcs']['pass']),
        host=conf['mysql']['dcs']['host'],
        port=conf['mysql']['dcs']['port'],
        db=conf['mysql']['dcs']['db'],
    )
)

DCS_DB_META = MetaData(bind=dcs_engine)
DCS_MISSION_TABLE = Table('missions', DCS_DB_META, autoload_with=dcs_engine)
DCS_MODULE_TABLE = Table('modules', DCS_DB_META, autoload_with=dcs_engine)
DCS_M_M_TABLE = Table('mission_module_count', DCS_DB_META, autoload_with=dcs_engine)


#ARMADA_DB_META = MetaData(bind=armada_engine, reflect=True)
#A_FLEET_TABLE = ARMADA_DB_META.tables['fleets']
#A_FLEET_MEMBERSHIP_TABLE = ARMADA_DB_META.tables['fleet_membership']
#A_GAME_MEMBERSHIP_TABLE = ARMADA_DB_META.tables['game_membership']
#A_GAME_TABLE = ARMADA_DB_META.tables['games']
#A_OBJECTIVE_TABLE = ARMADA_DB_META.tables['objectives']
#A_SHIP_TABLE = ARMADA_DB_META.tables['ships']
#A_SQUADRON_TABLE = ARMADA_DB_META.tables['squadrons']
#A_SYSTEM_TABLE = ARMADA_DB_META.tables['systems']
#A_TURN_TABLE = ARMADA_DB_META.tables['turn']
#A_TURN_LOG_TABLE = ARMADA_DB_META.tables['turn_log']
#A_UPGRADE_TABLE = ARMADA_DB_META.tables['upgrades']
#A_USER_TABLE = ARMADA_DB_META.tables['users']
CONTROL_MAPPER = ControlMapper()

GDRIVE = GDrive(
    conf['gdrive']['client_id'],
    conf['gdrive']['client_secret'],
    conf['gdrive']['refresh_token'],
    conf['gdrive']['access_token'],
)
