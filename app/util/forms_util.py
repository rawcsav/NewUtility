from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Regexp, Email, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=20),
        Regexp(r'^\S+$', message='Username cannot contain spaces.')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]',
               message='Password requirements not met.')
    ])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class ConfirmEmailForm(FlaskForm):
    code = StringField('Confirmation Code',
                       validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Confirm Email')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.'),
        EqualTo('confirm_password', message='Passwords must match.')
    ])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class ChangeUsernameForm(FlaskForm):
    new_username = StringField('New Username', validators=[
        DataRequired(),
        Length(min=3, max=20)  # Adjust length limits as needed
    ])
    submit = SubmitField('Change Username')


class UploadAPIKeyForm(FlaskForm):
    api_key = StringField('API Key', validators=[
        DataRequired(),
        Regexp(r'sk-[A-Za-z0-9]{48}', message='Invalid API key format.')
    ])
    nickname = StringField('Nickname', validators=[DataRequired()])
    submit = SubmitField('Upload')


class DeleteAPIKeyForm(FlaskForm):
    key_id = HiddenField('Key ID', validators=[DataRequired()])
    submit = SubmitField('Delete API Key')


class RetestAPIKeyForm(FlaskForm):
    key_id = HiddenField('Key ID', validators=[DataRequired()])
    submit = SubmitField('Retest API Key')
