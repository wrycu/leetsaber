from flask import Blueprint, render_template, Response, request

from app import config

xwing = Blueprint(
    'xwing',
    __name__,
)


@xwing.route('/', methods=['GET'])
def landing():
    return render_template(
        'wip.html',
    )
