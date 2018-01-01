from sqlalchemy import create_engine, MetaData
from configparser import ConfigParser
import os

DEBUG = True
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CSRF_ENABLED = True
# TODO: Move to a config file
CSRF_SESSION_KEY = "TOP_SECRET"
SECRET_KEY = "ANOTHER_SECRET"
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
    },
    'discord': {
        'email': config.get('discord', 'email'),
        'pass': config.get('discord', 'pass'),
    },
}
engine = create_engine(
    'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
        user=conf['mysql']['user'],
        password=conf['mysql']['pass'],
        host=conf['mysql']['host'],
        port=conf['mysql']['port'],
        db=conf['mysql']['stats']['db'],
    )
)
STATS_DB_META = MetaData(bind=engine, reflect=True)
DISCORD_USER_TABLE = STATS_DB_META.tables['users']
STATS_GAMES_TABLE = STATS_DB_META.tables['games']
STATS_STATS_TABLE = STATS_DB_META.tables['statistics']
