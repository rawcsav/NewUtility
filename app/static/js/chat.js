var chatBox = document.getElementById("chat-box");

function updateStatusMessage(message, type) {
  const statusElement = document.getElementById("conversation-history-status");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.classList.remove("error", "success");
    if (type === "success") {
      statusElement.classList.add("success");
    } else if (type === "error") {
      statusElement.classList.add("error");
    }

    setTimeout(() => {
      statusElement.textContent = "";
      statusElement.classList.remove("error", "success");
    }, 10000);
  }
}

function saveSystemPrompt(conversationId, newPrompt) {
  const payload = {
    system_prompt: newPrompt
  };

  fetch(`/chat/update-system-prompt/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken() // Ensure this function correctly retrieves the CSRF token
    },
    body: JSON.stringify(payload)
  })
    .then((response) => {
      if (!response.ok) {
        // Non-2xx HTTP status code response
        return response.json().then((data) => {
          // Assuming the server sends a JSON response with a 'message' field even on errors
          throw new Error(
            data.message || "HTTP error! Status: " + response.status
          );
        });
      }
      return response.json();
    })
    .then((data) => {
      if (data.status === "success") {
        console.log("System prompt updated successfully");
        updateStatusMessage("System prompt updated successfully", "success");
      } else {
        // Handle any other cases where the server indicates failure but doesn't throw an error
        console.error("Failed to update system prompt: " + data.message);
        updateStatusMessage(data.message, "error");
      }
    })
    .catch((error) => {
      // Handle network errors, parsing errors, and rejections from the server validation
      console.error("Failed to update system prompt: " + error.message);
      updateStatusMessage(error.message, "error");
    });
}

function toggleEditConvoTitle() {
  var titleInput = document.getElementById("editable-convo-title");
  titleInput.readOnly = !titleInput.readOnly;
  if (!titleInput.readOnly) {
    titleInput.focus();
  }
}

function saveConvoTitle(conversationId, newTitle) {
  const payload = {
    title: newTitle
  };

  fetch(`/chat/update-conversation-title/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken() // Ensure this function correctly retrieves the CSRF token
    },
    body: JSON.stringify(payload)
  })
    .then((response) => {
      if (!response.ok) {
        // Non-2xx HTTP status code response, try to parse and get error message
        return response.json().then((data) => {
          throw new Error(
            data.message || "HTTP error! Status: " + response.status
          );
        });
      }
      return response.json();
    })
    .then((data) => {
      if (data.status === "success") {
        console.log("Title updated successfully");
        updateStatusMessage("Title updated successfully", "success");

        // Update the conversation entry with the new title in the UI
        var conversationEntry = document.querySelector(
          `.conversation-entry[data-conversation-id="${conversationId}"]`
        );
        if (conversationEntry) {
          let textEntryElement = conversationEntry.querySelector(".text-entry");
          if (textEntryElement) {
            // Update the visible title in the conversation history
            textEntryElement.textContent = newTitle;
          }
          // Update the data-conversation-title attribute
          conversationEntry.setAttribute("data-conversation-title", newTitle);

          // Update the conversationHistory array with the new title, if it exists
          if (typeof conversationHistory !== "undefined") {
            let conversation = conversationHistory.find(
              (conv) => conv.id == conversationId
            );
            if (conversation) {
              conversation.title = newTitle;
            }
          }
        }
      } else {
        console.error("Failed to update title: " + data.message);
        updateStatusMessage(data.message, "error");
      }
    })
    .catch((error) => {
      // Handle network errors, parsing errors, and rejections from server validation
      console.error("Failed to update title: " + error.message);
      updateStatusMessage(error.message, "error");
    });
}

function setActiveButton(activeButtonId) {
  document.querySelectorAll(".options-button").forEach(function (button) {
    button.classList.remove("active");
  });

  var activeButton = document.getElementById(activeButtonId);
  if (activeButton) {
    activeButton.classList.add("active");
  }
}

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

