from flask import Blueprint, render_template, request

from app import config

fad = Blueprint(
    'fad',
    __name__,
)


@fad.route('/', methods=['GET'])
def landing():
    return render_template(
        'fad/base.html',
        body='',
    )
