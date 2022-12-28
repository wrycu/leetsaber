import datetime

import flask
from flask import Blueprint, render_template, request, Response, send_file, make_response
import json
from sqlalchemy import select, and_
import arrow
import os
from misc.t_dcs import MissionSearcher
import zipfile
import io
from pathlib import Path
from app import config

dcs = Blueprint(
    'dcs',
    __name__,
)


@dcs.route('/', methods=['GET'])
def landing():
    return render_template(
        'dcs/base.html',
    )


@dcs.route('/upload', methods=['POST'])
def upload():
    """
    TODO
        Throw client-side error if they select >2 files
        Change font size based on character count
        Include axis
            slew button
            slider
        Resize to be kneeboard sized?
        Include none-controller modifiers (e.g. keyboard)
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
        modules = select([
            config.DCS_MODULE_TABLE.c.id,
            config.DCS_MODULE_TABLE.c.name,
        ]).order_by(
            config.DCS_MODULE_TABLE.c.name,
        ).execute().fetchall()

        return render_template(
            'dcs/mission.html',
            modules=modules,
        )
    else:
        # find matching missions
        pilot_mapping = {}

        desired_modules = request.json['modules']
        desired_count = [int(x) for x in request.json['counts']]
        desired_cap = sum(desired_count) + int(request.json['cap'])

        # build the where statement
        for x, module in enumerate(desired_modules):
            pilot_mapping[int(module)] = desired_count[x]
        print(pilot_mapping)

        # ok, now build a list of slots available in the mission
        results = select([
            config.DCS_MISSION_TABLE.c.id,
        ]).execute().fetchall()

        missions = [x.id for x in results]
        # how many missions have the _slots_ we desire
        match_count = 0

        matched_details = []
        # select details for matched missions
        for mission in missions:
            results = select([
                config.DCS_MISSION_TABLE.c.id,
                config.DCS_MISSION_TABLE.c.name.label('mission_name'),
                config.DCS_MISSION_TABLE.c.map,
                config.DCS_MISSION_TABLE.c.start_time,
                config.DCS_MISSION_TABLE.c.ed_id,
                config.DCS_MISSION_TABLE.c.ed_upload_date,
            ]).where(
                config.DCS_MISSION_TABLE.c.id == mission
            ).execute().fetchall()
            for result in results:
                details = {
                    'terrain': result.map,
                    'time': result.start_time,
                    'factions': {
                        'blue': {
                            'aircraft': {},
                        },
                        'red': {
                            'aircraft': {},
                        },
                    },
                    'total_slots': 0,
                    'id': result.id,
                    'name': result.mission_name,
                    'ed_id': result.ed_id,
                    'ed_date': result.ed_upload_date,
                }
                # get aircraft in the mission
                raw_planes = select([
                    config.DCS_MODULE_TABLE.c.id,
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

                met_criteria = None

                parsed_planes = {}
                for plane in raw_planes:
                    parsed_planes[plane.id] = {
                        'name': plane.name,
                        'count': plane.module_count,
                    }

                for module, desired_module_count in pilot_mapping.items():
                    # check if it's in the mission, if it has the count, AND if we haven't already failed to meet these criteria
                    if module in parsed_planes.keys() and parsed_planes[module]['count'] >= desired_module_count:
                        if met_criteria is None:
                            # avoid setting it to true if we've already set it to false
                            met_criteria = True
                    else:
                        met_criteria = False
                if met_criteria:
                    match_count += 1
                for plane in raw_planes:
                    details['factions']['blue']['aircraft'][plane.name] = plane.module_count
                    details['total_slots'] += plane.module_count
                if details['total_slots'] > desired_cap or not met_criteria:
                    continue
                matched_details.append(details)
        matched_details = sorted(matched_details, key=lambda k: k['total_slots'])
        mission_count = len(select([config.DCS_MISSION_TABLE.c.id]).execute().fetchall())
        print("found a total of {} missions".format(len(matched_details)))

        return Response(
            json.dumps({
                'status': render_template(
                    'dcs/mission_filter_results.html',
                    missions=matched_details,
                    mission_count=mission_count,
                    match_count=match_count,
                    match_count_filtered=len(matched_details),
                )
            }),
            mimetype='application/json'
        )


@dcs.route('/stats', methods=['GET'])
def mission_stats():

    missions = select([
        config.DCS_MISSION_TABLE.c.ed_upload_date,
    ]).order_by(
        config.DCS_MISSION_TABLE.c.ed_upload_date,
    ).execute().fetchall()

    last_upload = arrow.now().floor('month')
    missions_uploaded = {}
    cumulative_upload = {}

    sorted_data = {
        'dates': [],
        'total': [],
        'by_month': [],
    }

    # populate data
    total = 0
    for row in missions:
        total += 1
        current_upload = str(arrow.get(row[0]).floor('month').year)
        if current_upload not in missions_uploaded:
            missions_uploaded[current_upload] = 0
        missions_uploaded[current_upload] += 1
        cumulative_upload[current_upload] = total

    current_upload = arrow.get(missions[0][0]).floor('month')
    # backfill months while iterating over every month
    x = 0
    while current_upload < last_upload:
        # add the date to our known dates
        sorted_data['dates'].append(
            str(current_upload.year)
        )
        # check if the date is known and add the individual point if it is
        if str(current_upload.year) not in missions_uploaded:
            sorted_data['by_month'].append(
                0
            )
            # we also have cumulative data for this date
            sorted_data['total'].append(
                sorted_data['total'][x - 1]
            )
        else:
            sorted_data['by_month'].append(
                missions_uploaded[str(current_upload.year)]
            )
            # we don't have cumulative data for this date, pick it from the previous date
            sorted_data['total'].append(
                cumulative_upload[str(current_upload.year)]
            )
        x += 1
        current_upload = current_upload.shift(years=1)

    return render_template(
        'dcs/mission_stats.html',
        uploaded=missions_uploaded,
        cumulative=cumulative_upload,
        sorted_data=sorted_data,
    )


@dcs.route('/kneeboard', methods=['GET', 'POST'])
def kneeboard():
    if request.method == 'GET':
        return render_template(
            'dcs/kneeboard.html',
        )
    elif request.method == 'POST':
        pages = [
            Path('C:\\Users\\Tim\\Pictures\\st_logo_transparent_yt_style.0.png'),
        ]
        try:
            in_memory_zip = io.BytesIO()
            data = io.BytesIO(request.files['msn'].getvalue())
            in_len = data.getbuffer().nbytes

            with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for file_name, contents in extract_zip(data).items():
                    zf.writestr(file_name, contents)
                for page in pages:
                    zf.write(page, 'KNEEBOARD\\F-14B\\IMAGES\\1.png')

            in_memory_zip.seek(0)
            out_len = in_memory_zip.getbuffer().nbytes
            extract_zip(in_memory_zip)
            in_memory_zip.seek(0)
            print(f"IN: {in_len} OUT: {out_len}")
            return send_file(in_memory_zip, attachment_filename=request.files['msn'].filename, as_attachment=True)
        except Exception as e:
            return Response(
                str(e),
                500
            )


def extract_zip(contents):
    input_zip = zipfile.ZipFile(contents, 'r')
    contents = {}
    for file in input_zip.namelist():
        contents[file] = input_zip.read(file)
    return contents
