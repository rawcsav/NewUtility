## User Dashboard and Utilities Guide


The dashboard is the central hub for managing your account, API keys, images, documents, and chat preferences. Access the dashboard by navigating to `/user/dashboard` after logging in.

### API Key Management

#### Adding a New API Key

- To add a new API key, fill out the form in the **Key Management** section.
- Enter the API key in the designated field and provide a nickname for easy identification.
- Click "Save" to store the API key. It will be tested for validity and available models.

#### Retesting an API Key

- If an API key needs revalidation, use the refresh icon next to the key in the list.
- The system will retest the key and update its status.

#### Deleting an API Key

- To delete an API key, click the trash icon next to the key you wish to remove.
- The key will be marked for deletion and removed from active use.

#### Selecting an API Key

- Click the hand pointer icon to select an API key as your active key for generating content.

### User Information and Preferences

#### Changing Username

- Change your username by entering a new one in the **User Info** section and clicking "Submit".
- Usernames can only be changed once every 7 days.

#### Resetting Password

- Reset your password by clicking the "Reset Password" link in the **User Change** section.

### Image History and Management

#### Viewing Image History

- The **Img History** section displays thumbnails of your most recent images.
- Click on an image to view options for downloading or deleting.

#### Downloading Images

- Click the download icon to save an image to your device.
- Images are served from the `/static/user_files/temp_img/` directory.

#### Deleting Images

- Click the trash icon to mark an image for deletion.
- The image will be flagged in the database and no longer displayed in your history.

### Utility Settings

Provides a quick way to edit essential settings for various utilities, more in-depth explanations available on the respective utility pages.
#### Editing Documents

- Click the edit icon next to a document to modify its title or author.
- Save changes by clicking the save icon.
- Remove a document by clicking the trash icon next to it.


#### Chat Preferences
- Open the chat preferences by clicking the speech bubble icon in the **Utility Settings** section.
- Adjust settings like model, temperature, max tokens, frequency penalty, and presence penalty using the provided form.
- Click "Update Preferences" to save your changes.

#### Knowledge Retrieval Settings
- In the **Knowledge Retrieval** section, select documents to include as context for chat conversations.
- Adjust the context token percentage to control how much of the document content the AI considers.
- Save your preferences by clicking the "Save Preferences" button.

### Utility Navigation

- Use the **Utilities** section to quickly navigate to all primary features.