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

user_blacklist = [

]


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
    # begin overview data
    results = select([
        func.count(config.STATS_GAMES_TABLE.c.name),
    ]).execute().fetchone()
    data['games'] = results[0]

    results = select([
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).execute().fetchall()
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
    # end overview data

    results = select([
        config.DISCORD_USER_TABLE.c.username,
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
    data['game_overview'] = game_stats(0).json
    data['game_heatmap'] = game_heatmap(0).json
    data['user_overview'] = user_stats(0).json
    data['user_heatmap'] = user_heatmap(0).json
    data['game_count'] = game_user_count().json

    return data


@stats.route('/top_games_by_play_time', methods=['GET'])
def top_games_by_play_time():
    results = select([
        config.STATS_GAMES_TABLE.c.name,
        func.sum(
            func.timestampdiff(
                text('SECOND'),
                config.STATS_STATS_TABLE.c.startTime,
                config.STATS_STATS_TABLE.c.endTime
            )
        ).label('time_played')
    ]).select_from(
        config.STATS_STATS_TABLE.join(
            config.STATS_GAMES_TABLE,
            config.STATS_GAMES_TABLE.c.id == config.STATS_STATS_TABLE.c.gameId,
        )
    ).where(
        and_(
            config.STATS_STATS_TABLE.c.endTime != None,
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).group_by(
        config.STATS_GAMES_TABLE.c.id,
    ).order_by(
        desc(
            'time_played'
        )
    ).limit(
        5
    ).execute().fetchall()

    top_games = []
    for game in results:
        top_games.append({'name': game.name, 'data': [float(game.time_played / 60 / 60)]})
    return Response(json.dumps(top_games), mimetype='application/json')


@stats.route('/top_games_by_user_count', methods=['GET'])
def top_games_by_user_count():
    g_stats = {}
    game_mapping = {}
    results = select([
        config.STATS_STATS_TABLE.c.gameId,
        config.STATS_STATS_TABLE.c.userId,
        config.STATS_GAMES_TABLE.c.name,
    ]).select_from(
        config.STATS_STATS_TABLE.join(
            config.STATS_GAMES_TABLE,
            config.STATS_GAMES_TABLE.c.id == config.STATS_STATS_TABLE.c.gameId
        )
    ).where(
        and_(
            config.STATS_STATS_TABLE.c.endTime != None,
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()
    for result in results:
        if result['gameId'] not in g_stats:
            game_mapping[result['gameId']] = result['name']
            g_stats[result['gameId']] = []
        if result['userId'] not in g_stats[result['gameId']]:
            g_stats[result['gameId']].append(result['userId'])
    raw_top_games = sorted(g_stats, key=lambda k: len(g_stats[k]), reverse=True)[:5]

    top_games = []
    for game in raw_top_games:
        top_games.append({'name': game_mapping[game], 'data': [len(g_stats[game])]})
    return Response(json.dumps(top_games), mimetype='application/json')


@stats.route('/top_active_time_of_day', methods=['GET'])
def top_active_time_of_day():
    results = select([
        config.STATS_STATS_TABLE.c.userId,
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).where(
        and_(
            config.STATS_STATS_TABLE.c.endTime != None,
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()

    # HourEachDay -> [userId]
    hour_map = {}
    for result in results:
        current_time = result['startTime'].replace(minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(minute=0, second=0, microsecond=0)

        # loop from start time to end time so we get a data point for each hour someone played a game
        while current_time <= end_time:
            if hour_map.get(current_time) is None:
                hour_map[current_time] = []
            # We don't want to count the same user in the same hour so make
            # sure they haven't already been accounted for in our map
            if result['userId'] not in hour_map[current_time]:
                hour_map[current_time].append(result['userId'])

            current_time += timedelta(hours=1)

    # We want to capture the number of people/hour AND the number of samples so that we
    # can compute the average number of players for that hour
    # Hour -> (# People, # Samples)
    g_stats = [(0, 0)] * 24
    for hour, users in hour_map.items():
        g_stats[hour.hour] = (g_stats[hour.hour][0] + len(users), g_stats[hour.hour][1] + 1)

    # convert stats for highcharts
    final_stats = []
    for hour in range(0, 24):
        if hour < 13:
            h = hour
            tod = 'AM'
        else:
            h = hour - 12
            tod = 'PM'
        final_stats.append({
            'name': str(h) + ':00' + tod,
            'data': [g_stats[hour][0] / g_stats[hour][1]]
        })

    return Response(json.dumps(final_stats), mimetype='application/json')


@stats.route('/user_stats', methods=['GET'])
@stats.route('/user_stats/<int:user_id>', methods=['GET'])
def user_stats(user_id=0):
    data = {
        'hours': 0,
        'games': 0,
        'days': 0,
    }

    if user_id != 0:
        where_clause = config.STATS_STATS_TABLE.c.userId == user_id
    else:
        where_clause = config.STATS_STATS_TABLE.c.userId != user_id

    print(user_id)

    results = select([
        config.STATS_STATS_TABLE.c.gameId,
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).where(
        and_(
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
            where_clause,
        )
    ).order_by(
        asc(
            config.STATS_STATS_TABLE.c.startTime
        )
    ).execute().fetchall()

    for result in results:
        if result.endTime:
            data['hours'] += (result.endTime - result.startTime).seconds / 60 / 60
        else:
            data['hours'] += (datetime.datetime.now() - result.startTime).seconds / 60 / 60
    data['hours'] = int(data['hours'])
    data['games'] = len(set([x['gameId'] for x in results]))
    data['days'] = (datetime.datetime.today() - results[0].startTime).days

    return Response(json.dumps(data), mimetype='application/json')


@stats.route('/game_stats', methods=['GET'])
@stats.route('/game_stats/<int:game_id>', methods=['GET'])
def game_stats(game_id=0):
    data = {
        'hours': 0,
        'players': 0,
        'percent_players': 0,
        'avg_session': 0,
    }

    if game_id != 0:
        where_clause = config.STATS_STATS_TABLE.c.gameId == game_id
    else:
        where_clause = config.STATS_STATS_TABLE.c.gameId != game_id

    results = select([
        config.STATS_STATS_TABLE.c.userId,
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).where(
        and_(
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
            where_clause,
        )
    ).execute().fetchall()

    players = []
    for result in results:
        players.append(result.userId)
        if result.endTime:
            data['hours'] += (result.endTime - result.startTime).seconds / 60 / 60
        else:
            data['hours'] += (datetime.datetime.now() - result.startTime).seconds / 60 / 60

    if results:
        data['avg_session'] = round(
            float(
                data['hours'] / len(
                    select([
                        config.STATS_STATS_TABLE.c.gameId
                    ]).where(
                        where_clause
                    ).execute().fetchall()
                )
            ),
            2
        )
    else:
        data['avg_session'] = 0

    data['players'] = len(set(players))
    data['percent_players'] = int(len(set(players)) / len(select([config.DISCORD_USER_TABLE.c.username]).execute().fetchall()) * 100)
    data['hours'] = round(data['hours'], 2)

    return Response(json.dumps(data), mimetype='application/json')


@stats.route('/game_heatmap', methods=['GET'])
@stats.route('/game_heatmap/<int:game_id>', methods=['GET'])
def game_heatmap(game_id=0):
    if game_id != 0:
        where_clause = config.STATS_STATS_TABLE.c.gameId == game_id
    else:
        where_clause = config.STATS_STATS_TABLE.c.gameId != game_id

    results = select([
        config.DISCORD_USER_TABLE.c.username,
        func.sum(
            func.timestampdiff(
                text('SECOND'),
                config.STATS_STATS_TABLE.c.startTime,
                config.STATS_STATS_TABLE.c.endTime
            )
        ).label('time_played')
    ]).select_from(
        config.DISCORD_USER_TABLE.join(
            config.STATS_STATS_TABLE,
            config.DISCORD_USER_TABLE.c.id == config.STATS_STATS_TABLE.c.userId
        )
    ).where(
        and_(
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
            where_clause,
        )
    ).group_by(
        config.STATS_STATS_TABLE.c.userId
    ).execute().fetchall()

    data = []
    for result in results:
        data.append({
            'name': result.username,
            'value': float(result.time_played / 60 / 60),
            'colorValue': int(result.time_played / 60 / 60),
        })
    return Response(json.dumps(data), mimetype='application/json')


@stats.route('/user_heatmap', methods=['GET'])
@stats.route('/user_heatmap/<int:user_id>', methods=['GET'])
def user_heatmap(user_id=0):
    if user_id != 0:
        where_clause = config.STATS_STATS_TABLE.c.userId == user_id
    else:
        where_clause = config.STATS_STATS_TABLE.c.userId != user_id
    results = select([
        config.STATS_GAMES_TABLE.c.name,
        func.sum(
            func.timestampdiff(
                text('SECOND'),
                config.STATS_STATS_TABLE.c.startTime,
                config.STATS_STATS_TABLE.c.endTime
            )
        ).label('time_played')
    ]).select_from(
        config.STATS_GAMES_TABLE.join(
            config.STATS_STATS_TABLE,
            config.STATS_GAMES_TABLE.c.id == config.STATS_STATS_TABLE.c.gameId
        )
    ).where(
        and_(
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
            where_clause,
        )
    ).group_by(
        config.STATS_STATS_TABLE.c.gameId
    ).order_by(
        desc(
            'time_played',
        )
    ).limit(
        50
    ).execute().fetchall()

    data = []
    for result in results:
        if result.time_played:
            data.append({
                'name': result.name,
                'value': float(result.time_played / 60 / 60),
                'colorValue': int(result.time_played / 60 / 60),
            })
        else:
            data.append({'name': result.name, 'value': 0.0, 'colorValue': 0})
    return Response(json.dumps(data), mimetype='application/json')


@stats.route('/typeahead', methods=['GET'])
def typeahead():
    user = request.args.get('user', None)
    game = request.args.get('game', None)
    if user is not None:
        results = select([
            config.DISCORD_USER_TABLE.c.username,
            config.DISCORD_USER_TABLE.c.id,
        ]).where(
            config.DISCORD_USER_TABLE.c.username.like(
                '%' + user + '%'
            )
        ).execute().fetchall()
        # Convert the data into typeahead format
        json_results = {'results': []}
        for result in results:
            json_results['results'].append({
                'title': result['username'],
                'value': str(result['id']),
            })
        return Response(json.dumps(json_results), mimetype='application/json')
    elif game is not None:
        results = select([
            config.STATS_GAMES_TABLE.c.name,
            config.STATS_GAMES_TABLE.c.id,
        ]).where(
            config.STATS_GAMES_TABLE.c.name.like(
                '%' + game + '%'
            )
        ).execute().fetchall()
        # Convert the data into typeahead format
        json_results = {'results': []}
        for result in results:
            json_results['results'].append({
                'title': result['name'],
                'value': result['id']
            })
        return Response(json.dumps(json_results), mimetype='application/json')
    else:
        return 'You must include a parameter to typeahead on', 400


@stats.route('/game_user_count', methods=['GET'])
@stats.route('/game_user_count/<int:game_id>', methods=['GET'])
def game_user_count_over_time(game_id):
    # get stats for the game
    results = select([
        config.STATS_STATS_TABLE.c.userId,
        config.STATS_GAMES_TABLE.c.name.label('gameName'),
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).select_from(
        config.STATS_STATS_TABLE.join(
            config.STATS_GAMES_TABLE,
            config.STATS_STATS_TABLE.c.gameId == config.STATS_GAMES_TABLE.c.id
        )
    ).where(
        and_(
            config.STATS_STATS_TABLE.c.endTime != None,
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
            config.STATS_STATS_TABLE.c.gameId == game_id,
            )
    ).order_by(
        asc(
            config.STATS_STATS_TABLE.c.startTime
        )
    ).execute().fetchall()

    # get the name of the game
    known_games = select([
        config.STATS_GAMES_TABLE.c.name,
    ]).where(
        config.STATS_GAMES_TABLE.c.id == game_id
    ).execute().fetchone()

    # sort the stats into the dates when they occurred
    game_data = {}
    for result in results:
        try:
            game_data[result['startTime'].strftime('%Y-%m-%d')].append(result['userId'])
        except KeyError:
            game_data[result['startTime'].strftime('%Y-%m-%d')] = []
            game_data[result['startTime'].strftime('%Y-%m-%d')].append(result['userId'])

    # get the earliest date we tracked stats for
    current_time = select([
        config.STATS_STATS_TABLE.c.startTime
    ]).order_by(asc(config.STATS_STATS_TABLE.c.startTime)).limit(1).execute().fetchone().startTime

    formatted_times = []
    games = []
    # reform the data into the format highcharts expects
    while current_time <= datetime.datetime.today():
        form_time = current_time.strftime('%Y-%m-%d')
        formatted_times.append(form_time)
        try:
            games.append(len(set(game_data[form_time])))
        except KeyError:
            games.append(0)
        current_time += timedelta(days=1)

    return Response(json.dumps({'times': formatted_times, 'games': [{'name': known_games['name'], 'data': games}]}), mimetype='application/json')


@stats.route('/total_game_user_count', methods=['GET'])
def game_user_count():
    results = select([
        config.STATS_STATS_TABLE.c.userId,
        config.STATS_GAMES_TABLE.c.name.label('gameName'),
        config.STATS_STATS_TABLE.c.startTime,
        config.STATS_STATS_TABLE.c.endTime,
    ]).select_from(
        config.STATS_STATS_TABLE.join(
            config.STATS_GAMES_TABLE,
            config.STATS_STATS_TABLE.c.gameId == config.STATS_GAMES_TABLE.c.id
        )
    ).where(
        and_(
            config.STATS_STATS_TABLE.c.endTime != None,
            ~config.STATS_STATS_TABLE.c.userId.in_(user_blacklist),
        )
    ).execute().fetchall()

    # We want to capture the number of unique players per game per hour
    # Hour -> (Game -> [Players])
    hour_map = {}
    for result in results:
        current_time = result['startTime'].replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = result['endTime'].replace(hour=0, minute=0, second=0, microsecond=0)

        # loop from start time to end time so we get a data point for each hour someone played a game
        while current_time <= end_time:
            if not hour_map.get(current_time):
                hour_map[current_time] = {}
            if result['gameName'] not in hour_map[current_time]:
                hour_map[current_time][result['gameName']] = []
            if result['userId'] not in hour_map[current_time][result['gameName']]:
                hour_map[current_time][result['gameName']].append(result['userId'])

            current_time += timedelta(days=1)

    known_games = select([
        config.STATS_GAMES_TABLE.c.name
    ]).execute().fetchall()

    # sort the times so that the resulting chart is a nice timeline
    times = sorted(list(hour_map.keys()))
    formatted_times = []

    games = {}
    for time in times:
        formatted_times.append(time.strftime('%Y-%m-%d'))

        # we want a metric for every game even if it hasn't been played within our timeframe
        # so we loop over all known games here
        for game_row in known_games:
            game_name = game_row['name']
            if games.get(game_name) is None:
                games[game_name] = []
            # if there were no players, we make sure to default to 0
            games[game_name].append(len(hour_map[time].get(game_name, [])))
    game_series = []
    for game, data in games.items():
        # make sure all lines are set to invisible since we presumably have a ton of
        # games to display and we don't want to crowd the graph
        # TODO: Set the Top X games to be visible
        game_series.append({'name': game, 'data': data, 'visible': False})

    stats = {'times': formatted_times, 'games': game_series}
    return Response(json.dumps(stats), mimetype='application/json')
