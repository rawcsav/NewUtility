from datetime import datetime
from decimal import Decimal

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileField, FileAllowed
from wtforms import (StringField, PasswordField, BooleanField, SubmitField, HiddenField, IntegerField, TextAreaField,
                     DecimalField, SelectField, )
from wtforms.fields.numeric import FloatField
from wtforms.validators import DataRequired, Length, Regexp, Email, EqualTo, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=20),
                                                   Regexp(r"^\S+$", message="Username cannot contain spaces.")], )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8),
        Regexp(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]", message="Password requirements not met."),
        EqualTo("password", message="Passwords must match.")])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), Length(min=8), Regexp(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]", message="Password requirements not met."), ])
    submit = SubmitField("Register")


class ConfirmEmailForm(FlaskForm):
    code = StringField("Confirmation Code", validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField("Confirm Email")


class ResetPasswordRequestForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long."),
            EqualTo("confirm_password", message="Passwords must match."), ], )
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset Password")


class ChangeUsernameForm(FlaskForm):
    new_username = StringField("New Username", validators=[DataRequired(), Length(min=3, max=20)])
    submit = SubmitField("Change Username")


class UploadAPIKeyForm(FlaskForm):
    api_key = StringField("API Key",
        validators=[DataRequired(), Regexp(r"sk-[A-Za-z0-9]{48}", message="Invalid API key format.")])
    nickname = StringField("Nickname", validators=[Optional()])
    submit = SubmitField("Upload")


class DeleteAPIKeyForm(FlaskForm):
    key_id = HiddenField("Key ID", validators=[DataRequired()])
    submit = SubmitField("Delete API Key")


class RetestAPIKeyForm(FlaskForm):
    key_id = HiddenField("Key ID", validators=[DataRequired()])
    submit = SubmitField("Retest API Key")


class SelectAPIKeyForm(FlaskForm):
    key_id = HiddenField("Key ID", validators=[DataRequired()])


class GenerateImageForm(FlaskForm):
    prompt = StringField("Prompt", validators=[DataRequired(), Length(max=1000)])
    model = StringField("Model", validators=[DataRequired()])
    n = IntegerField("N", validators=[DataRequired(), NumberRange(min=1, max=3)])
    size = StringField("Size", validators=[DataRequired()])
    quality = StringField("Quality", validators=[Optional()])
    response_format = StringField("Response Format", validators=[Optional()])
    style = StringField("Style", validators=[Optional()])

    def validate(self, extra_validators=None):
        if not super(GenerateImageForm, self).validate(extra_validators=extra_validators):
            return False

        if self.model.data == "dall-e-3":
            self.prompt.validators.append(Length(max=4000))

            self.n.validators.append(NumberRange(min=1, max=1))

            return super(GenerateImageForm, self).validate(extra_validators=extra_validators)
        return True


class DocumentUploadForm(FlaskForm):
    file = FileField("Document", validators=[FileRequired(),
                                             FileAllowed(["pdf", "txt", "py", "css", "html", "md", "yml", "json"],
                                                         "Text or PDF files only!")], )
    title = StringField("Document Title", validators=[Optional()])
    author = StringField("Author Name", validators=[Optional()])
    chunk_size = IntegerField("Max Tokens per Chunk", validators=[Optional(), NumberRange(min=1, max=8000)])
    advanced_preprocessing = BooleanField("Enable Advanced Preprocessing", default=False)  # Added field


class DeleteDocumentForm(FlaskForm):
    submit = SubmitField("Delete")


class EditDocumentForm(FlaskForm):
    document_id = HiddenField("document_id", validators=[DataRequired()])
    title = StringField("Title", validators=[Optional()])
    author = StringField("Author", validators=[Optional()])
    submit = SubmitField("Update")


class ChatCompletionForm(FlaskForm):
    prompt = TextAreaField("Prompt", validators=[DataRequired()])
    conversation_id = HiddenField("Conversation ID", validators=[DataRequired()])
    submit = SubmitField("Get Completion")


class UserPreferencesForm(FlaskForm):
    model = SelectField("Model",
        choices=[("gpt-4-turbo", "GPT-4 Turbo"), ("gpt-4-turbo-2024-04-09", "GPT-4 Turbo 2024-04-09"),
            ("gpt-4-turbo-preview", "GPT-4 Turbo Preview"), ("gpt-4-0125-preview", "GPT-4 0125 Preview"),
            ("gpt-4-1106-preview", "GPT-4 1106 Preview"), ("gpt-4-vision-preview", "GPT-4 Vision Preview"),
            ("gpt-4-1106-vision-preview", "GPT-4 1106 Vision Preview"), ("gpt-4", "GPT-4"),
            ("gpt-4-0613", "GPT-4 0613"), ("gpt-4-32k", "GPT-4 32k"), ("gpt-4-32k-0613", "GPT-4 32k 0613"),
            ("gpt-3.5-turbo-0125", "GPT-3.5 Turbo 0125"), ("gpt-3.5-turbo", "GPT-3.5 Turbo"),
            ("gpt-3.5-turbo-1106", "GPT-3.5 Turbo 1106"), ("gpt-3.5-turbo-instruct", "GPT-3.5 Turbo Instruct"),
            ("gpt-3.5-turbo-16k", "GPT-3.5 Turbo 16k"), ("gpt-3.5-turbo-0613", "GPT-3.5 Turbo 0613"),
            ("gpt-3.5-turbo-16k-0613", "GPT-3.5 Turbo 16k 0613")], )
    max_tokens = IntegerField("Max Tokens")
    temperature = DecimalField("Temperature", validators=[NumberRange(min=0, max=2), Optional()], places=1,
        default=Decimal("0.7"))
    top_p = DecimalField("Top P", validators=[NumberRange(min=0, max=1)], places=2, default=Decimal("1.00"))

    frequency_penalty = DecimalField("Frequency Penalty", validators=[NumberRange(min=-2, max=2)], places=2,
        default=Decimal("0.00"))

    presence_penalty = DecimalField("Presence Penalty", validators=[NumberRange(min=-2, max=2)], places=2,
        default=Decimal("0.00"))

    submit = SubmitField("Get Completion")


