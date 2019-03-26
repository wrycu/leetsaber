import json
from datetime import timedelta

from flask import Blueprint, render_template, Response, request
from sqlalchemy import select, and_, asc, desc, func
from sqlalchemy import text
import datetime

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
    try:
        return config.CONTROL_MAPPER.render_controls(request.files['controls'].read())
    except Exception as e:
        print(e)
        return str(e), 400
