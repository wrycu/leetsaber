import json
from datetime import timedelta

from flask import Blueprint, render_template, Response, request
from sqlalchemy import select, and_, asc, desc, func
from sqlalchemy import text
import datetime

from app import config

stats = Blueprint(
    'stats',
    __name__,
)


@stats.route('/', methods=['GET'])
def landing():
    return render_template(
        'stats/overview.html',
        current_games={},
        stats=overview_data(),
    )


def overview_data():
    data = {
        'time': 0,
    }
    results = select([
        func.count(config.STATS_GAMES_TABLE.c.name),
    ]).execute().fetchone()
    data['games'] = results[0]

    results = select([
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).group_by(
        config.STATS_STATS_TABLE.c.gameId
    ).execute().fetchall()
    for result in results:
        if result.endTime:
            data['time'] += (result.endTime - result.startTime).seconds / 60 / 60  # hours
        else:
            data['time'] += (datetime.datetime.now() - result.startTime).seconds / 60 / 60
    data['time'] = int(data['time'])

    results = select([
        func.count(config.DISCORD_USER_TABLE.c.username),
    ]).execute().fetchone()
    data['users'] = results[0]

    results = select([
        config.DISCORD_USER_TABLE.c.username,
        config.STATS_STATS_TABLE.c.userId,
        func.count(func.distinct(config.STATS_STATS_TABLE.c.gameId)).label('count'),
    ]).select_from(
        config.STATS_STATS_TABLE.join(
            config.DISCORD_USER_TABLE,
            config.DISCORD_USER_TABLE.c.id == config.STATS_STATS_TABLE.c.userId
        )
    ).group_by(
        config.STATS_STATS_TABLE.c.userId
    ).order_by(
        desc(
            'count'
        )
    ).execute().fetchall()

    data['most_shared'] = results[0].username
    data['least_shared'] = results[-1].username
    data['shared'] = results

    return data
