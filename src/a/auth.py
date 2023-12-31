#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""authentication"""

import typing as t
from functools import wraps

import flask
from flask_ishuman import CaptchaGenerator
from flask_login import login_required  # type: ignore
from flask_login import current_user, login_user, logout_user  # type: ignore
from werkzeug.wrappers import Response

from . import const, models, util
from .c import audio as gen_audio_captcha
from .c import c
from .routing import Bp

auth: Bp = Bp("auth", __name__)


def nologin(fn: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    """redirect back to / if logged in"""

    @wraps(fn)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        if current_user.is_authenticated:  # type: ignore
            flask.flash("you are already signed in", "info")
            return flask.redirect("/")

        return fn(*args, **kwargs)

    return wrapper


@auth.get("/captcha")
def captcha() -> str:
    """returns a captcha as json"""

    new: CaptchaGenerator = c.new()

    return flask.jsonify(  # type: ignore
        [
            new.image(),
            gen_audio_captcha(new),
        ]
    )


@auth.route("/", methods=("POST", "GET"))
def auth_redirect() -> Response:
    """redirect to auth.signin"""
    return flask.redirect(flask.url_for("auth.signin"))


@auth.get("/signout")
@login_required
def signout() -> Response:
    """sign the current user out"""
    logout_user()
    flask.flash("you have been signed out", "info")
    return flask.redirect("/")


@auth.get("/signup")
@nologin
def signup_page() -> str:
    """signup page"""
    return flask.render_template(
        "signup.j2",
        c=util.jscaptcha(),
    )


@auth.get("/signin")
@nologin
def signin_page() -> str:
    """signin page"""
    return flask.render_template(
        "signin.j2",
        c=util.jscaptcha(),
    )


@auth.get("/manage")
@login_required
def manage_page() -> str:
    """manage current user"""

    return flask.render_template(
        "manage.j2",
        c=util.jscaptcha(),
        username_len=const.USERNAME_LEN,
        bio_len=const.BIO_LEN,
    )


@auth.post("/signup")
@nologin
@util.captcha
def signup() -> t.Union[t.Tuple[str, int], Response]:
    """signup logic"""

    username: t.Optional[str] = flask.request.form.get("username")
    password: t.Optional[str] = flask.request.form.get("password")
    terms: t.Optional[str] = flask.request.form.get("terms")

    if terms != "on":
        return util.flash_render("terms have not been accepted", "signup.j2"), 403

    if not (username and password) or not util.validate_username(username):
        return util.flash_render("invalid request", "signup.j2"), 400

    pin: str = models.gen_pin()

    try:
        models.db.session.add(models.User(username, password, pin))
        models.db.session.commit()
    except Exception:
        models.db.session.rollback()
        return (
            util.flash_render("username is taken / invalid request", "signup.j2"),
            500,
        )

    return flask.render_template("created.j2", pin=pin, username=username), 200


@auth.post("/signin")
@nologin
@util.captcha
def signin() -> t.Union[t.Tuple[str, int], Response]:
    """login logic"""

    username: t.Optional[str] = flask.request.form.get("username")
    password: t.Optional[str] = flask.request.form.get("password")
    pin: t.Optional[str] = flask.request.form.get("pin")
    user: t.Optional[models.User]

    if not (username and password and pin):
        return util.flash_render("invalid request", "signin.j2"), 400

    if (user := models.User.get_by_user(username)) is None:
        return util.flash_render("no such user", "signin.j2"), 404

    if not (user.verify_password(password) and user.verify_pin(pin)):
        return util.flash_render("invalid pin and / or password", "signin.j2"), 401

    login_user(user, True)

    return flask.redirect("/")


@auth.post("/manage")
@login_required
@util.captcha
def manage() -> t.Tuple[str, int]:
    """manage current user"""

    old_password: t.Optional[str] = flask.request.form.get("password_old")
    new_password: t.Optional[str] = flask.request.form.get("password")
    pin: t.Optional[str] = flask.request.form.get("pin")
    bio: t.Optional[str] = flask.request.form.get("bio")

    if old_password and new_password and pin:
        if not (
            current_user.check_password(new_password)  # type: ignore
            and current_user.verify_pin(pin)  # type: ignore
            and current_user.verify_password(old_password)  # type: ignore
        ):
            return (
                util.flash_render(
                    "invalid password( s ) or PIN",
                    "manage.j2",
                ),
                401,
            )

        current_user.set_password(new_password)  # type: ignore

    if bio is not None:
        current_user.bio = bio  # type: ignore

    try:
        models.db.session.commit()
    except Exception:
        models.db.session.rollback()
        return (
            util.flash_render(
                "invalid request / server error",
                "manage.j2",
            ),
            500,
        )

    return (
        util.flash_render(
            "user updated",
            "manage.j2",
            level="info",
        ),
        200,
    )


@auth.get("/delete")
@login_required
def delete() -> str:
    """delete account"""
    return flask.render_template("delete.j2", c=util.jscaptcha())


@auth.post("/delete")
@login_required
@util.captcha
def delete_user() -> Response:
    """delete account"""

    sure: t.Optional[str] = flask.request.form.get("sure")

    if sure != "on":
        flask.flash("account not deleted", "info")
        return flask.redirect("/")

    if not current_user.delete_user():  # type: ignore
        flask.flash("failed to delete account", "error")
        flask.abort(500)

    logout_user()
    flask.flash("account deleted", "info")

    return flask.redirect("/")
