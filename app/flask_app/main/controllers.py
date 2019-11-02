from flask import Blueprint, redirect, url_for

main = Blueprint(
    'main',
    __name__,
)


@main.route('/', methods=['GET'])
def landing():
    return redirect(
        url_for(
            'stats.landing'
        )
    )
