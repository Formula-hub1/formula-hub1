"""
Community module initialization
"""

from flask import Flask


def init_app(app: Flask):
    """Initialize community module"""
    from app.modules.community.routes import community_bp

    app.register_blueprint(community_bp)

    # Import models to ensure they're registered with SQLAlchemy
    from app.modules.community import models  # noqa: F401
