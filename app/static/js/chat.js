var chatBox = document.getElementById("chat-box");

hljs.configure({
  ignoreUnescapedHTML: true
});

function toggleHistory() {
  document.getElementById("conversation-container").style.display = "block";
  document.getElementById("preference-popup").style.display = "none";
  setActiveButton("show-history-btn");
}

function updateStatusMessage(message, type) {
  const statusElement = document.getElementById("conversation-history-status");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = type; // 'error' or 'success'

    setTimeout(() => {
      statusElement.textContent = "";
      statusElement.className = "";
    }, 10000);
  }
}

function performFetch(url, payload) {
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken()
    },
    body: JSON.stringify(payload)
  });
}

function handleFetchResponse(response, successMessage) {
  if (!response.ok) {
    throw new Error(response.statusText || "HTTP error!");
  }
  return response.json().then((data) => {
    if (data.status === "success") {
      console.log(successMessage);
      updateStatusMessage(successMessage, "success");
    } else {
      throw new Error(data.message);
    }
  });
}

function saveSystemPrompt(conversationId, newPrompt) {
  performFetch(`/chat/update-system-prompt/${conversationId}`, {
    system_prompt: newPrompt
  })
    .then((response) =>
      handleFetchResponse(response, "System prompt updated successfully")
    )
    .catch((error) => {
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
  performFetch(`/chat/update-conversation-title/${conversationId}`, {
    title: newTitle
  })
    .then((response) =>
      handleFetchResponse(response, "Title updated successfully")
    )
    .then(() => updateConversationUI(conversationId, newTitle))
    .catch((error) => {
      console.error("Failed to update title: " + error.message);
      updateStatusMessage(error.message, "error");
    });
}

function updateConversationUI(conversationId, newTitle) {
  var conversationEntry = document.querySelector(
    `.conversation-entry[data-conversation-id="${conversationId}"]`
  );
  if (conversationEntry) {
    let textEntryElement = conversationEntry.querySelector(".text-entry");
    if (textEntryElement) {
      textEntryElement.textContent = newTitle;
    }
    conversationEntry.setAttribute("data-conversation-title", newTitle);

    if (typeof conversationHistory !== "undefined") {
      let conversation = conversationHistory.find(
        (conv) => conv.id == conversationId
      );
      if (conversation) {
        conversation.title = newTitle;
      }
    }
  }
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

function appendStreamedResponse(chunk, chatBox, isUserMessage = false) {
  // Create message container if it doesn't exist
  if (!window.currentStreamMessageDiv) {
    window.currentStreamMessageDiv = createStreamMessageDiv(isUserMessage);
    chatBox.appendChild(window.currentStreamMessageDiv);
  }

  if (chunk != null) {
    // Buffer for incomplete Markdown content
    window.incompleteMarkdownBuffer += chunk;

    // Update message content based on the source
    updateStreamMessageContent(isUserMessage);
  }

  chatBox.scrollTop = chatBox.scrollHeight;
}

function createStreamMessageDiv(isUserMessage) {
  let messageDiv = document.createElement("div");
  messageDiv.classList.add(
    "message",
    isUserMessage ? "user-message" : "assistant-message"
  );

  let title = document.createElement("h5");
  title.textContent = isUserMessage ? "User" : "Jack";
  messageDiv.appendChild(title);

  let contentDiv = document.createElement("div");
  messageDiv.appendChild(contentDiv);
  window.currentStreamContentDiv = contentDiv;

  window.incompleteMarkdownBuffer = "";
  return messageDiv;
}

function updateStreamMessageContent(isUserMessage) {
  if (isUserMessage) {
    window.currentStreamContentDiv.textContent += chunk;
  } else {
    window.currentStreamContentDiv.innerHTML = marked.parse(
      window.incompleteMarkdownBuffer
    );
    applySyntaxHighlighting(window.currentStreamContentDiv);
  }
}

function applySyntaxHighlighting(element) {
  element.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightBlock(block);
  });
}

function finalizeStreamedResponse(isUserMessage = false) {
  if (window.currentStreamMessageDiv) {
    // Assuming the first <div> inside currentStreamMessageDiv contains the message content
    let messageContentDiv = window.currentStreamMessageDiv.querySelector("div");
    if (messageContentDiv) {
      let finalMessageContent = messageContentDiv.textContent;
      let messageId =
        window.currentStreamMessageDiv.getAttribute("data-message-id");
      let className = isUserMessage ? "user-message" : "assistant-message";

      // Sanitize the content if not a user message
      if (!isUserMessage) {
        finalMessageContent = DOMPurify.sanitize(finalMessageContent);
      }

      // Replace the temporary streamed message with the final one
      window.currentStreamMessageDiv.remove();
      appendMessageToChatBox(finalMessageContent, className, messageId);
    } else {
      // Handle the case where the message content div was not found
      console.error("Streamed message content div not found.");
    }

    // Reset global variables for streaming
    resetStreamMessageGlobals();
  }
}

function resetStreamMessageGlobals() {
  window.currentStreamMessageDiv = null;
  window.incompleteMarkdownBuffer = "";
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

function appendMessageToChatBox(message, className, messageId) {
  let messageDiv = createMessageDiv(message, className, messageId);
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function createMessageDiv(message, className, messageId) {
  let messageDiv = document.createElement("div");
  messageDiv.classList.add("message", className);

  // Set the data-message-id attribute if provided
  if (messageId) {
    messageDiv.setAttribute("data-message-id", messageId);
  }

  let messageHeader = createMessageHeader(className, messageId);
  messageDiv.appendChild(messageHeader);

  let messageContent = createMessageContent(message, className);
  messageDiv.appendChild(messageContent);

  if (className !== "system-message") {
    let editIcon = messageHeader.querySelector(".fa-edit");
    editIcon.addEventListener("click", function () {
      // Retrieve the messageId from the data attribute at the time of the click
      let currentMessageId = messageDiv.getAttribute("data-message-id");
      setupMessageEditing(messageContent, currentMessageId);
    });
  }
  return messageDiv;
}

function setupMessageEditing(content, messageId) {
  content.contentEditable = "true";
  content.focus();
  content.addEventListener("blur", function () {
    content.contentEditable = "false";
    saveMessageContent(messageId, content.textContent);
  });
  content.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      content.blur();
    }
  });
}