class NewConversationForm(FlaskForm):
    default_prompt = ("You are RAWCBOT, a large language model trained by OpenAI, "
                      "based on the GPT-4 architecture. You are chatting with the user "
                      "via the RAWCSAV interface. This means you should "
                      "use proper machine-readable markdown format where it is relevant. "
                      "Knowledge cutoff: 2022-01. "
                      f"The current date is {datetime.now().strftime('%Y-%m-%d')}.")

    system_prompt = StringField("System Prompt", default=default_prompt)
    submit = SubmitField("Start Conversation")


class UpdateDocPreferencesForm(FlaskForm):
    default_prompt = "You are a helpful academic literary assistant. Provide in -depth guidance, suggestions, code snippets, and explanations as needed to help the user. Leverage your expertise and intuition to offer innovative and effective solutions.Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. Use the provided text excerpts directly to aid in your responses."
    cwd_system_prompt = StringField("System Prompt", default=default_prompt)
    document_id = StringField("Document ID", validators=[Optional()])
    selected = BooleanField("Selected", validators=[Optional()])
    knowledge_query_mode = BooleanField("Enable", validators=[Optional()], default=False)
    top_k = FloatField("Sections",
        validators=[Optional(), NumberRange(min=1, max=60, message="Value must be between 1 and 60")], default=10)
    threshold = FloatField("Threshold",
        validators=[Optional(), NumberRange(min=0.0, max=1.0, message="Value must be between 0.0 and 1.0")],
        default=0.5)
    temperature = DecimalField("Temperature", validators=[NumberRange(min=0, max=2), Optional()], places=1,
        default=Decimal("0.7"))
    top_p = DecimalField("Top P", validators=[NumberRange(min=0, max=1)], places=2, default=Decimal("1.00"))


class TtsPreferencesForm(FlaskForm):
    model = SelectField("Model", choices=[("tts-1", "TTS 1"), ("tts-1-hd", "TTS 1 HD")], default="tts-1")
    voice = SelectField("Voice",
        choices=[("alloy", "Alloy"), ("echo", "Echo"), ("fable", "Fable"), ("onyx", "Onyx"), ("nova", "Nova"),
            ("shimmer", "Shimmer"), ], default="alloy", )
    response_format = SelectField("Response Format",
        choices=[("mp3", "MP3"), ("opus", "OPUS"), ("aac", "AAC"), ("flac", "FLAC")], default="mp3")
    speed = FloatField("Speed", validators=[DataRequired(), NumberRange(min=0.5, max=2.0)], default=1.0)


class TtsForm(FlaskForm):
    input = StringField("Input", validators=[DataRequired(), Length(max=4096)])


class WhisperPreferencesForm(FlaskForm):
    response_format = SelectField("Response Format",
        choices=[("json", "JSON"), ("text", "Text"), ("srt", "SRT"), ("verbose_json", "Verbose JSON"), ("vtt", "VTT")],
        default="json", )
    temperature = DecimalField("Temperature", validators=[Optional(), NumberRange(min=0.0, max=1.0)], places=1,
        default=Decimal("0.0"))
    model = SelectField("Model", choices=[("whisper-1", "Whisper 1")], default="whisper-1")
    language_choices = [("en", "English"), ("zh", "Chinese"), ("es", "Spanish"), ("hi", "Hindi"), ("ar", "Arabic"),
        ("pt", "Portuguese"), ("ru", "Russian"), ("ja", "Japanese"), ("de", "German"), ("fr", "French"),
        ("ko", "Korean"), ("it", "Italian"), ("vi", "Vietnamese"), ("ur", "Urdu"), ]
    language = SelectField("Language", choices=language_choices)


class TranscriptionForm(FlaskForm):
    file = FileField("Audio File", validators=[DataRequired(),
        FileAllowed(["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"], "Invalid audio format!"), ], )
    prompt_option = SelectField("Prompt option",
        choices=[("none", "None"), ("manual", "Enter prompt manually"), ("generate", "Generate prompt based on idea")],
        default="none", )
    prompt = StringField("Prompt", validators=[Optional()])
    generate_prompt = StringField("Generate Prompt", validators=[Optional()])


class TranslationForm(FlaskForm):
    # Form for creating translation POST requests
    file = FileField("Audio File", validators=[DataRequired(),
        FileAllowed(["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"], "Invalid audio format!"), ], )
    prompt_option = SelectField("Prompt option",
        choices=[("none", "None"), ("manual", "Enter prompt manually"), ("generate", "Generate prompt based on idea")],
        default="none", )
    prompt = StringField("Prompt", validators=[Optional()])
    generate_prompt = StringField("Generate Prompt", validators=[Optional()])
