"""
Package: service
This module creates and configures the Flask app, adds logging,
security headers (Talisman), and CORS policies.
"""
import sys
from flask import Flask
from flask_talisman import Talisman
from flask_cors import CORS
from service import config
from service.common import log_handlers

# Create Flask application
app = Flask(__name__)
app.config.from_object(config)

# Apply security headers with Flask-Talisman
talisman = Talisman(app)

# Apply CORS policy to allow all origins
CORS(app)

# Import routes and models after app creation
from service import routes, models  # noqa: E402
from service.common import error_handlers, cli_commands  # noqa: E402

# Set up logging for production
log_handlers.init_logging(app, "gunicorn.error")

app.logger.info(70 * "*")
app.logger.info("  A C C O U N T   S E R V I C E   R U N N I N G  ".center(70, "*"))
app.logger.info(70 * "*")

try:
    models.init_db(app)  # make our database tables
except Exception as error:  # pylint: disable=broad-except
    app.logger.critical("%s: Cannot continue", error)
    sys.exit(4)

app.logger.info("Service initialized!")
