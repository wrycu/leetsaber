from flask import Flask
from app.flask_app.main.controllers import main
from app.flask_app.stats.controllers import stats
from app.flask_app.armada.controllers import armada

app = Flask(__name__)
app.config.from_object('app.config')


@app.errorhandler(404)
def not_found(error):
    return 'Not found, bubs', 404


app.register_blueprint(main)
app.register_blueprint(stats, url_prefix='/stats')
app.register_blueprint(armada, url_prefix='/armada')