// Function to save the edited content for non-system messages
function saveMessageContent(messageId, newContent) {
  // Perform fetch request to save the updated content
  performFetch(`/chat/edit-message/${messageId}`, { content: newContent })
    .then((response) =>
      handleFetchResponse(response, "Message updated successfully")
    )
    .catch((error) => {
      console.error("Failed to update message: " + error.message);
      updateStatusMessage(error.message, "error");
    });
}
// Function to create the message header and include the edit icon
function createMessageHeader(className, messageId) {
  let header = document.createElement("div");
  header.classList.add("message-header");
  messageContent = document.querySelector(".message-content");
  let title = document.createElement("h5");
  title.textContent = getTitleBasedOnClassName(className);
  header.appendChild(title);

  // Append edit icon to the header for all messages
  let editIcon = createEditIcon();
  header.appendChild(editIcon);

  // Attach the appropriate editing function based on the message type
  // If this is a system message, set up the specific functionality
  if (className === "system-message") {
    editIcon.addEventListener("click", function () {
      messageContent.contentEditable = "true";
      messageContent.focus();
      // Call the function to handle system message editing
      setupSystemMessageEditing(messageContent, messageId);
    });
  }

  return header;
}

function getTitleBasedOnClassName(className) {
  if (className === "assistant-message") {
    return "Jack";
  } else if (className === "user-message") {
    return "User";
  } else if (className === "system-message") {
    return "System";
  }
  return ""; // Default title
}

// Function to create the edit icon and append it to every message header
function createEditIcon() {
  let editIcon = document.createElement("i");
  editIcon.classList.add("fas", "fa-edit");
  return editIcon;
}

function createMessageContent(message, className) {
  let content = document.createElement("div");
  content.classList.add("message-content");
  if (className === "assistant-message") {
    content.innerHTML = DOMPurify.sanitize(marked.parse(message));
    applySyntaxHighlighting(content);
  } else {
    content.textContent = message;
  }
  return content;
}

