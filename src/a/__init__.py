#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a.ari-web.xyz"""

import os
import secrets
from functools import lru_cache
from typing import Optional, Tuple

import flask
import web_mini
from flask_login import LoginManager  # type: ignore
from werkzeug.exceptions import HTTPException

from .const import USERNAME_LEN


@lru_cache
def min_css(css: str) -> str:
    """minify css"""
    return web_mini.css.minify_css(css)


def create_app() -> flask.Flask:
    """create a new flask app"""

    web_mini.compileall()

    app: flask.Flask = flask.Flask(__name__)

    if not os.path.exists("secret.key"):
        with open("secret.key", "wb") as fp:
            fp.write(secrets.SystemRandom().randbytes(2**14))

    with open("secret.key", "rb") as fp:
        app.config["SECRET_KEY"] = fp.read()

    app.config["CAPTCHA_PEPPER_FILE"] = "captcha.key"
    app.config["CAPTCHA_EXPIRY"] = 60 * 10  # 10 minutes

    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True

    app.config["REMEMBER_COOKIE_NAME"] = "authorization"
    app.config["REMEMBER_COOKIE_SAMESITE"] = "None"
    app.config["REMEMBER_COOKIE_SECURE"] = True

    app.config["USE_SESSION_FOR_NEXT"] = True

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///main.db"

    from .models import User, argon2, db

    db.init_app(app)

    with app.app_context():
        db.create_all()

    argon2.init_app(app)  # type: ignore

    lm: LoginManager = LoginManager(app)

    lm.login_view = "auth.signin"  # type: ignore
    lm.refresh_view = "auth.signin"  # type: ignore
    lm.session_protection = "strong"  # type: ignore
    lm.login_message = "please sign in"  # type: ignore
    lm.needs_refresh_message = "your login expired, please sign in again"  # type: ignore

    @lm.user_loader  # type: ignore
    def _(username: str) -> Optional[User]:
        """load user by username"""

        if username and len(username) <= USERNAME_LEN:
            return User.get_by_user(username)

    @app.after_request
    def _(response: flask.Response) -> flask.Response:
        """minify resources"""

        if response.direct_passthrough:
            return response

        response_data: str = response.get_data(as_text=True)

        if response.content_type == "text/html; charset=utf-8":
            minified_data: str = web_mini.html.minify_html(response_data)
        elif response.content_type == "text/css; charset=utf-8":
            minified_data: str = min_css(response_data)
        else:
            return response

        return app.response_class(
            response=minified_data,
            status=response.status,
            headers=dict(response.headers),
            mimetype=response.mimetype,
        )

    @app.errorhandler(HTTPException)
    def _(e: HTTPException) -> Tuple[str, int]:
        """handle http errors"""
        return (
            flask.render_template(
                "http.j2",
                code=e.code,
                summary=e.name.lower(),
                description=(e.description or f"http error code {e.code}").lower(),
            ),
            e.code or 200,
        )

    from .c import c

    c.init_app(app)

    from .views import views

    app.register_blueprint(views, url_prefix="/")

    from .auth import auth

    app.register_blueprint(auth, url_prefix="/auth")

    from .api import api

    app.register_blueprint(api, url_prefix="/api")

    return app
