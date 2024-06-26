const chatBox = document.getElementById("chat-box");
let isInterrupted = false;

hljs.configure({
  ignoreUnescapedHTML: true,
});

function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
}

// Function to display the loading template
function showLoading() {
  const loadingTemplate = document.getElementById("loader-template");
  if (loadingTemplate) {
    loadingTemplate.style.display = "block";
  }
}

// Function to hide the loading template
function hideLoading() {
  const loadingTemplate = document.getElementById("loader-template");
  if (loadingTemplate) {
    loadingTemplate.style.display = "none";
  }
}

// Refactored showToast function using modern JavaScript features:
function showToast(message, type) {
  let toast = document.getElementById("toast") || createToastElement();
  toast.textContent = message;
  toast.className = type;
  showAndHideToast(toast);
}

function createToastElement() {
  const toast = document.createElement("div");
  toast.id = "toast";
  document.body.appendChild(toast);
  return toast;
}

function showAndHideToast(toast) {
  Object.assign(toast.style, {
    display: "block",
    opacity: "1",
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.style.display = "none";
    }, 600);
  }, 3000);
}

function throttle(func, limit) {
  let inThrottle;
  return function () {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

function scrollToBottom(chatBox) {
  requestAnimationFrame(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
  });
}

function removeActiveClassFromButtons() {
  document.querySelectorAll(".options-button").forEach((button) => {
    button.classList.remove("active");
  });
}

function setActiveButton(activeButtonId) {
  removeActiveClassFromButtons();

  const activeButton = document.getElementById(activeButtonId);
  if (activeButton) {
    activeButton.classList.add("active");
  }
}

function debounce(func, wait, immediate) {
  let timeout;
  return function () {
    const context = this,
      args = arguments;
    const later = function () {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(context, args);
  };
}

// Modify setupFormSubmission to support debounced submission
function setupFormSubmission(
  formId,
  submitUrl,
  successCallback,
  errorCallback,
) {
  const form = document.getElementById(formId);
  if (!form) return;

  const debouncedSubmit = debounce(function () {
    const formData = new FormData(form);
    submitForm(formData, submitUrl).then(successCallback).catch(errorCallback);
  }, 1000); // Debounce time of 1000 milliseconds

  form.addEventListener("input", function (event) {
    event.preventDefault();
    debouncedSubmit();
  });
}

async function submitForm(formData, submitUrl) {
  const response = await fetch(submitUrl, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to update preferences.");
  }

  return response.json();
}

function handleResponse(data) {
  if (data.status === "success") {
    showToast(data.message, "success");
  } else {
    showToast(data.message, "error");
    console.error(data.errors);
  }
}

setupFormSubmission(
  "update-preferences-form",
  "/chat/update-preferences",
  handleResponse,
  (error) => showToast("Error: " + error.message, "error"),
);

setupFormSubmission(
  "docs-preferences-form",
  "/embedding/update-doc-preferences",
  handleResponse,
  (error) => showToast("Error: " + error.message, "error"),
);

function togglePopup(activePopupId, activeButtonId) {
  requestAnimationFrame(() => {
    const popups = {
      "preference-popup": "show-preferences-btn",
      "docs-settings-popup": "docs-preferences-btn",
      "conversation-container": "show-history-btn",
    };

    // Iterate through the popups to show/hide them as necessary
    Object.keys(popups).forEach((popupId) => {
      document.getElementById(popupId).style.display =
        popupId === activePopupId ? "block" : "none";
    });

    // Set the active button
    setActiveButton(activeButtonId);
  });
}

// After refactoring
function setupButtonListener(buttonId, popupId) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.addEventListener("click", () => togglePopup(popupId, buttonId));
  }
}

setupButtonListener("show-preferences-btn", "preference-popup");
setupButtonListener("docs-preferences-btn", "docs-settings-popup");
setupButtonListener("show-history-btn", "conversation-container");

function toggleButtonState() {
  const button = document.getElementById("toggle-button");
  const currentState = button.getAttribute("data-state");
  const icon = button.querySelector("i");

  if (currentState === "send") {
    icon.classList.remove("nuicon-paper-plane");
    icon.classList.add("nuicon-pause");
    button.setAttribute("data-state", "pause");
  } else {
    icon.classList.remove("nuicon-pause");
    icon.classList.add("nuicon-paper-plane");
    button.setAttribute("data-state", "send");
  }
}

