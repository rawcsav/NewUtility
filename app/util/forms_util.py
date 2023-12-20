from datetime import datetime

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, \
    IntegerField, TextAreaField, FloatField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length, Regexp, Email, EqualTo, \
    NumberRange, Optional


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
        Length(min=3, max=20)
    ])
    submit = SubmitField('Change Username')


class UploadAPIKeyForm(FlaskForm):
    api_key = StringField('API Key', validators=[
        DataRequired(),
        Regexp(r'sk-[A-Za-z0-9]{48}', message='Invalid API key format.')
    ])
    nickname = StringField('Nickname', validators=[Optional()])
    submit = SubmitField('Upload')


class DeleteAPIKeyForm(FlaskForm):
    key_id = HiddenField('Key ID', validators=[DataRequired()])
    submit = SubmitField('Delete API Key')


class RetestAPIKeyForm(FlaskForm):
    key_id = HiddenField('Key ID', validators=[DataRequired()])
    submit = SubmitField('Retest API Key')


class SelectAPIKeyForm(FlaskForm):
    key_id = HiddenField('Key ID', validators=[DataRequired()])


class GenerateImageForm(FlaskForm):
    prompt = StringField('Prompt', validators=[
        DataRequired(),
        Length(max=1000)
    ])
    model = StringField('Model', validators=[DataRequired()])
    n = IntegerField('N', validators=[
        DataRequired(),
        NumberRange(min=1, max=3)
    ])
    size = StringField('Size', validators=[DataRequired()])
    quality = StringField('Quality', validators=[Optional()])
    response_format = StringField('Response Format', validators=[Optional()])
    style = StringField('Style', validators=[Optional()])

    def validate(self, extra_validators=None):

        if not super(GenerateImageForm, self).validate(
                extra_validators=extra_validators):
            return False

        if self.model.data == 'dall-e-3':
            self.prompt.validators.append(Length(max=4000))

            self.n.validators.append(NumberRange(min=1, max=1))

            return super(GenerateImageForm, self).validate(
                extra_validators=extra_validators)
        return True


class DocumentUploadForm(FlaskForm):
    file = FileField('Document', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'txt'], 'Text, pdf, or doc files only!')
    ])
    title = StringField('Document Title', validators=[Optional()])
    author = StringField('Author Name', validators=[Optional()])
    chunk_size = IntegerField('Max Tokens per Chunk', validators=[
        Optional(), NumberRange(min=1, max=8000)
    ])


class DeleteDocumentForm(FlaskForm):
    submit = SubmitField('Delete')


class EditDocumentForm(FlaskForm):
    document_id = HiddenField('document_id', validators=[DataRequired()])
    title = StringField('Title', validators=[Optional()])
    author = StringField('Author', validators=[Optional()])
    submit = SubmitField('Update')


class ChatCompletionForm(FlaskForm):
    prompt = TextAreaField('Prompt', validators=[DataRequired()])
    conversation_id = HiddenField('Conversation ID', validators=[DataRequired()])
    submit = SubmitField('Get Completion')


class UserPreferencesForm(FlaskForm):
    show_timestamps = BooleanField('Timestamps')
    model = SelectField('Model', choices=[
        ('gpt-4-1106-preview', 'GPT-4 1106 Preview'),
        ('gpt-4-vision-preview', 'GPT-4 Vision Preview'),
        ('gpt-4', 'GPT-4'),
        ('gpt-4-32k', 'GPT-4 32k'),
        ('gpt-4-0613', 'GPT-4 0613'),
        ('gpt-4-32k-0613', 'GPT-4 32k 0613'),
        ('gpt-3.5-turbo-1106', 'GPT-3.5 Turbo 1106'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('gpt-3.5-turbo-16k', 'GPT-3.5 Turbo 16k')
    ])
    max_tokens = IntegerField('Max Tokens')
    temperature = DecimalField('Temperature',
                               validators=[NumberRange(min=0, max=2), Optional()],
                               places=1,
                               default=0.7)
    top_p = DecimalField('Top P', validators=[NumberRange(min=0, max=1)], places=2,
                         default=1.0)

    frequency_penalty = DecimalField('Frequency Penalty',
                                     validators=[NumberRange(min=-2, max=2)], places=2,
                                     default=0)

    presence_penalty = DecimalField('Presence Penalty',
                                    validators=[NumberRange(min=-2, max=2)], places=2,
                                    default=0)

    stream = BooleanField('Stream')
    submit = SubmitField('Get Completion')


class NewConversationForm(FlaskForm):
    # Dynamically generate the default system prompt with the current date
    default_prompt = (
        "You are Jack, a large language model trained by OpenAI, "
        "based on the GPT-4 architecture. You are chatting with the user "
        "via the RAWCSAV interface. This means you should "
        "use proper machine-readable markdown format where it is relevant. "
        "Knowledge cutoff: 2022-01. "
        f"The current date is {datetime.now().strftime('%Y-%m-%d')}."
    )

    system_prompt = StringField('System Prompt', default=default_prompt)
    submit = SubmitField('Start Conversation')
