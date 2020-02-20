from flask import Flask
from app.flask_app.main.controllers import main
from app.flask_app.stats.controllers import stats
from app.flask_app.armada.controllers import armada
from app.flask_app.dcs.controller import dcs
from app.flask_app.fad.controller import fad

app = Flask(__name__)
app.config.from_object('app.config')


@app.errorhandler(404)
def not_found(error):
    return 'Not found, bubs', 404


app.register_blueprint(main)
app.register_blueprint(stats, url_prefix='/stats')
app.register_blueprint(armada, url_prefix='/armada')
app.register_blueprint(dcs, url_prefix='/dcs')
app.register_blueprint(fad, url_prefix='/force_and_destiny')