function toggleHistory() {
  document.getElementById("conversation-container").style.display = "block";
  document.getElementById("preference-popup").style.display = "none";
  setActiveButton("show-history-btn");
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

    window.currentStreamContentDiv = document.createElement("div");

    var title = document.createElement("h5");

    if (
      window.currentStreamMessageDiv.classList.contains("assistant-message")
    ) {
      title.textContent = "Jack";
    } else if (
      window.currentStreamMessageDiv.classList.contains("user-message")
    ) {
      title.textContent = "User";
    }

    window.currentStreamMessageDiv.appendChild(title);
    window.currentStreamMessageDiv.appendChild(window.currentStreamContentDiv);
  }

  if (chunk != null) {
    window.incompleteMarkdownBuffer += chunk;

    window.currentStreamContentDiv.innerHTML = marked.parse(
      window.incompleteMarkdownBuffer
    );
  }

  hljs.highlightAll();
  chatBox.scrollTop = chatBox.scrollHeight;
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
  setActiveButton("show-preferences-btn");
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

  var title = document.createElement("h5");
  if (className === "assistant-message") {
    title.textContent = "Jack";
  } else if (className === "user-message") {
    title.textContent = "User";
  } else if (className === "system-message") {
    title.textContent = "System";
  }

  messageDiv.appendChild(title);

  if (message != null) {
    var messageContent = document.createElement("div");
    messageContent.innerHTML = DOMPurify.sanitize(marked.parse(message));

    // Make the system prompt editable when the icon is clicked
    if (className === "system-message") {
      var editIcon = document.createElement("i");
      editIcon.classList.add("fas", "fa-edit");
      editIcon.addEventListener("click", function () {
        messageContent.contentEditable = "true";
        messageContent.focus();
      });

      messageContent.addEventListener("blur", function () {
        messageContent.contentEditable = "false";
        // Get the conversation ID
        var conversationId = document
          .getElementById("convo-title")
          .getAttribute("data-conversation-id");
        // Save the changes to the database
        saveSystemPrompt(conversationId, messageContent.textContent);
      });

      messageContent.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          this.blur();
        }
      });

      messageDiv.appendChild(editIcon);
    }

    messageDiv.appendChild(messageContent);
  }

  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
  hljs.highlightAll();
}

