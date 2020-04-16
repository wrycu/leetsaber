from flask import Blueprint, render_template, request, Response
import json
from sqlalchemy import select
import dcs as pydcs
from misc.t_dcs import MissionParser, MissionSearcher
from app import config

dcs = Blueprint(
    'dcs',
    __name__,
)


@dcs.route('/', methods=['GET'])
def landing():
    return render_template(
        'dcs/base.html',
        body='',
    )


@dcs.route('/upload', methods=['POST'])
def upload():
    """
    TODO
    throw client-side error if they select >2 files
    change font size based on character count
CMS down is not in image
label switched images

IGN --> ENG OPER
all IGN should be blue

IGN L / IGN R are missing
slew button --> include
resize to be kneeboard sized?

    :return:
    """
    try:
        stick, throttle = config.CONTROL_MAPPER.render_controls(request.files['controls'].read())
        if 'controls2' in request.files:
            # user uploaded two files
            stick2, throttle2 = config.CONTROL_MAPPER.render_controls(request.files['controls2'].read())
            # we are not sure which file we parsed first. there are better ways to do this, but this is fastest :0
            if not stick:
                stick = stick2
            elif not throttle:
                throttle = throttle2

        return render_template(
            'dcs/hotas.html',
            joystick=stick,
            throttle=throttle,
        )
    except Exception as e:
        print(e)
        return str(e), 400


@dcs.route('/missions', methods=['GET', 'POST'])
def list_missions():
    if request.method == 'GET':
        pilots, modules = config.GDRIVE.get_pilots()
        print(pilots)
        return render_template(
            'dcs/mission_filter.html',
            pilots=pilots,
            modules=modules,
        )
    else:
        # build a list of modules that the POSTed pilots own so we can query for missions
        # build a pilot --> modules mapping
        matching_missions = []
        world_pilots, modules = config.GDRIVE.get_pilots()
        pilot_mapping = {}
        for pilot in request.json['pilot']:
            modules = world_pilots[request.json['context']][pilot]
            pilot_mapping[pilot] = [x for x in modules if modules[x] == '1']
        print(pilot_mapping)
        # ok, now build a list of slots available in the mission
        missions = {}

        results = select([
            config.DCS_M_M_TABLE.c.module_count,
            config.DCS_M_M_TABLE.c.mission_id,
            config.DCS_MODULE_TABLE.c.name,
        ]).select_from(
            config.DCS_M_M_TABLE.join(
                config.DCS_MODULE_TABLE,
                config.DCS_MODULE_TABLE.c.id == config.DCS_M_M_TABLE.c.module_id
            )
        ).execute().fetchall()

        mission_count = len(results)

        for result in results:
            if result.mission_id not in missions:
                missions[result.mission_id] = {}
            if result.name not in missions[result.mission_id]:
                missions[result.mission_id][result.name] = 0
            missions[result.mission_id][result.name] += 1

        print(missions)
        matched = []

        for m_id, mission in missions.items():
            m = MissionSearcher(
                pilot_mapping,
                mission
            )
            if m.solve(m.state):
                print("solved for {} - {}".format(m_id, m.state))
                matched.append(m_id)
            else:
                print("Couldn't find matching for {} - slots - {}".format(m_id, mission))

        matched_details = {}
        # select details for matched missions
        for mission in matched:
            results = select([
                config.DCS_MISSION_TABLE.c.name.label('mission_name'),
                config.DCS_MISSION_TABLE.c.map,
                config.DCS_MISSION_TABLE.c.start_time,
            ]).where(
                config.DCS_MISSION_TABLE.c.id == mission
            ).execute().fetchall()
            for result in results:
                matched_details[result.mission_name] = {
                    'terrain': result.map,
                    'time': result.start_time,
                    'factions': {
                        'blue': {
                            'aircraft': {},
                        },
                        'red': {
                            'aircraft': {},
                        },
                    }
                }
                # get aircraft in the mission
                raw_planes = select([
                    config.DCS_MODULE_TABLE.c.name,
                    config.DCS_M_M_TABLE.c.module_count,
                ]).select_from(
                    config.DCS_MODULE_TABLE.join(
                        config.DCS_M_M_TABLE,
                        config.DCS_MODULE_TABLE.c.id == config.DCS_M_M_TABLE.c.module_id,
                    )
                ).where(
                    config.DCS_M_M_TABLE.c.mission_id == mission
                ).execute().fetchall()
                for plane in raw_planes:
                    matched_details[result.mission_name]['factions']['blue']['aircraft'][plane.name] = plane.module_count
        print(pilot_mapping)
        return Response(
            json.dumps({
                'status': render_template(
                    'dcs/mission_filter_results.html',
                    missions=matched_details,
                    players=pilot_mapping,
                    mission_count=mission_count,
                    match_count=len(matched),
                )
            }),
            mimetype='application/json'
        )
        return Response(json.dumps({'status': 'you <b>did</b> it!'}), mimetype='application/json')
