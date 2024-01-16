## Getting Started with Image Utilities

### Text-to-Speech (TTS)

The TTS utility converts written text into spoken words. You can use this feature to generate audio from text for various purposes, such as creating voiceovers or aiding those with visual impairments.

#### Usage

- **Accessing TTS**: Click on the microphone icon to open the TTS utility.
- **Input Text**: Enter the text you wish to convert into speech in the provided text box (maximum of 4096 characters).
- **Generate Speech**: Click the "Generate Speech" button to create the audio file.
- **Download**: Once the audio is generated, access the job in the history model for detailed info and a download link.

#### TTS Preferences

- **Model**: Select the desired voice model from the dropdown menu.
  - For real-time applications, the standard tts-1 model provides the lowest latency but at a lower quality than the tts-1-hd model. Due to the way the audio is generated, tts-1 is likely to generate content that has more static in certain situations than tts-1-hd .
- **Voice**: Choose the voice you prefer from the available options.
- **Speed**: Adjust the speed of speech using the slider or input box.
- **Save Preferences**: Click "Save TTS Preferences" to apply your settings.

### Transcription

The transcription utility converts spoken words from an audio file into written text. This is useful for creating transcripts of recordings, meetings, or interviews.

#### Usage

- **Accessing Transcription**: Click on the file audio icon to open the transcription utility.
- **Upload File**: Click "Choose File" to select the audio file you want to transcribe.
  - Maximum file size should strive to be under 25mb or parts may be inaccurately concatenated. Especially if using SRT or VTT as response format.
- **Prompt Option**: Choose between a manual or generated prompt for the transcription.
  - For transcription and translation, a prompt is 'an optional text to guide the model's style or continue a previous audio segment. The prompt should match the audio language.'
  - You can either submit no prompt, a purely manual one, or you can provide the general context of the audio and a prompt can be generated for you.
- **Transcribe**: Click the "Transcribe" button to start the transcription process.
- **Download**: After transcription, access the job in the history model for detailed info and a download link. May need to refresh for updates.

#### Transcription Preferences

- **Model**: Select the transcription model from the dropdown menu.
  - Only the `whisper-1` model is available at this time.
- **Language**: Choose the language of the audio file.
  - Whisper is capable of transcribing audio in a host of languages (identified using ISO 639-1 codes). By identifying the language of the input audio file, it improves its overall understanding.
- **Response Format**: Select the desired format for the transcription output.
  - Options include plain text, SRT, and VTT, json, and verbose json. SRT and VTT are subtitle formats that include timestamps. Verbose json contains lots of specifically detailed data returned by the API alongside the output content.
- **Temperature**: Adjust the creativity level of the transcription using the slider.
  - If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.
- **Save Preferences**: Click "Save Whisper Preferences" to apply your settings.

### Translation

The translation utility allows you to translate spoken words from an audio file into another language, which is beneficial for understanding content in foreign languages.

**Note**: These definitions are all of the same type and behave the same as the ones outlined above. For more information, please refer to the transcription section.

#### Usage

- **Accessing Translation**: Click on the language icon to open the translation utility.
- **Upload File**: Click "Choose File" to select the audio file you want to translate.
- **Caveat**: The translation model is only capable of translating audio in English, so ironically there is no language option to define here.
- **Prompt Option**: Choose between a manual or generated prompt for the translation.
- **Translate**: Click the "Translate" button to start the translation process.
- **Download**: After translation, access the job in the history model for detailed info and a download link. May need to refresh for updates.

### History Section

The history section displays a list of your past jobs for TTS, transcription, and translation. You can view details and download the outputs of completed jobs.

- **Viewing History**: Click on the respective history tab to see your past jobs.
- **Details**: Click on a job entry to expand and view more details.
- **Download**: Use the download link to save the output files to your device.