function selectConversation(conversationId) {
  var conversationEntry = document.querySelector(
    `.conversation-entry[data-conversation-id="${conversationId}"]`
  );

  if (conversationEntry && conversationEntry.dataset.conversationTitle) {
    var convoTitleElement = document.getElementById("convo-title");
    if (convoTitleElement) {
      convoTitleElement.textContent =
        conversationEntry.dataset.conversationTitle;
      convoTitleElement.setAttribute("data-conversation-id", conversationId);
    }
  }

  chatBox.innerHTML = "";

  fetch(`/chat/conversation/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then((response) => response.json())
    .then((data) => {
      data.messages.forEach((message) => {
        appendMessageToChatBox(message.content, message.className);
      });
      // Update the hidden input field for conversation_id
      var completionConversationIdInput = document.getElementById(
        "completion-conversation-id"
      );
      if (completionConversationIdInput) {
        completionConversationIdInput.value = conversationId;
      }
    })
    .catch((error) => console.error("Error:", error));
}

function deleteConversation(conversationId) {
  var allConversations = document.querySelectorAll(".conversation-entry");

  // Check if there's only one conversation left
  if (allConversations.length <= 1) {
    updateStatusMessage("Cannot delete the last conversation.", "error");
    return;
  }

  if (!confirm("Are you sure you want to delete this conversation?")) {
    return;
  }

  fetch(`/chat/delete-conversation/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken()
    },
    credentials: "same-origin"
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        // Remove the conversation from the list
        var entry = document.querySelector(
          `.conversation-entry[data-conversation-id="${conversationId}"]`
        );
        if (entry) {
          entry.remove();
        }
        updateStatusMessage("Conversation deleted successfully.", "success");
      } else {
        // Handle error case
        updateStatusMessage("Failed to delete conversation.", "error");
      }
    })
    .catch((error) => {
      // Handle error case
      updateStatusMessage("Error: " + error.message, "error");
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
  var convoTitleElement = document.getElementById("convo-title");
  if (convoTitleElement) {
    convoTitleElement.addEventListener("blur", function () {
      var conversationId = this.getAttribute("data-conversation-id");
      var newTitle = this.textContent.trim();

      if (newTitle.length >= 1 && newTitle.length <= 25) {
        saveConvoTitle(conversationId, newTitle);
      } else {
        updateStatusMessage(
          "Conversation title must be between 1 and 25 characters.",
          "error"
        );
        this.textContent = this.getAttribute("data-conversation-title");
      }
    });

    convoTitleElement.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        this.blur();
      }
    });
  }

  convoTitleElement.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      this.blur();
    }
  });

  function fadeOutTooltip(tooltip) {
    tooltip.style.opacity = "0";
    tooltip.style.transition = "opacity 0.5s ease-out";
    setTimeout(() => {
      tooltip.style.visibility = "hidden";
    }, 500);
  }

  function hideAllTooltips(exceptId) {
    let tooltipTexts = document.querySelectorAll(".tooltip-text");
    tooltipTexts.forEach((tooltip) => {
      if (tooltip.getAttribute("data-info-id") !== exceptId) {
        fadeOutTooltip(tooltip);
      }
    });
  }

  let infoIcons = document.querySelectorAll(".info-icon");
  infoIcons.forEach((icon) => {
    icon.addEventListener("click", function (event) {
      event.stopPropagation();

      let tooltipText = this.nextElementSibling;

      hideAllTooltips(tooltipText.getAttribute("data-info-id"));

      if (tooltipText.style.opacity === "1") {
        fadeOutTooltip(tooltipText);
      } else {
        tooltipText.style.visibility = "visible";
        tooltipText.style.opacity = "1";
        tooltipText.style.transition = "opacity 0.5s ease-in";
      }
    });
  });

  let tooltipTexts = document.querySelectorAll(".tooltip-text");
  tooltipTexts.forEach((tooltip) => {
    tooltip.addEventListener("click", function (event) {
      event.stopPropagation();
      fadeOutTooltip(this);
    });
  });

  window.addEventListener("click", function () {
    hideAllTooltips();
  });

  function checkConversationHistory() {
    if (conversationHistory && conversationHistory.length > 0) {
      var mostRecentConversation =
        conversationHistory[conversationHistory.length - 1];
      selectConversation(mostRecentConversation.id);
      conversationHistory.forEach(function (message) {
        appendMessageToChatBox(message.content, message.className);
      });
    } else {
      newConversationForm.style.display = "block";
      chatCompletionForm.style.display = "none";
    }
  }

  document.getElementById("model").addEventListener("change", function () {
    var selectedModel = this.value;
    var maxTokensSlider = document.getElementById("max_tokens");
    var maxTokensValueInput = document.getElementById("max-tokens-value");
    maxTokensSlider.max = modelMaxTokens[selectedModel];
    maxTokensSlider.value = modelMaxTokens[selectedModel];
    maxTokensValueInput.value = maxTokensSlider.value;
  });

  if (chatCompletionForm) {
    chatCompletionForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var messageToSend = messageInput.value;
      var formData = new FormData(chatCompletionForm);
      formData.append("prompt", messageToSend);

      appendMessageToChatBox(messageToSend, "user-message");

      messageInput.value = "";
      fetch("/chat/completion", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken()
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
                  finalizeStreamedResponse();
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
      e.preventDefault();
      var formData = new FormData(newConversationForm);

      fetch("/chat/new-conversation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken()
        },
        credentials: "same-origin",
        body: JSON.stringify(Object.fromEntries(formData))
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            const newConversationId = data.conversation_id;
            const newConversationPrompt = data.system_prompt;
            const newConversationTitle = data.title;
            const createdAt = data.created_at;

            conversationHistory.push({
              id: newConversationId,
              title: newConversationTitle,
              created_at: createdAt,
              system_prompt: newConversationPrompt
            });

            const conversationHistoryDiv = document.getElementById(
              "conversation-history"
            );
            const newConvoEntry = document.createElement("div");
            newConvoEntry.classList.add("conversation-entry");
            newConvoEntry.setAttribute(
              "data-conversation-id",
              newConversationId
            );
            newConvoEntry.setAttribute(
              "data-conversation-title",
              newConversationTitle
            ); // Set the title attribute

            newConvoEntry.addEventListener("click", function () {
              selectConversation(newConversationId);
            });

            newConvoEntry.innerHTML = `<p class="text-entry">${newConversationTitle}</p> <span class="delete-conversation" onclick="deleteConversation(${newConversationId})"><i class="fas fa-trash-alt"></i></span>`;
            conversationHistoryDiv.appendChild(newConvoEntry);
            chatBox.innerHTML = "";
            selectConversation(newConversationId);
            updateStatusMessage("New conversation started.", "success");
          } else if (data.status === "limit-reached") {
            updateStatusMessage(data.message, "error");
          } else {
            updateStatusMessage(data.message, "error");
          }
        })
        .catch((error) => {
          updateStatusMessage("Error: " + error.message, "error");
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
          "X-CSRFToken": getCsrfToken()
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
          updatePreferencMessages("Error: " + error, "error");
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
