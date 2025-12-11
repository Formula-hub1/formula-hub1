from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, RecoverPasswordForm, ResetPasswordForm, SignupForm
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()

@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)
        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.login(form.email.data, form.password.data):
            return redirect(url_for("public.index"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))

@auth_bp.route("/recover-password/", methods=["GET", "POST"])
def show_recover_password_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = RecoverPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        if authentication_service.is_email_available(email):
            return render_template(
                "auth/recover_password_form.html", form=form, error=f"Email {email} does not belong to a user"
            )

    try:
        authentication_service.send_email(**form.data)
    except Exception as exc:
        return render_template("auth/recover_password_form.html", form=form, error=f"Error sending email: {exc}")

    return render_template("auth/recover_password_form.html", form=form)

@auth_bp.route("/reset-password/", methods=["GET", "POST"])
def reset_password_form():
    token = request.args.get("token")
    user = authentication_service.verify_reset_token(token)
    if not user:
        return redirect(url_for("auth.login"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        new_password_value = form.password.data

        if user.check_password(new_password_value):
            error_message = "New password can not be the same as the last one."
            return render_template("auth/reset_password_form.html", form=form, token=token, error=error_message)

        authentication_service.update_password(user.id, new_password_value)
        db.session.commit()
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password_form.html", form=form)
