var chatBox = document.getElementById("chat-box");

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

function toggleHistory() {
  document.getElementById("conversation-container").style.display = "block";
  document.getElementById("preference-popup").style.display = "none";
}

function appendStreamedResponse(chunk, chatBox) {
  if (!window.currentStreamMessageDiv) {
    window.currentStreamMessageDiv = document.createElement("div");
    window.currentStreamMessageDiv.classList.add(
      "message",
      "assistant-message"
    );
    chatBox.appendChild(window.currentStreamMessageDiv);
    window.incompleteMarkdownBuffer = "";

    // Create a container for the message content
    window.currentStreamContentDiv = document.createElement("div");

    // Create a title element
    var title = document.createElement("h5");

    // Set the title text based on the message's class name
    if (
      window.currentStreamMessageDiv.classList.contains("assistant-message")
    ) {
      title.textContent = "Jack";
    } else if (
      window.currentStreamMessageDiv.classList.contains("user-message")
    ) {
      title.textContent = "User";
    }

    // Append the title to the message div
    window.currentStreamMessageDiv.appendChild(title);
    // Append the content container to the message div
    window.currentStreamMessageDiv.appendChild(window.currentStreamContentDiv);
  }

  // Combine the new chunk with any incomplete Markdown from the previous chunk
  window.incompleteMarkdownBuffer += chunk;

  // Convert the combined Markdown chunk to HTML using marked.js
  // Note: We are not sanitizing here to avoid breaking HTML structure with partial data
  window.currentStreamContentDiv.innerHTML = marked.parse(
    window.incompleteMarkdownBuffer
  );
  hljs.highlightAll();
  chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom of the chat box
}

function finalizeStreamedResponse() {
  if (window.currentStreamMessageDiv) {
    window.currentStreamMessageDiv.innerHTML = DOMPurify.sanitize(
      window.currentStreamMessageDiv.innerHTML
    );

    window.currentStreamMessageDiv = null;
    window.incompleteMarkdownBuffer = "";
  }
}

function togglePreferences() {
  document.getElementById("conversation-container").style.display = "none";
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

  // Create a title element
  var title = document.createElement("h5");
  // Set the title text based on the message's class name
  if (className === "assistant-message") {
    title.textContent = "Jack";
  } else if (className === "user-message") {
    title.textContent = "User";
  }

  // Append the title to the message div
  messageDiv.appendChild(title);

  // Convert Markdown to HTML using marked.js
  var messageContent = document.createElement("div");
  messageContent.innerHTML = DOMPurify.sanitize(marked.parse(message));

  // Append the message content to the message div
  messageDiv.appendChild(messageContent);

  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the bottom of the chat box

  hljs.highlightAll();
}

