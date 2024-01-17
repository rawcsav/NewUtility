## Getting Started with Chat Utilities

- **Starting a Conversation**: To begin chatting with the AI, type your message into the text box at the bottom of the chat window and click the send icon (paper airplane) or press "Enter" on your keyboard. The AI will process your input and provide a response.
- **Viewing Conversation History**: Click on the history icon (clockwise arrow forming a circle) to view past conversations. You can click on any previous conversation to continue from where you left off.
- **Interrupting the AI**: If the AI is generating a long response and you wish to interrupt it, click the pause icon (two vertical bars) to stop the response.

## Managing Conversations

- **Editing a Conversation Title**: To edit the title of a conversation, click the edit icon (pencil) next to the conversation title in the history view. After making changes, press "Enter" or click outside the text box to save.
- **Deleting a Conversation**: To delete a conversation, click the trash icon (trash can) next to the conversation you wish to remove. Confirm the deletion when prompted to ensure you do not accidentally lose important conversations.

## Customizing Chat Preferences

- **Accessing Preferences**: Click the settings icon (gear) to open the preferences panel where you can customize your chat experience.
- **Model Selection**: Choose the AI model you want to interact with. Different models may have different capabilities and limitations.
- **Temperature**: This setting controls the randomness of the AI's responses. A lower temperature (closer to 0) will make the AI's responses more deterministic and predictable, while a higher temperature (closer to 1) will make them more random and varied.
- **Max Tokens**: Set the maximum number of tokens (pieces of text) that the AI can generate in a single response. A higher number allows for longer responses, while a lower number restricts the AI to shorter replies.
- **Top P (Nucleus Sampling)**: This parameter controls the diversity of the AI's responses by only considering the top P percent of probability mass when generating each token. Lower values can lead to more focused responses, while higher values allow for more varied outputs.
- **Frequency Penalty**: Adjust how much the AI should avoid repeating itself. A positive value discourages repetition, while a negative value makes repetition more likely.
- **Presence Penalty**: This setting influences whether the AI should bring up new topics. A positive value encourages the AI to introduce new content, while a negative value makes it more likely to stay on the current topic.
- **Saving Preferences**: After adjusting the settings to your liking, click the "Update Preferences" button to save your changes. These preferences will be applied to future conversations.

## Using Documents in Chat

- **Selecting Documents**: If you have uploaded documents to be embedded, you can include them as context for the AI. Check the boxes next to the documents you want to use in the chat.
- **Knowledge Query**: Adjust the slider to set the percentage of context tokens from your selected documents that the AI should consider when generating responses.
- **Saving Document Preferences**: Click the "Save Preferences" button to apply your document selections to the chat.
- **Important Caveat**: Any knowledge queries made within a conversation will not be saved into the conversation history as such. Thus, you will not be able to ask a subsequent question about the documents from a previous query without keeping the mode enabled and having it refresh the context for the present query.

## Uploading Images (if supported by the model)

- **Uploading an Image**: Click the image icon (picture frame) to upload an image from your computer. This is a bit finicky still in terms of differentiating between web URLs and user uploads, but it does work to some degree.
- **Important Caveat**: Unlike document queries, images are in fact saved into the conversation history and can be discussed/mentioned in subsequent messages. However, changing the model away from one with image capabilities will remove the image context from the conversation.