function interruptAIResponse() {
  let conversationId = document
    .getElementById("convo-title")
    .getAttribute("data-conversation-id");

  fetch(`/chat/interrupt-stream/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
  })
    .then((response) => response.json())
    // eslint-disable-next-line no-unused-vars
    .then((data) => {
      isInterrupted = true;
      toggleButtonState();
    })
    .catch((error) => console.error("Error interrupting the stream:", error));
}

function performFetch(url, payload) {
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify(payload),
  });
}

function handleFetchResponse(response, successMessage) {
  if (!response.ok) {
    throw new Error(response.statusText || "HTTP error!");
  }
  return response.json().then((data) => {
    if (data.status === "success") {
      showToast(successMessage, "success");
    } else {
      throw new Error(data.message);
    }
  });
}

function saveSystemPrompt(conversationId, newPrompt) {
  performFetch(`/chat/update-system-prompt/${conversationId}`, {
    system_prompt: newPrompt,
  })
    .then((response) =>
      handleFetchResponse(response, "System prompt updated successfully"),
    )
    .catch((error) => {
      console.error("Failed to update system prompt: " + error.message);
      showToast(error.message, "error");
    });
}

function saveConvoTitle(conversationId, newTitle) {
  performFetch(`/chat/update-conversation-title/${conversationId}`, {
    title: newTitle,
  })
    .then((response) =>
      handleFetchResponse(response, "Title updated successfully"),
    )
    .then(() => updateConversationUI(conversationId, newTitle))
    .catch((error) => {
      console.error("Failed to update title: " + error.message);
      showToast(error.message, "error");
    });
}

function updateConversationUI(conversationId, newTitle) {
  requestAnimationFrame(() => {
    let conversationEntry = document.querySelector(
      `.conversation-entry[data-conversation-id="${conversationId}"]`,
    );
    if (conversationEntry) {
      let textEntryElement = conversationEntry.querySelector(".text-entry");
      if (textEntryElement) {
        textEntryElement.textContent = newTitle;
      }
      conversationEntry.setAttribute("data-conversation-title", newTitle);

      if (typeof conversationHistory !== "undefined") {
        let conversation = conversationHistory.find(
          (conv) => conv.id === conversationId,
        );
        if (conversation) {
          conversation.title = newTitle;
        }
      }
    }
  });
}

function appendStreamedResponse(chunk, chatBox, isUserMessage = false) {
  requestAnimationFrame(() => {
    if (!window.currentStreamMessageDiv) {
      window.currentStreamMessageDiv = createStreamMessageDiv(isUserMessage);
      chatBox.appendChild(window.currentStreamMessageDiv);
    }

    if (chunk != null) {
      window.incompleteMarkdownBuffer += chunk;

      updateStreamMessageContent(isUserMessage);
    }

    scrollToBottom(chatBox);
  });
}

function createStreamMessageDiv(isUserMessage) {
  let messageDiv = document.createElement("div");
  messageDiv.classList.add(
    "message",
    isUserMessage ? "user-message" : "assistant-message",
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

function updateStreamMessageContent(isUserMessage, chunk) {
  requestAnimationFrame(() => {
    if (isUserMessage) {
      window.currentStreamContentDiv.textContent += chunk;
    } else {
      window.currentStreamContentDiv.innerHTML = marked.parse(
        window.incompleteMarkdownBuffer,
      );
      applySyntaxHighlighting(window.currentStreamContentDiv);
    }
  });
}

function applySyntaxHighlighting(element) {
  element.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightBlock(block);
  });
}

function finalizeStreamedResponse(isUserMessage = false) {
  requestAnimationFrame(() => {
    if (window.currentStreamMessageDiv) {
      let messageContentDiv =
        window.currentStreamMessageDiv.querySelector("div");
      if (messageContentDiv) {
        let finalMessageContent = isUserMessage
          ? messageContentDiv.textContent
          : marked.parse(window.incompleteMarkdownBuffer);
        let messageId =
          window.currentStreamMessageDiv.getAttribute("data-message-id");
        let className = isUserMessage ? "user-message" : "assistant-message";

        if (!isUserMessage) {
          finalMessageContent = DOMPurify.sanitize(finalMessageContent);
        }

        window.currentStreamMessageDiv.remove();
        let finalDiv = appendMessageToChatBox(
          finalMessageContent,
          className,
          messageId,
        );
        toggleButtonState();
        window.isWaitingForResponse = false;

        if (!isUserMessage) {
          applySyntaxHighlighting(finalDiv);
        }
      } else {
        console.error("Streamed message content div not found.");
      }

      resetStreamMessageGlobals();
    }
  });
}

function resetStreamMessageGlobals() {
  window.currentStreamMessageDiv = null;
  window.incompleteMarkdownBuffer = "";
}

function appendMessageToChatBox(message, className, messageId) {
  let messageDiv = createMessageDiv(message, className, messageId);
  requestAnimationFrame(() => {
    chatBox.appendChild(messageDiv);
    scrollToBottom(chatBox);
  });
  return messageDiv;
}

function createMessageDiv(message, className, messageId) {
  let messageDiv = document.createElement("div");
  messageDiv.classList.add("message", className);

  if (messageId) {
    messageDiv.setAttribute("data-message-id", messageId);
  }

  let messageHeader = createMessageHeader(className, messageId);
  messageDiv.appendChild(messageHeader);

  let messageContent = createMessageContent(message, className);
  messageDiv.appendChild(messageContent);
  return messageDiv;
}

function createClipboardIcon(copyTarget) {
  let clipboardIcon = document.createElement("i");
  clipboardIcon.classList.add("nuicon-clipboard", "clipboard-icon");
  clipboardIcon.addEventListener("click", function (event) {
    event.stopPropagation();

    let textToCopy;
    if (copyTarget === "code") {
      textToCopy = this.parentNode.textContent;
    } else if (copyTarget === "message") {
      textToCopy = this.parentNode.parentNode.textContent;
    }
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {})
      .catch((err) => {
        console.error("Failed to copy text:", err);
      });
  });

  return clipboardIcon;
}

function removeSubsequentMessagesUI(messageId) {
  if (messageId == null) {
    console.error(
      "removeSubsequentMessagesUI was called with an undefined or null messageId.",
    );
    return;
  }

  const allMessages = Array.from(chatBox.getElementsByClassName("message"));

  const currentMessageIndex = allMessages.findIndex((msg) => {
    return msg.dataset.messageId === messageId.toString();
  });

  if (
    currentMessageIndex !== -1 &&
    currentMessageIndex + 1 < allMessages.length
  ) {
    allMessages.slice(currentMessageIndex + 1).forEach((msg) => msg.remove());
  }
}

function retryMessage(messageId) {
  toggleButtonState();
  performFetch(`/chat/retry-message/${messageId}`, {}).then((response) => {
    if (!response.ok) {
      throw new Error("Failed to retry message.");
    }
    const contentType = response.headers.get("Content-Type");
    if (contentType && contentType.includes("text/event-stream")) {
      processStreamedResponse(response);
    }
  });
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

function saveMessageContent(messageId, newContent) {
  performFetch(`/chat/edit-message/${messageId}`, { content: newContent })
    .then((response) =>
      handleFetchResponse(response, "Message updated successfully"),
    )
    .catch((error) => {
      console.error("Failed to update message: " + error.message);
      showToast(error.message, "error");
    });
}

function createMessageHeader(className, messageId) {
  let header = document.createElement("div");
  header.classList.add("message-header");
  let messageContent = document.querySelector(".message-content");
  let title = document.createElement("h5");
  title.textContent = getTitleBasedOnClassName(className);
  header.appendChild(title);

  if (className === "assistant-message") {
    let clipboardIcon = createClipboardIcon("message");
    header.appendChild(clipboardIcon);
  }

  if (className === "user-message") {
    let retryIcon = document.createElement("i");
    retryIcon.classList.add("nuicon-refresh", "retry-icon");
    retryIcon.addEventListener("click", function (event) {
      event.stopPropagation();

      let messageElement = event.target.closest(".message");
      if (!messageElement) {
        console.error("Message element not found for the retry icon.");
        return;
      }
      let messageId = messageElement.dataset.messageId;
      if (!messageId) {
        console.error("Message ID is undefined for the retry icon.");
        return;
      }
      removeSubsequentMessagesUI(messageId);
      retryMessage(messageId);
    });
    header.appendChild(retryIcon);
  }

  let editIcon = createEditIcon();
  header.appendChild(editIcon);

  if (className === "system-message") {
    editIcon.addEventListener("click", function () {
      messageContent = document.querySelector(".message-content");

      messageContent.contentEditable = "true";
      messageContent.focus();

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
  return "";
}

function createEditIcon() {
  let editIcon = document.createElement("i");
  editIcon.classList.add("nuicon-square-pen");
  return editIcon;
}

function createMessageContent(message, className) {
  let content = document.createElement("div");
  content.classList.add("message-content");
  if (className === "assistant-message") {
    content.innerHTML = DOMPurify.sanitize(marked.parse(message));
    applySyntaxHighlighting(content);

    let codeBlocks = content.querySelectorAll("pre > code");
    codeBlocks.forEach((code) => {
      let clipboardIcon = createClipboardIcon("code");
      clipboardIcon.classList.add("code-clipboard-icon");
      code.parentNode.insertBefore(clipboardIcon, code);
    });
  } else {
    content.textContent = message;
  }

  return content;
}

function setupSystemMessageEditing(content, messageId) {
  content.addEventListener("blur", function () {
    content.contentEditable = "false";
    saveSystemPrompt(messageId, this.textContent);
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
  highlightActiveConversation(conversationId);
  clearChatBox();

  fetchConversationMessages(conversationId)
    .then((messages) => {
      messages.forEach((message) => {
        // Use the existing appendMessageToChatBox function to add the message content
        appendMessageToChatBox(
          message.content,
          message.className,
          message.messageId,
        );
      });
      updateCompletionConversationId(conversationId);
    })
    .catch((error) => {
      console.error("Error loading conversation:", error);
    });
}

const throttledSelectConversation = throttle(selectConversation, 1000); // Adjust the 1000ms delay as needed

function updateConversationTitle(conversationId) {
  requestAnimationFrame(() => {
    const conversationEntry = document.querySelector(
      `.conversation-entry[data-conversation-id="${conversationId}"]`,
    );

    if (conversationEntry && conversationEntry.dataset.conversationTitle) {
      const convoTitleElement = document.getElementById("convo-title");
      if (convoTitleElement) {
        convoTitleElement.setAttribute("data-conversation-id", conversationId);
      }
    }
  });
}

function updateCompletionConversationId(conversationId) {
  const completionConversationIdInput = document.getElementById(
    "completion-conversation-id",
  );
  if (completionConversationIdInput) {
    completionConversationIdInput.value = conversationId;
  }
}

function clearChatBox() {
  requestAnimationFrame(() => {
    chatBox.innerHTML = "";
  });
}

function fetchConversationMessages(conversationId) {
  return fetch(`/chat/conversation/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => data.messages);
}

