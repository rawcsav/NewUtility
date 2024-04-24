# New Utility

'New Utility' is a project that has evolved through various name changes and shifting focuses throughout its development. At its heart, it's my own way of taking the customizable and utilitarian aspects of the OpenAI API suite, and making them more intuitive and user-friendly for friends, random users, and anyone who may find navigating the full capabilities of the API challenging. 

More than that, it's also a platform for me to learn, experiment, and grow as a developer. This means it certainly may not work 100% correctly, it may not look 100% beautiful, but it is all my own effort to learn by experience. In this vain, if you encounter any issues or see potential improvements, please feel free to [reach out](https://rawcsav.com/contact.html). Your feedback is invaluable.

While my experiments with CSS Flexbox might not directly affect users, any compromise on security measures certainly could. Creating an account is meant to be a secure and worry-free experience. The project is [open-source on GitHub](https://github.com/rawcsav/AIUtilsFlask), and I've implemented best practice security measures at every step. These measures are detailed in full after the utilities snapshot.

## Core Utilities

### Chat Utilities
- Manage conversation history, including all previous messages.
- Knowledge retrieval using provided documents.
- GPT-4 Vision integration.
- Customize AI responses: model, temperature, max tokens, top P, frequency penalty, presence penalty.


### Image Utilities
- Generate images from text prompts using AI.
- Models: `dall-e-2`, `dall-e-3`.
- Options for image size and style.
- Quality selection for DALL-E 3: standard, HD.

### Document Embedding and Management
- Upload documents for chat embedding: `.txt` or `.pdf`.
- Edit document metadata for better context in retrieval.
- Manage embedded documents: select for chat, delete.
- Adjust context token percentage for knowledge retrieval in chat.
- Metadata helps AI with citing and sourcing.

### Text-to-Speech (TTS)
- Converts text to speech with selectable voice models.
- Adjustable speech speed.
- Option to download audio files.
- Models: `tts-1`, `tts-1-hd`.

### Transcription
- Converts audio to text.
- Supports multiple languages (ISO 639-1 codes).
- Various response formats: text, SRT, VTT, JSON, verbose JSON.
- Adjustable model creativity with temperature setting.

### Translation
- Translates English audio to other languages.
- Option for manual or generated context prompts.
- Downloadable translation files.

### User Dashboard
- Manage API keys: add, retest, select, delete.
- Update user information: username (7-day cooldown), password reset.
- Image history: view, download, delete.
- Document management: upload, edit metadata, delete.
- Edit and update utility settings and preferences.

## Listed Security Implements

### Authentication
- Flask-Login for user session and authentication management.
- Tracking of login attempts to prevent brute-force attacks.
- Account lockout after multiple failed login attempts.
- Email confirmation for new accounts to verify identity.

### Password Management
- Flask-Bcrypt for password hashing.
- Secure password reset with ItsDangerous for token generation and verification.
- Enforced password complexity during creation and reset.

### Session Management
- Flask-Login for user session handling with fresh login options.
- Secure session cookies with HTTPOnly and SameSite attributes.
- Configurable permanent session lifetime.
- Remember me functionality with secure cookies.

### Communication Security
- Flask-Mail with TLS for secure email communication.

### Database Security
- SQLAlchemy ORM to prevent SQL injection.
- Encrypted storage of API keys in the database.

### Configuration and Environment
- Separate configurations for development and production.
- Environment variables for sensitive data.
- SSH tunneling in development for secure database access.

### CSRF Protection
- Flask-WTF CSRF protection for forms.

### Secure Headers
- HTTPOnly and SameSite attributes for session and remember cookies.
- Configurable session lifetime and remember cookie duration.

### Code and Dependency Management
- Flask-Migrate for database schema migrations.
- Flask-CORS for Cross-Origin Resource Sharing control.