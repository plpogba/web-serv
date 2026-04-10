from flask import Flask
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

# Import routes so they are registered on the shared app instance.
_flask_app = app
import app.app  # noqa: F401
app = _flask_app
del _flask_app