function deleteConversation(conversationId) {
  requestAnimationFrame(() => {
    if (isLastConversation()) {
      showToast("Cannot delete the last conversation.", "error");
      return;
    }

    if (confirmDeletion()) {
      performDeletion(conversationId);
    }
  });
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
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
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
        showToast("Conversation deleted successfully.", "success");
      } else {
        showToast("Failed to delete conversation.", "error");
      }
    })
    .catch((error) => {
      showToast("Error: " + error.message, "error");
    });
}

function removeConversationEntry(conversationId) {
  requestAnimationFrame(() => {
    const entry = document.querySelector(
      `.conversation-entry[data-conversation-id="${conversationId}"]`,
    );
    if (entry) {
      entry.remove();
    }
  });
}

function checkNewMessages(conversationId) {
  return fetch(`/chat/check-new-messages/${conversationId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
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
      let messageElements = chatBox.querySelectorAll(
        ".message:not([data-message-id])",
      );

      newMessages.forEach((newMessage) => {
        let matchingElement = Array.from(messageElements).find(
          (messageElement) =>
            messageElement.classList.contains(newMessage.className),
        );

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
  "gpt-4-turbo": 128000,
  "gpt-4-turbo-2024-04-09": 128000,
  "gpt-4-turbo-preview": 128000,
  "gpt-4-0125-preview": 128000,
  "gpt-4-1106-preview": 128000,
  "gpt-4-vision-preview": 128000,
  "gpt-4-1106-vision-preview": 128000,
  "gpt-4": 8192,
  "gpt-4-0613": 8192,
  "gpt-4-32k": 32768,
  "gpt-4-32k-0613": 32768,
  "gpt-3.5-turbo-0125": 16385,
  "gpt-3.5-turbo": 16385,
  "gpt-3.5-turbo-1106": 16385,
  "gpt-3.5-turbo-instruct": 4096,
  "gpt-3.5-turbo-16k": 16385,
  "gpt-3.5-turbo-0613": 4096,
  "gpt-3.5-turbo-16k-0613": 16385,
};

requestAnimationFrame(() => {
  setupMessageInput();
  initializeToggleButton();
  setupModelChangeListener();
  setupChatCompletionForm();
  setupNewConversationForm();
  checkConversationHistory();
});
window.isWaitingForResponse = false;

document.addEventListener("click", function (event) {
  if (event.target.matches(".nuicon-pen-line")) {
    const messageDiv = event.target.closest(".message");
    if (messageDiv && !messageDiv.classList.contains("system-message")) {
      const messageId = messageDiv.dataset.messageId;
      const messageContent = messageDiv.querySelector(".message-content");
      setupMessageEditing(messageContent, messageId);
    }
  }
});

const conversationHistoryDiv = document.getElementById("conversation-history");
conversationHistoryDiv.addEventListener("click", function (event) {
  const conversationEntry = event.target.closest(".conversation-entry");
  if (conversationEntry) {
    event.stopPropagation();
  }
});

function initializeToggleButton() {
  const toggleButton = document.getElementById("toggle-button");
  if (!toggleButton) return;

  toggleButton.setAttribute("data-state", "send");

  toggleButton.addEventListener("click", function (event) {
    const currentState = this.getAttribute("data-state");

    if (currentState === "send") {
      /* empty */
    } else {
      event.preventDefault();
      interruptAIResponse();
      toggleButtonState();
    }
  });
}

function setupMessageInput() {
  let messageInput = document.getElementById("message-input");
  if (!messageInput) return;

  messageInput.addEventListener("input", function () {
    adjustTextareaHeight(this);
  });

  messageInput.addEventListener("keydown", function (e) {
    handleSubmitOnEnter(e, this);
  });
}

function adjustTextareaHeight(textarea) {
  requestAnimationFrame(() => {
    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";
  });
}

let isSubmitting = false;

function handleSubmitOnEnter(event, textarea) {
  if (event.key === "Enter" && !event.shiftKey) {
    if (textarea.value.trim() === "") {
      event.preventDefault();
      console.error("Cannot submit an empty message.");
    } else if (isSubmitting) {
      event.preventDefault();
      console.error("Submission in progress.");
    } else {
      event.preventDefault();
      isSubmitting = true;
      triggerFormSubmission("chat-completion-form");
      setTimeout(() => (isSubmitting = false), 2000);
    }
  }
}

function triggerFormSubmission(formId) {
  let form = document.getElementById(formId);
  if (form) {
    form.dispatchEvent(
      new Event("submit", { cancelable: true, bubbles: true }),
    );
  }
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
  throttledSelectConversation(mostRecentConversation.id);
}

function appendAllMessagesFromHistory() {
  requestAnimationFrame(() => {
    const fragment = document.createDocumentFragment();
    conversationHistory.forEach((message) => {
      if (
        message.messageId === null ||
        message.messageId === "None" ||
        message.messageId === undefined
      ) {
        return;
      }
      const messageDiv = appendMessageToChatBox(
        message.content,
        message.className,
        message.messageId,
      );
      fragment.appendChild(messageDiv);
    });

    chatBox.appendChild(fragment);
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

  updateMaxTokensBasedOnModel(modelDropdown.value);
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
    throttledHandleChatCompletionFormSubmission(event, this);
  });
}

function handleChatCompletionFormSubmission(event, form) {
  event.preventDefault();
  const messageToSend = document.getElementById("message-input").value;
  if (messageToSend.trim() === "") {
    console.error("Cannot send an empty message.");
    return;
  }
  if (window.isWaitingForResponse) {
    console.error("Please wait for the current AI response.");
    return;
  }
  window.isWaitingForResponse = true;
  submitChatMessage(messageToSend, form);
  document.getElementById("message-input").value = "";
}

const throttledHandleChatCompletionFormSubmission = throttle(
  handleChatCompletionFormSubmission,
  2000,
);

function submitChatMessage(message, form) {
  appendMessageToChatBox(message, "user-message", null);
  showLoading();
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
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
    body: JSON.stringify(Object.fromEntries(formData)),
  });
}

function processChatCompletionResponse(response) {
  const contentType = response.headers.get("Content-Type");
  if (contentType && contentType.includes("text/event-stream")) {
    hideLoading(); // Hide the loader when the response is processed
    toggleButtonState();
    processStreamedResponse(response);
  }
}

function processStreamedResponse(response) {
  requestAnimationFrame(() => {
    isInterrupted = false;
    const reader = response.body.getReader();
    const chunks = [];
    const updateInterval = 100; // Update the DOM every 100ms or adjust as needed
    let lastUpdateTime = Date.now();

    function readStreamedResponseChunk(reader) {
      if (isInterrupted) {
        finalizeStreamedResponse();
        let conversationId = document
          .getElementById("convo-title")
          .getAttribute("data-conversation-id");
        locateNewMessages(conversationId);
        return;
      }

      reader
        .read()
        .then(({ done, value }) => {
          if (done) {
            if (chunks.length) {
              appendStreamedResponse(chunks.join(""), chatBox);
            }
            finalizeStreamedResponse();
            let conversationId = document
              .getElementById("convo-title")
              .getAttribute("data-conversation-id");
            locateNewMessages(conversationId);
            return;
          }

          const chunk = new TextDecoder().decode(value);
          chunks.push(chunk);

          const now = Date.now();
          if (now - lastUpdateTime > updateInterval) {
            appendStreamedResponse(chunks.join(""), chatBox);
            chunks.length = 0; // Clear the chunks array
            lastUpdateTime = now;
          }

          readStreamedResponseChunk(reader);
        })
        .catch((error) => {
          showToast("Streaming Error: " + error.message, "error");
          console.error("Streaming error:", error);
        });
    }

    readStreamedResponseChunk(reader);
  });
}

function highlightActiveConversation(conversationId) {
  const conversationEntries = document.querySelectorAll(".conversation-entry");
  conversationEntries.forEach((entry) => {
    if (entry.getAttribute("data-conversation-id") === conversationId) {
      entry.classList.add("active");
    } else {
      entry.classList.remove("active");
    }
  });
}

function handleChatCompletionError(error) {
  requestAnimationFrame(() => {
    hideLoading(); // Hide the loader when the response is processed
    showToast("Fetch Error: " + error.message, "error");
    console.error("Fetch error:", error);
  });
}

function setupNewConversationForm() {
  const newConversationForm = document.getElementById("new-conversation-form");
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
    .catch((error) => showToast("Error: " + error.message, "error"));
}

function submitNewConversation(formData) {
  return fetch("/chat/new-conversation", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
    body: JSON.stringify(Object.fromEntries(formData)),
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
    throttledSelectConversation(data.conversation_id);
    showToast("New conversation started.", "success");
  } else {
    showToast(data.message, "error");
  }
}

function addNewConversationToHistory(data) {
  conversationHistory.push({
    id: data.conversation_id,
    title: data.title,
    created_at: data.created_at,
    system_prompt: data.system_prompt,
  });
}

function updateConversationListUI(conversationId, conversationTitle) {
  requestAnimationFrame(() => {
    const conversationHistoryDiv = document.getElementById(
      "conversation-history",
    );
    const fragment = document.createDocumentFragment();

    const newConvoEntry = createConversationEntry(
      conversationId,
      conversationTitle,
    );

    fragment.appendChild(newConvoEntry);

    conversationHistoryDiv.appendChild(fragment);
    chatBox.innerHTML = ""; // Clear the chat box for the new conversation

    // Ensure the new conversation is highlighted as active
    highlightActiveConversation(conversationId);
  });
}

// Create a text entry for the conversation title
function createTextEntry(conversationTitle) {
  const textEntry = document.createElement("p");
  textEntry.classList.add("text-entry");
  textEntry.textContent = conversationTitle;
  return textEntry;
}

// Create an edit icon span
function createTitleEditIcon(conversationId) {
  const editSpan = document.createElement("span");
  editSpan.classList.add("edit-conversation-title");
  editSpan.setAttribute("data-conversation-id", conversationId);
  const editIcon = document.createElement("i");
  editIcon.classList.add("nuicon-pen-line");
  editSpan.appendChild(editIcon);
  return editSpan;
}

// Create a delete icon span
function createDeleteIcon(conversationId) {
  const deleteSpan = document.createElement("span");
  deleteSpan.classList.add("delete-conversation");
  deleteSpan.setAttribute("data-conversation-id", conversationId);
  const deleteIcon = document.createElement("i");
  deleteIcon.classList.add("nuicon-trash-can");
  deleteSpan.appendChild(deleteIcon);
  return deleteSpan;
}

// Create a div to contain the icons
function createIconsContainer(editSpan, deleteSpan) {
  const iconsContainer = document.createElement("div");
  iconsContainer.classList.add("convo-icons");
  iconsContainer.appendChild(editSpan);
  iconsContainer.appendChild(deleteSpan);
  return iconsContainer;
}

// Main function to create a conversation entry
function createConversationEntry(conversationId, conversationTitle) {
  const newConvoEntry = document.createElement("div");
  newConvoEntry.classList.add("conversation-entry");
  newConvoEntry.setAttribute("data-conversation-id", conversationId);
  newConvoEntry.setAttribute("data-conversation-title", conversationTitle);

  const textEntry = createTextEntry(conversationTitle);
  newConvoEntry.appendChild(textEntry);

  const editSpan = createTitleEditIcon(conversationId);
  const deleteSpan = createDeleteIcon(conversationId);
  const iconsContainer = createIconsContainer(editSpan, deleteSpan);
  newConvoEntry.appendChild(iconsContainer);

  return newConvoEntry;
}
// Event delegation setup on the container of all conversation entries
function initializeEventListeners() {
  const conversationContainer = document.getElementById("conversation-history");

  conversationContainer.addEventListener("keydown", function (event) {
    if (
      event.key === "Enter" &&
      event.target.classList.contains("text-entry") &&
      event.target.contentEditable === "true"
    ) {
      event.preventDefault();
      const textEntry = event.target;
      const conversationId = textEntry
        .closest(".conversation-entry")
        .getAttribute("data-conversation-id");
      saveConvoTitle(conversationId, textEntry.textContent.trim());
      textEntry.contentEditable = "false";
      textEntry.blur(); // Remove focus after editing
    }
  });

  conversationContainer.addEventListener("click", function (event) {
    const target = event.target;
    const editIcon = target.closest(".edit-conversation-title");
    const deleteIcon = target.closest(".delete-conversation");
    const textEntry = target.closest(".text-entry");

    // Handle clicks on edit and delete icons
    if (editIcon || deleteIcon) {
      event.stopPropagation(); // Prevent triggering conversation selection

      if (editIcon) {
        const textEntry = editIcon.parentNode.previousElementSibling;
        textEntry.contentEditable = "true";
        textEntry.focus();
      } else if (deleteIcon) {
        const conversationId = deleteIcon.getAttribute("data-conversation-id");
        deleteConversation(conversationId);
      }
    } else if (textEntry && textEntry.contentEditable === "true") {
      // Prevent conversation selection when text entry is editable
      event.stopPropagation();
    } else {
      // Handle conversation entry clicks for non-editable text entries
      const conversationEntry = target.closest(".conversation-entry");
      if (conversationEntry) {
        const conversationId = conversationEntry.getAttribute(
          "data-conversation-id",
        );
        throttledSelectConversation(conversationId);
      }
    }
  });
}

initializeEventListeners();