function setupSystemMessageEditing(content, messageId) {
  content.addEventListener("blur", function () {
    this.contentEditable = "false";
    let conversationId = messageId; // Assuming messageId holds the conversation ID
    saveSystemPrompt(conversationId, this.textContent);
  });

  content.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      this.blur();
    }
  });
}

function selectConversation(conversationId) {
  updateConversationTitle(conversationId);
  clearChatBox();

  fetchConversationMessages(conversationId)
    .then((messages) => {
      messages.forEach((message) => {
        appendMessageToChatBox(
          message.content,
          message.className,
          message.messageId
        );
      });
      updateCompletionConversationId(conversationId);
    })
    .catch((error) => {
      console.error("Error loading conversation:", error);
    });
}

function updateConversationTitle(conversationId) {
  const conversationEntry = document.querySelector(
    `.conversation-entry[data-conversation-id="${conversationId}"]`
  );

  if (conversationEntry && conversationEntry.dataset.conversationTitle) {
    const convoTitleElement = document.getElementById("convo-title");
    if (convoTitleElement) {
      convoTitleElement.textContent =
        conversationEntry.dataset.conversationTitle;
      convoTitleElement.setAttribute("data-conversation-id", conversationId);
    }
  }
}

function updateCompletionConversationId(conversationId) {
  const completionConversationIdInput = document.getElementById(
    "completion-conversation-id"
  );
  if (completionConversationIdInput) {
    completionConversationIdInput.value = conversationId;
  }
}

function clearChatBox() {
  chatBox.innerHTML = "";
}

function fetchConversationMessages(conversationId) {
  return fetch(`/chat/conversation/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => data.messages);
}

function updateCompletionConversationId(conversationId) {
  const completionConversationIdInput = document.getElementById(
    "completion-conversation-id"
  );
  if (completionConversationIdInput) {
    completionConversationIdInput.value = conversationId;
  }
}

function deleteConversation(conversationId) {
  if (isLastConversation()) {
    updateStatusMessage("Cannot delete the last conversation.", "error");
    return;
  }

  if (confirmDeletion()) {
    performDeletion(conversationId);
  }
}

function isLastConversation() {
  const allConversations = document.querySelectorAll(".conversation-entry");
  return allConversations.length <= 1;
}

function confirmDeletion() {
  return confirm("Are you sure you want to delete this conversation?");
}

function performDeletion(conversationId) {
  fetch(`/chat/delete-conversation/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken()
    },
    credentials: "same-origin"
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to delete conversation.");
      }
      return response.json();
    })
    .then((data) => {
      if (data.status === "success") {
        removeConversationEntry(conversationId);
        updateStatusMessage("Conversation deleted successfully.", "success");
      } else {
        updateStatusMessage("Failed to delete conversation.", "error");
      }
    })
    .catch((error) => {
      updateStatusMessage("Error: " + error.message, "error");
    });
}

function removeConversationEntry(conversationId) {
  const entry = document.querySelector(
    `.conversation-entry[data-conversation-id="${conversationId}"]`
  );
  if (entry) {
    entry.remove();
  }
}

