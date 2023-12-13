function toggleHistory() {
  document.getElementById("conversation-history").style.display = "block";
  document.getElementById("preference-popup").style.display = "none";
}

// Function to handle appending streamed responses
function appendStreamedResponse(chunk, chatBox) {
  // Create a message element for the stream if it does not exist
  if (!window.currentStreamMessageDiv) {
    window.currentStreamMessageDiv = document.createElement("div");
    window.currentStreamMessageDiv.classList.add("message", "system-message");
    chatBox.appendChild(window.currentStreamMessageDiv);
  }

  // Append new text chunk to the current message element
  window.currentStreamMessageDiv.textContent += chunk;
  chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom of the chat box
}

// Function to finalize the streamed response
function finalizeStreamedResponse() {
  window.currentStreamMessageDiv = null; // Clear the reference to the message element
}

function togglePreferences() {
  document.getElementById("conversation-history").style.display = "none";
  document.getElementById("preference-popup").style.display = "block";
}

function updatePreferenceMessages(message, status) {
  var messageDiv = document.getElementById("preference-messages");
  messageDiv.textContent = message;
  messageDiv.className = status;
}

function togglePreferencePopup() {
  var popup = document.getElementById("preference-popup");
  popup.classList.toggle("show");
}

function appendMessageToChatBox(message, className) {
  var messageDiv = document.createElement("div");
  messageDiv.classList.add("message", className);
  messageDiv.textContent = message;
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function selectConversation(conversationId) {
  var conversationIdInput = document.getElementById(
    "completion-conversation-id"
  );
  if (conversationIdInput) {
    conversationIdInput.value = conversationId;
  }
}

const modelMaxTokens = {
  "gpt-4-1106-preview": 128000,
  "gpt-4-vision-preview": 128000,
  "gpt-4": 8192,
  "gpt-4-32k": 32768,
  "gpt-4-0613": 8192,
  "gpt-4-32k-0613": 32768,
  "gpt-4-0314": 8192,
  "gpt-4-32k-0314": 32768,
  "gpt-3.5-turbo-1106": 16385,
  "gpt-3.5-turbo": 4096,
  "gpt-3.5-turbo-16k": 16385
};

document.addEventListener("DOMContentLoaded", function () {
  var chatBox = document.getElementById("chat-box");
  var messageInput = document.getElementById("message-input");
  var newConversationForm = document.getElementById("new-conversation-form");
  var chatCompletionForm = document.getElementById("chat-completion-form");
  var updatePreferencesForm = document.getElementById(
    "update-preferences-form"
  );

  // Utility function to append messages to the chat box
  function appendMessageToChatBox(message, className) {
    var messageDiv = document.createElement("div");
    messageDiv.classList.add("message", className);
    messageDiv.textContent = message;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Call toggleHistory on page load to show conversation history first

  function checkConversationHistory() {
    if (conversationHistory && conversationHistory.length > 0) {
      // Set the completion-conversation-id to the most recent conversation ID
      var mostRecentConversation =
        conversationHistory[conversationHistory.length - 1];
      selectConversation(mostRecentConversation.id); // Ensure 'id' matches your data structure

      // Append historical messages to the chat box
      conversationHistory.forEach(function (message) {
        appendMessageToChatBox(message.content, message.className); // Ensure 'content' and 'className' match your data structure
      });
    } else {
      // No historical conversations, switch to the new conversation system prompt
      messageInput.placeholder =
        "Enter system prompt to start a new conversation...";
      newConversationForm.style.display = "block";
      chatCompletionForm.style.display = "none";
    }
  }

  document.getElementById("model").addEventListener("change", function () {
    var selectedModel = this.value;
    var maxTokensSlider = document.getElementById("max_tokens");
    var maxTokensValueInput = document.getElementById("max-tokens-value");
    maxTokensSlider.max = modelMaxTokens[selectedModel];
    maxTokensSlider.value = modelMaxTokens[selectedModel]; // Set to max or a default value within the range
    maxTokensValueInput.value = maxTokensSlider.value; // Update the output display
  });

  if (chatCompletionForm) {
    chatCompletionForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var messageToSend = messageInput.value;
      var formData = new FormData(chatCompletionForm);
      formData.append("prompt", messageToSend);

      // Display the outgoing message immediately
      appendMessageToChatBox(messageToSend, "user-message");

      messageInput.value = ""; // Clear the input field

      fetch("/chat/completion", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": formData.get("csrf_token")
        },
        credentials: "same-origin",
        body: JSON.stringify(Object.fromEntries(formData))
      })
        .then((response) => {
          const contentType = response.headers.get("Content-Type");
          if (contentType && contentType.includes("text/plain")) {
            const reader = response.body.getReader();
            reader
              .read()
              .then(function processText({ done, value }) {
                if (done) {
                  finalizeStreamedResponse(); // Finalize the message when the streaming is done
                  return;
                }
                var chunk = new TextDecoder().decode(value);
                // Check if the chunk starts with a JSON structure for an error message
                if (chunk.startsWith("{") && chunk.endsWith("}\n\n")) {
                  try {
                    // Parse the JSON chunk to check for errors
                    var jsonChunk = JSON.parse(chunk.trim());
                    if (jsonChunk.status === "error") {
                      // Display the error message
                      appendMessageToChatBox(
                        jsonChunk.message,
                        "error-message"
                      );
                    }
                  } catch (error) {
                    // Handle errors that occur while parsing the JSON chunk
                    appendMessageToChatBox(
                      "Error parsing streamed response: " + error.message,
                      "error-message"
                    );
                    console.error("Error parsing streamed response:", error);
                  }
                } else {
                  // Append normal content to the chat box
                  appendStreamedResponse(chunk, chatBox);
                }
                return reader.read().then(processText);
              })
              .catch((streamError) => {
                // Handle errors that occur during reading the stream
                appendMessageToChatBox(
                  "Streaming Error: " + streamError.message,
                  "error-message"
                );
                console.error("Streaming error:", streamError);
              });
          } else {
            // Handle non-streaming response
            return response.json();
          }
        })
        .then((data) => {
          if (data && data.status === "success") {
            // Display the AI's response
            appendMessageToChatBox(data.message, "system-message");
          } else if (data && data.status === "error") {
            // Display the error message
            appendMessageToChatBox(data.message, "error-message");
          }
        })
        .catch((error) => {
          // Display the error message if the fetch fails
          appendMessageToChatBox(
            "Fetch Error: " + error.message,
            "error-message"
          );
          console.error("Fetch error:", error);
        });
    });
  }

  if (updatePreferencesForm) {
    updatePreferencesForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var formData = new FormData(updatePreferencesForm);
      fetch("/chat/update-preferences", {
        method: "POST",
        headers: {
          "X-CSRFToken": formData.get("csrf_token")
        },
        body: formData
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            updatePreferenceMessages(data.message, "success");
          } else {
            updatePreferenceMessages(data.message, "error");
            console.error(data.errors);
          }
        })
        .catch((error) => {
          updateApiKeyMessages("Error: " + error, "error");
        });
    });
  }
  window.onclick = function (event) {
    var popup = document.getElementById("preference-popup");
    if (event.target == popup) {
      popup.classList.remove("show");
    }
  };
  toggleHistory();
  checkConversationHistory();
});
