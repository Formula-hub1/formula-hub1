from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import Optional, URL


class UploaderForm(FlaskForm):
    file = FileField("Zip file", validators=[Optional()])
    url = StringField("GitHub URL", validators=[Optional(), URL()])
    submit = SubmitField("Upload")