function selectConversation(conversationId) {
  var conversationIdInput = document.getElementById(
    "completion-conversation-id"
  );
  if (conversationIdInput) {
    conversationIdInput.value = conversationId;
  }

  // Clear the chat box
  chatBox.innerHTML = "";

  // Fetch the messages for the selected conversation
  fetch(`/chat/conversation/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then((response) => response.json())
    .then((data) => {
      // Append each message to the chat box
      data.messages.forEach((message) => {
        appendMessageToChatBox(message.content, message.className);
      });
    })
    .catch((error) => console.error("Error:", error));
}

function deleteConversation(conversationId) {
  const statusMessageDiv = document.getElementById(
    "conversation-history-status"
  );
  statusMessageDiv.textContent = ""; // Clear any previous messages
  statusMessageDiv.className = "";

  if (!confirm("Are you sure you want to delete this conversation?")) {
    return;
  }

  fetch(`/chat/delete-conversation/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken() // Include the CSRF token here
    },
    credentials: "same-origin"
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        // Remove the conversation entry from the DOM
        var entry = document.querySelector(
          `.conversation-entry[data-conversation-id="${conversationId}"]`
        );
        if (entry) {
          entry.remove();
          // Display a success message
          statusMessageDiv.textContent = "Conversation deleted successfully.";
          statusMessageDiv.className = "success"; // Use your CSS class for success messages
        }
      } else {
        // Display an error message
        statusMessageDiv.textContent =
          "Failed to delete the conversation: " + data.message;
        statusMessageDiv.className = "error"; // Use your CSS class for error messages
      }
    })
    .catch((error) => {
      // Display an error message
      statusMessageDiv.textContent = "Error deleting conversation: " + error;
      statusMessageDiv.className = "error"; // Use your CSS class for error messages
    });
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
  var messageInput = document.getElementById("message-input");
  var newConversationForm = document.getElementById("new-conversation-form");
  var chatCompletionForm = document.getElementById("chat-completion-form");
  var updatePreferencesForm = document.getElementById(
    "update-preferences-form"
  );

  // Function to fade out tooltips
  // Function to fade out tooltips
  function fadeOutTooltip(tooltip) {
    tooltip.style.opacity = "0";
    tooltip.style.transition = "opacity 0.5s ease-out";
    // Set a timeout to change visibility after the opacity transition
    setTimeout(() => {
      tooltip.style.visibility = "hidden";
    }, 500); // This should match the transition duration
  }

  // Function to hide all tooltips
  function hideAllTooltips(exceptId) {
    let tooltipTexts = document.querySelectorAll(".tooltip-text");
    tooltipTexts.forEach((tooltip) => {
      // Fade out all tooltips except the one that should remain open
      if (tooltip.getAttribute("data-info-id") !== exceptId) {
        fadeOutTooltip(tooltip);
      }
    });
  }

  // Add click event listener to each info icon
  let infoIcons = document.querySelectorAll(".info-icon");
  infoIcons.forEach((icon) => {
    icon.addEventListener("click", function (event) {
      // Prevent the click event from triggering any parent element's click event
      event.stopPropagation();

      let tooltipText = this.nextElementSibling;

      // Hide all other tooltips except this one
      hideAllTooltips(tooltipText.getAttribute("data-info-id"));

      // Toggle the visibility of this tooltip text
      if (tooltipText.style.opacity === "1") {
        fadeOutTooltip(tooltipText);
      } else {
        tooltipText.style.visibility = "visible";
        tooltipText.style.opacity = "1";
        tooltipText.style.transition = "opacity 0.5s ease-in";
      }
    });
  });

  // Add click event listener to each tooltip text
  let tooltipTexts = document.querySelectorAll(".tooltip-text");
  tooltipTexts.forEach((tooltip) => {
    tooltip.addEventListener("click", function (event) {
      // Stop the propagation to prevent triggering the click event on the window
      event.stopPropagation();
      fadeOutTooltip(this); // Fade out this tooltip
    });
  });

  // Global click event to hide tooltips when clicking anywhere else
  window.addEventListener("click", function () {
    hideAllTooltips(); // Hide all tooltips
  });

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

  // Inside the 'DOMContentLoaded' event listener
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
          "X-CSRFToken": getCsrfToken() // Include the CSRF token here
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

                if (chunk.startsWith("An error occurred:")) {
                  appendMessageToChatBox(chunk, "error-message");
                } else {
                  appendStreamedResponse(chunk, chatBox);
                }
                return reader.read().then(processText);
              })
              .catch((streamError) => {
                appendMessageToChatBox(
                  "Streaming Error: " + streamError.message,
                  "error-message"
                );
                console.error("Streaming error:", streamError);
              });
          } else {
            return response.text().then((text) => {
              if (text.includes("An error occurred:")) {
                appendMessageToChatBox(text, "error-message");
              } else {
                try {
                  const data = JSON.parse(text);
                  appendMessageToChatBox(data.message, "assistant-message");
                } catch (e) {
                  appendMessageToChatBox(
                    "Unexpected response format: " + text,
                    "error-message"
                  );
                }
              }
            });
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
  if (newConversationForm) {
    newConversationForm.addEventListener("submit", function (e) {
      e.preventDefault(); // Prevent default form submission

      // Gather form data to send
      var formData = new FormData(newConversationForm);

      // Send AJAX request to create a new conversation
      fetch("/chat/new-conversation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken() // Include the CSRF token here
        },
        credentials: "same-origin",
        body: JSON.stringify(Object.fromEntries(formData))
      })
        .then((response) => response.json())
        .then((data) => {
          const statusMessageDiv = document.getElementById(
            "conversation-history-status"
          );
          if (data.status === "success") {
            // Handle successful conversation creation
            const newConversationId = data.conversation_id;
            const newConversationPrompt = data.system_prompt;
            const newConversationTitle = data.title; // Assuming the title is included in the response
            const createdAt = data.created_at; // Assuming created_at is included in the response

            // Clear the chat box and set the new conversation as active
            chatBox.innerHTML = "";
            selectConversation(newConversationId);

            // Update conversationHistory variable
            conversationHistory.push({
              id: newConversationId,
              title: newConversationTitle,
              created_at: createdAt,
              system_prompt: newConversationPrompt
            });

            // Update conversation history in the HTML
            const conversationHistoryDiv = document.getElementById(
              "conversation-history"
            );
            const newConvoEntry = document.createElement("div");
            newConvoEntry.classList.add("conversation-entry");
            newConvoEntry.setAttribute(
              "data-conversation-id",
              newConversationId
            );

            newConvoEntry.addEventListener("click", function () {
              selectConversation(newConversationId);
            });

            newConvoEntry.innerHTML = `${newConversationTitle} - ${createdAt} <span class="delete-conversation" onclick="deleteConversation(${newConversationId})"><i class="fas fa-trash-alt"></i></span>`;
            conversationHistoryDiv.appendChild(newConvoEntry);
            statusMessageDiv.textContent = "";
            // Display a success message
            statusMessageDiv.textContent =
              "New conversation created successfully!";
            statusMessageDiv.className = "success"; // Use your CSS class for success messages
          } else if (data.status === "limit-reached") {
            // Inform the user they've hit the limit
            statusMessageDiv.textContent = data.message;
            statusMessageDiv.className = "error"; // Use your CSS class for error messages
          } else {
            // Handle any other errors
            statusMessageDiv.textContent =
              "Failed to start a new conversation: " + data.message;
            statusMessageDiv.className = "error"; // Use your CSS class for error messages
          }
        })
        .catch((error) => {
          // Handle the error case, such as displaying a message to the user
          statusMessageDiv.textContent = "Error: " + error.message;
          statusMessageDiv.className = "error-message"; // Use your CSS class for error messages
          console.error("New conversation error:", error);
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
          "X-CSRFToken": getCsrfToken() // Include the CSRF token here
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
