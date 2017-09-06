import json
from datetime import timedelta

from flask import Blueprint, render_template, Response, request
from sqlalchemy import select, and_, asc, desc, func
from sqlalchemy import text
import datetime

from app import config

main = Blueprint(
    'main',
    __name__,
)


@main.route('/', methods=['GET'])
def landing():
    return render_template(
        'base.html',
    )
