from flask import Flask
from routes.process import bp as process_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.register_blueprint(process_bp, url_prefix='/api')
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
