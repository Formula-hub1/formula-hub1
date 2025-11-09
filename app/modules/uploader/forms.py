from flask_wtf import FlaskForm
from wtforms import SubmitField


class UploaderForm(FlaskForm):
    submit = SubmitField('Save uploader')