function checkNewMessages(conversationId) {
  return fetch(`/chat/check-new-messages/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => data.new_messages);
}

function locateNewMessages(conversationId) {
  checkNewMessages(conversationId)
    .then((newMessages) => {
      // Assume that all messages in chatBox are from the current conversation
      let messageElements = chatBox.querySelectorAll(
        ".message:not([data-message-id])"
      );

      // Iterate over the new messages
      newMessages.forEach((newMessage) => {
        // Find the first message element that matches the new message content
        let matchingElement = Array.from(messageElements).find(
          (messageElement) =>
            messageElement.classList.contains(newMessage.className)
        );

        // If a matching element is found, assign the new message ID to it
        if (matchingElement) {
          matchingElement.setAttribute("data-message-id", newMessage.id);
        }
      });
    })
    .catch((error) => {
      console.error("Error locating new messages:", error);
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
  setupMessageInput();
  setupConversationTitleEditing();
  initializeTooltipBehavior();
  setupModelChangeListener();
  setupChatCompletionForm();
  setupNewConversationForm();
  setupUpdatePreferencesForm();
  setupWindowClick();
  toggleHistory();
  checkConversationHistory();

  function toggleHistory() {
    document.getElementById("conversation-container").style.display = "block";
    document.getElementById("preference-popup").style.display = "none";
    setActiveButton("show-history-btn");
  }
  function setupMessageInput() {
    var messageInput = document.getElementById("message-input");
    if (!messageInput) return;

    messageInput.addEventListener("input", function () {
      adjustTextareaHeight(this);
    });

    messageInput.addEventListener("keydown", function (e) {
      handleSubmitOnEnter(e, this);
    });
  }

  function adjustTextareaHeight(textarea) {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  }

  function handleSubmitOnEnter(event, textarea) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault(); // Prevent the default behavior of enter key
      triggerFormSubmission("chat-completion-form");
    }
  }

  function triggerFormSubmission(formId) {
    var form = document.getElementById(formId);
    if (form) {
      form.dispatchEvent(
        new Event("submit", { cancelable: true, bubbles: true })
      );
    }
  }

  function setupConversationTitleEditing() {
    var convoTitleElement = document.getElementById("convo-title");
    if (!convoTitleElement) return;

    convoTitleElement.addEventListener("blur", function () {
      handleConversationTitleChange(this);
    });

    convoTitleElement.addEventListener("keydown", function (event) {
      submitOnEnter(event, this);
    });
  }

  function handleConversationTitleChange(element) {
    var conversationId = element.getAttribute("data-conversation-id");
    var newTitle = element.textContent.trim();

    if (newTitle.length >= 1 && newTitle.length <= 25) {
      saveConvoTitle(conversationId, newTitle);
    } else {
      updateStatusMessage(
        "Conversation title must be between 1 and 25 characters.",
        "error"
      );
      element.textContent = element.getAttribute("data-conversation-title");
    }
  }

  function submitOnEnter(event, element) {
    if (event.key === "Enter") {
      event.preventDefault();
      element.blur();
    }
  }
  function initializeTooltipBehavior() {
    setupInfoIcons();
    setupTooltipClicks();
    setupWindowClick();
  }

  function setupInfoIcons() {
    document.querySelectorAll(".info-icon").forEach((icon) => {
      icon.addEventListener("click", function (event) {
        handleInfoIconClick(event, this);
      });
    });
  }

  function handleInfoIconClick(event, icon) {
    event.stopPropagation();
    let tooltipText = icon.nextElementSibling;
    toggleTooltip(tooltipText);
  }

  function toggleTooltip(tooltip) {
    const isTooltipVisible = tooltip.style.opacity === "1";
    hideAllTooltips(
      !isTooltipVisible ? tooltip.getAttribute("data-info-id") : null
    );

    if (isTooltipVisible) {
      fadeOutTooltip(tooltip);
    } else {
      fadeInTooltip(tooltip);
    }
  }

  function fadeInTooltip(tooltip) {
    tooltip.style.visibility = "visible";
    tooltip.style.opacity = "1";
    tooltip.style.transition = "opacity 0.5s ease-in";
  }

  function fadeOutTooltip(tooltip) {
    tooltip.style.opacity = "0";
    tooltip.style.transition = "opacity 0.5s ease-out";
    setTimeout(() => {
      tooltip.style.visibility = "hidden";
    }, 500);
  }

  function hideAllTooltips(exceptId = null) {
    document.querySelectorAll(".tooltip-text").forEach((tooltip) => {
      if (!exceptId || tooltip.getAttribute("data-info-id") !== exceptId) {
        fadeOutTooltip(tooltip);
      }
    });
  }

  function setupTooltipClicks() {
    document.querySelectorAll(".tooltip-text").forEach((tooltip) => {
      tooltip.addEventListener("click", function (event) {
        event.stopPropagation();
        fadeOutTooltip(this);
      });
    });
  }

  function setupWindowClick() {
    window.addEventListener("click", function () {
      hideAllTooltips();
    });
  }
  function checkConversationHistory() {
    if (hasConversationsInHistory()) {
      displayMostRecentConversation();
      appendAllMessagesFromHistory();
    } else {
      showNewConversationForm();
    }
  }

  function hasConversationsInHistory() {
    return conversationHistory && conversationHistory.length > 0;
  }

  function displayMostRecentConversation() {
    const mostRecentConversation =
      conversationHistory[conversationHistory.length - 1];
    selectConversation(mostRecentConversation.id);
  }

  function appendAllMessagesFromHistory() {
    conversationHistory.forEach((message) => {
      // Skip the message if its id is null, None, or undefined
      if (
        message.messageId === null ||
        message.messageId === "None" ||
        message.messageId === undefined
      ) {
        return;
      }
      appendMessageToChatBox(
        message.content,
        message.className,
        message.messageId
      );
    });
  }

  function showNewConversationForm() {
    newConversationForm.style.display = "block";
    chatCompletionForm.style.display = "none";
  }
  function setupModelChangeListener() {
    const modelDropdown = document.getElementById("model");
    if (!modelDropdown) return;

    modelDropdown.addEventListener("change", function () {
      updateMaxTokensBasedOnModel(this.value);
    });
  }

  function updateMaxTokensBasedOnModel(selectedModel) {
    const maxTokens = modelMaxTokens[selectedModel];
    if (!maxTokens) return;

    updateMaxTokensSlider(maxTokens);
    updateMaxTokensValueInput(maxTokens);
  }

  function updateMaxTokensSlider(maxTokens) {
    const maxTokensSlider = document.getElementById("max_tokens");
    if (maxTokensSlider) {
      maxTokensSlider.max = maxTokens;
      maxTokensSlider.value = maxTokens;
    }
  }

  function updateMaxTokensValueInput(maxTokens) {
    const maxTokensValueInput = document.getElementById("max-tokens-value");
    if (maxTokensValueInput) {
      maxTokensValueInput.value = maxTokens;
    }
  }

  function setupChatCompletionForm() {
    const chatCompletionForm = document.getElementById("chat-completion-form");
    if (!chatCompletionForm) return;

    chatCompletionForm.addEventListener("submit", function (event) {
      handleChatCompletionFormSubmission(event, this);
    });
  }

  function handleChatCompletionFormSubmission(event, form) {
    event.preventDefault();
    const messageToSend = document.getElementById("message-input").value;
    submitChatMessage(messageToSend, form);
    document.getElementById("message-input").value = "";
  }

  function submitChatMessage(message, form) {
    appendMessageToChatBox(message, "user-message");

    const formData = new FormData(form);
    formData.append("prompt", message);

    fetchChatCompletionResponse(formData)
      .then((response) => processChatCompletionResponse(response))
      .catch((error) => handleChatCompletionError(error));
  }

  function fetchChatCompletionResponse(formData) {
    return fetch("/chat/completion", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
      credentials: "same-origin",
      body: JSON.stringify(Object.fromEntries(formData))
    });
  }

  function processChatCompletionResponse(response) {
    const contentType = response.headers.get("Content-Type");
    if (contentType && contentType.includes("text/plain")) {
      processStreamedResponse(response);
    } else {
      response.text().then((text) => processNonStreamedResponse(text));
    }
  }

  function processStreamedResponse(response) {
    const reader = response.body.getReader();
    readStreamedResponseChunk(reader);
  }

  function readStreamedResponseChunk(reader) {
    reader
      .read()
      .then(({ done, value }) => {
        if (done) {
          finalizeStreamedResponse();
          var conversationId = document
            .getElementById("convo-title")
            .getAttribute("data-conversation-id");
          locateNewMessages(conversationId);
          return;
        }
        handleResponseChunk(value);
        readStreamedResponseChunk(reader);
      })
      .catch((error) => {
        appendMessageToChatBox(
          "Streaming Error: " + error.message,
          "error-message"
        );
        console.error("Streaming error:", error);
      });
  }

  function handleResponseChunk(value) {
    const chunk = new TextDecoder().decode(value);
    if (chunk.startsWith("An error occurred:")) {
      appendMessageToChatBox(chunk, "error-message");
    } else {
      appendStreamedResponse(chunk, chatBox);
    }
  }

  function processNonStreamedResponse(text) {
    if (text.includes("An error occurred:")) {
      appendMessageToChatBox(text, "error-message");
    } else {
      try {
        const data = JSON.parse(text);
        appendMessageToChatBox(data.message, "assistant-message");
        var conversationId = document
          .getElementById("convo-title")
          .getAttribute("data-conversation-id");
        locateNewMessages(conversationId);
      } catch (error) {
        appendMessageToChatBox(
          "Unexpected response format: " + text,
          "error-message"
        );
      }
    }
  }

  function handleChatCompletionError(error) {
    appendMessageToChatBox("Fetch Error: " + error.message, "error-message");
    console.error("Fetch error:", error);
  }
  function setupNewConversationForm() {
    const newConversationForm = document.getElementById(
      "new-conversation-form"
    );
    if (!newConversationForm) return;

    newConversationForm.addEventListener("submit", function (event) {
      handleNewConversationFormSubmission(event, this);
    });
  }

  function handleNewConversationFormSubmission(event, form) {
    event.preventDefault();
    const formData = new FormData(form);

    submitNewConversation(formData)
      .then((data) => processNewConversationResponse(data))
      .catch((error) =>
        updateStatusMessage("Error: " + error.message, "error")
      );
  }

  function submitNewConversation(formData) {
    return fetch("/chat/new-conversation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
      credentials: "same-origin",
      body: JSON.stringify(Object.fromEntries(formData))
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Failed to start a new conversation.");
      }
      return response.json();
    });
  }

  function processNewConversationResponse(data) {
    if (data.status === "success") {
      addNewConversationToHistory(data);
      updateConversationListUI(data.conversation_id, data.title);
      selectConversation(data.conversation_id);
      updateStatusMessage("New conversation started.", "success");
    } else {
      updateStatusMessage(data.message, "error");
    }
  }

  function addNewConversationToHistory(data) {
    conversationHistory.push({
      id: data.conversation_id,
      title: data.title,
      created_at: data.created_at,
      system_prompt: data.system_prompt
    });
  }

  function updateConversationListUI(conversationId, conversationTitle) {
    const conversationHistoryDiv = document.getElementById(
      "conversation-history"
    );
    const newConvoEntry = createConversationEntry(
      conversationId,
      conversationTitle
    );
    conversationHistoryDiv.appendChild(newConvoEntry);
    chatBox.innerHTML = "";
  }

  function createConversationEntry(conversationId, conversationTitle) {
    const newConvoEntry = document.createElement("div");
    newConvoEntry.classList.add("conversation-entry");
    newConvoEntry.setAttribute("data-conversation-id", conversationId);
    newConvoEntry.setAttribute("data-conversation-title", conversationTitle);
    newConvoEntry.innerHTML = `<p class="text-entry">${conversationTitle}</p> <span class="delete-conversation" onclick="deleteConversation(${conversationId})"><i class="fas fa-trash-alt"></i></span>`;
    newConvoEntry.addEventListener("click", function () {
      selectConversation(conversationId);
    });
    return newConvoEntry;
  }
  function setupUpdatePreferencesForm() {
    const updatePreferencesForm = document.getElementById(
      "update-preferences-form"
    );
    if (!updatePreferencesForm) return;

    updatePreferencesForm.addEventListener("submit", function (event) {
      handleUpdatePreferencesFormSubmission(event);
    });
  }

  function handleUpdatePreferencesFormSubmission(event) {
    event.preventDefault();
    const formData = new FormData(event.target);

    submitUpdatePreferences(formData)
      .then((data) => processUpdatePreferencesResponse(data))
      .catch((error) =>
        updatePreferenceMessages("Error: " + error.message, "error")
      );
  }

  function submitUpdatePreferences(formData) {
    return fetch("/chat/update-preferences", {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken()
      },
      body: formData
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Failed to update preferences.");
      }
      return response.json();
    });
  }

  function processUpdatePreferencesResponse(data) {
    if (data.status === "success") {
      updatePreferenceMessages(data.message, "success");
    } else {
      updatePreferenceMessages(data.message, "error");
      console.error(data.errors);
    }
  }

  function setupWindowClick() {
    window.addEventListener("click", function (event) {
      closePreferencePopupOnClick(event);
    });
  }

  function closePreferencePopupOnClick(event) {
    const popup = document.getElementById("preference-popup");
    if (popup && event.target == popup) {
      popup.classList.remove("show");
    }
  }
});
