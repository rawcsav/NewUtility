var chatBox = document.getElementById("chat-box");
let isInterrupted = false;

hljs.configure({
  ignoreUnescapedHTML: true
});

function showToast(message, type) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.className = type;

  toast.style.display = "block";
  toast.style.opacity = "1";

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

function toggleButtonState() {
  const button = document.getElementById("toggle-button");
  const currentState = button.getAttribute("data-state");
  const icon = button.querySelector("i");

  if (currentState === "send") {
    icon.classList.remove("fa-paper-plane");
    icon.classList.add("fa-pause");
    button.setAttribute("data-state", "pause");
  } else {
    icon.classList.remove("fa-pause");
    icon.classList.add("fa-paper-plane");
    button.setAttribute("data-state", "send");
  }
}

function interruptAIResponse() {
  var conversationId = document
    .getElementById("convo-title")
    .getAttribute("data-conversation-id");

  fetch(`/chat/interrupt-stream/${conversationId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken()
    },
    credentials: "same-origin"
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data.message);
      isInterrupted = true;
      toggleButtonState();
    })
    .catch((error) => console.error("Error interrupting the stream:", error));
}

function toggleHistory() {
  document.getElementById("conversation-container").style.display = "block";
  document.getElementById("preference-popup").style.display = "none";
  setActiveButton("show-history-btn");
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
      showToast(successMessage, "success");
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
      showToast(error.message, "error");
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
      showToast(error.message, "error");
    });
}

function updateConversationUI(conversationId, newTitle) {
  requestAnimationFrame(() => {
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

function updateStreamMessageContent(isUserMessage, chunk) {
  requestAnimationFrame(() => {
    if (isUserMessage) {
      window.currentStreamContentDiv.textContent += chunk;
    } else {
      window.currentStreamContentDiv.innerHTML = marked.parse(
        window.incompleteMarkdownBuffer
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
          messageId
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

function togglePreferences() {
  requestAnimationFrame(() => {
    document.getElementById("conversation-container").style.display = "none";
    document.getElementById("preference-popup").style.display = "block";
    setActiveButton("show-preferences-btn");
  });
}

function togglePreferencePopup() {
  requestAnimationFrame(() => {
    var popup = document.getElementById("preference-popup");
    popup.classList.toggle("show");
  });
}

function appendMessageToChatBox(message, className, messageId, images = []) {
  let messageDiv = createMessageDiv(message, className, messageId);
  if (images.length > 0) {
    appendThumbnailsToMessageElement(messageDiv, images);
  }
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

  if (className !== "system-message") {
    let editIcon = messageHeader.querySelector(".fa-edit");
  }
  return messageDiv;
}

function createClipboardIcon(copyTarget) {
  let clipboardIcon = document.createElement("i");
  clipboardIcon.classList.add("fas", "fa-clipboard", "clipboard-icon");
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
      .then(() => {
        console.log("Text copied to clipboard!");
      })
      .catch((err) => {
        console.error("Failed to copy text:", err);
      });
  });

  return clipboardIcon;
}

function removeSubsequentMessagesUI(messageId) {
  if (messageId == null) {
    console.error(
      "removeSubsequentMessagesUI was called with an undefined or null messageId."
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
  performFetch(`/chat/retry-message/${messageId}`, {}).then((response) => {
    if (!response.ok) {
      throw new Error("Failed to retry message.");
    }
    const contentType = response.headers.get("Content-Type");
    if (contentType && contentType.includes("text/plain")) {
      processStreamedResponse(response);
    } else {
      response.text().then((text) => processNonStreamedResponse(text));
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

function appendThumbnailsToMessageElement(messageElement, imageUrls) {
  if (!messageElement || !imageUrls) {
    console.error("Invalid parameters for appendThumbnailsToMessageElement.");
    return;
  }

  // Find the .message-content div within the message element
  const contentDiv = messageElement.querySelector(".message-content");
  if (!contentDiv) {
    console.error("No .message-content div found within the message element.");
    return;
  }

  // For each image URL
  for (let imageUrl of imageUrls) {
    // Create a new img element
    let img = document.createElement("img");

    // Set the src of the new img element to the image URL
    img.src = imageUrl;
    img.classList.add("thumbnail"); // Add CSS class for styling the thumbnails

    // Append the new img element to the .message-content div
    contentDiv.appendChild(img);
  }
}

function saveMessageContent(messageId, newContent) {
  performFetch(`/chat/edit-message/${messageId}`, { content: newContent })
    .then((response) =>
      handleFetchResponse(response, "Message updated successfully")
    )
    .catch((error) => {
      console.error("Failed to update message: " + error.message);
      showToast(error.message, "error");
    });
}

function createMessageHeader(className, messageId) {
  let header = document.createElement("div");
  header.classList.add("message-header");
  messageContent = document.querySelector(".message-content");
  let title = document.createElement("h5");
  title.textContent = getTitleBasedOnClassName(className);
  header.appendChild(title);

  if (className === "assistant-message") {
    let clipboardIcon = createClipboardIcon("message");
    header.appendChild(clipboardIcon);
  }

  if (className === "user-message") {
    let retryIcon = document.createElement("i");
    retryIcon.classList.add("fas", "fa-redo", "retry-icon");
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
  editIcon.classList.add("fas", "fa-edit");
  return editIcon;
}

function processStreamedResponse(response) {
  isInterrupted = false;
  const reader = response.body.getReader();
  readStreamedResponseChunk(reader);
}

function readStreamedResponseChunk(reader) {
  if (isInterrupted) {
    console.log("Response processing was interrupted.");
    finalizeStreamedResponse();
    var conversationId = document
      .getElementById("convo-title")
      .getAttribute("data-conversation-id");
    locateNewMessages(conversationId);
    return;
  }
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
      showToast("Streaming Error: " + error.message, "error");
      console.error("Streaming error:", error);
    });
}

function handleResponseChunk(value) {
  const chunk = new TextDecoder().decode(value);
  if (chunk.startsWith("An error occurred:")) {
    appendMessageToChatBox(chunk, "error");
  } else {
    appendStreamedResponse(chunk, chatBox);
  }
}

function processNonStreamedResponse(text) {
  if (text.includes("An error occurred:")) {
    appendMessageToChatBox(text, "error");
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
  showToast("Fetch Error: " + error.message, "error");
  console.error("Fetch error:", error);
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
    this.contentEditable = "false";
    let conversationId = messageId;
    saveSystemPrompt(conversationId, this.textContent);
  });

  content.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      this.blur();
    }
  });
}

function appendImagesToMessageById(messageId, imageUrls) {
  // Find the message element by its data-message-id attribute
  const messageElement = chatBox.querySelector(
    `[data-message-id="${messageId}"]`
  );
  if (messageElement) {
    // Call the function to append thumbnails to the found message element
    appendThumbnailsToMessageElement(messageElement, imageUrls);
  }
}

function selectConversation(conversationId) {
  updateConversationTitle(conversationId);
  clearChatBox();

  fetchConversationMessages(conversationId)
    .then((messages) => {
      console.log("Loaded conversation messages:", messages);
      messages.forEach((message) => {
        // Use the existing appendMessageToChatBox function to add the message content
        appendMessageToChatBox(
          message.content,
          message.className,
          message.messageId,
          message.images || [] // Pass an empty array if no images are present
        );
      });
      updateCompletionConversationId(conversationId);
    })
    .catch((error) => {
      console.error("Error loading conversation:", error);
    });
}

function updateConversationTitle(conversationId) {
  requestAnimationFrame(() => {
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
  });
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
  requestAnimationFrame(() => {
    chatBox.innerHTML = "";
  });
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
      `.conversation-entry[data-conversation-id="${conversationId}"]`
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
      let messageElements = chatBox.querySelectorAll(
        ".message:not([data-message-id])"
      );

      newMessages.forEach((newMessage) => {
        let matchingElement = Array.from(messageElements).find(
          (messageElement) =>
            messageElement.classList.contains(newMessage.className)
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
  "gpt-4-1106-preview": 4096,
  "gpt-4-vision-preview": 4096,
  "gpt-4": 8192,
  "gpt-4-32k": 32768,
  "gpt-4-0613": 8192,
  "gpt-4-32k-0613": 32768,
  "gpt-4-0314": 8192,
  "gpt-4-32k-0314": 32768,
  "gpt-3.5-turbo-1106": 16385,
  "gpt-3.5-turbo": 4096,
  "gpt-3.5-turbo-16k": 4096
};

document.addEventListener("DOMContentLoaded", function () {
  requestAnimationFrame(() => {
    setupMessageInput();
    initializeToggleButton();
    setupConversationTitleEditing();
    setupModelChangeListener();
    setupChatCompletionForm();
    setupNewConversationForm();
    setupUpdatePreferencesForm();
    setupWindowClick();
    toggleHistory();
    checkConversationHistory();
    setupImageUpload();
  });
  window.isWaitingForResponse = false;

  document.addEventListener("click", function (event) {
    if (event.target.matches(".fa-edit")) {
      const messageDiv = event.target.closest(".message");
      if (messageDiv && !messageDiv.classList.contains("system-message")) {
        const messageId = messageDiv.dataset.messageId;
        const messageContent = messageDiv.querySelector(".message-content");
        setupMessageEditing(messageContent, messageId);
      }
    }
  });

  const conversationHistoryDiv = document.getElementById(
    "conversation-history"
  );
  conversationHistoryDiv.addEventListener("click", function (event) {
    const conversationEntry = event.target.closest(".conversation-entry");
    if (conversationEntry) {
      event.stopPropagation();
      const conversationId = conversationEntry.dataset.conversationId;
    }
  });

  function initializeToggleButton() {
    const toggleButton = document.getElementById("toggle-button");
    if (!toggleButton) return;

    toggleButton.setAttribute("data-state", "send");

    toggleButton.addEventListener("click", function (event) {
      const currentState = this.getAttribute("data-state");

      if (currentState === "send") {
      } else {
        event.preventDefault();
        interruptAIResponse();
        toggleButtonState();
      }
    });
  }

  function toggleHistory() {
    requestAnimationFrame(() => {
      document.getElementById("conversation-container").style.display = "block";
      document.getElementById("preference-popup").style.display = "none";
      setActiveButton("show-history-btn");
    });
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
      showToast(
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
          message.messageId
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

  function setupImageUpload() {
    const modelDropdown = document.getElementById("model");
    toggleImageUploadIcon(modelDropdown.value);
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

  function toggleImageUploadIcon(selectedModel) {
    const imageUploadIcon = document.getElementById("image-upload-icon");
    const chatBox = document.getElementById("chat-box");
    const fileInput = document.getElementById("image-upload");

    const shouldEnable = selectedModel === "gpt-4-vision-preview";
    imageUploadIcon.style.display = shouldEnable ? "block" : "none";

    if (shouldEnable) {
      chatBox.addEventListener("dragover", handleDragOver);
      chatBox.addEventListener("drop", handleDrop);
      chatBox.addEventListener("paste", handlePaste);

      imageUploadIcon.onclick = function () {
        fileInput.click();
      };

      fileInput.onchange = function (event) {
        if (event.target.files && event.target.files[0]) {
          const conversationId = document
            .getElementById("convo-title")
            .getAttribute("data-conversation-id");
          uploadImage(event.target.files[0], conversationId);
        }
      };
    } else {
      chatBox.removeEventListener("dragover", handleDragOver);
      chatBox.removeEventListener("drop", handleDrop);
      chatBox.removeEventListener("paste", handlePaste);

      imageUploadIcon.onclick = null;
      fileInput.onchange = null;
    }
  }

  function uploadImage(file, conversationId) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("conversation_id", conversationId);

    fetch("/chat/upload-chat-image", {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken()
      },
      credentials: "same-origin"
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        if (data.status === "success") {
          showToast("Image uploaded successfully", "success");

          console.log("Uploaded image URL:", data.image_url);
          displayThumbnail(data.image_url);
        } else {
          showToast(data.message, "error");
        }
      })
      .catch((error) => {
        console.error(
          "There has been a problem with your fetch operation:",
          error
        );
        showToast(error.message, "error");
      });
  }

  function displayThumbnail(imageUrl) {
    const thumbnailDiv = document.getElementById("thumbnail-div");

    const img = document.createElement("img");

    img.src = imageUrl;

    img.className = "thumbnail";

    thumbnailDiv.appendChild(img);
  }

  function handleDragOver(event) {
    event.preventDefault();
  }

  function handleDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      console.log("Dropped files:", files);
    }
  }

  function handlePaste(event) {
    const items = (event.clipboardData || event.originalEvent.clipboardData)
      .items;
    for (index in items) {
      const item = items[index];
      if (item.kind === "file") {
        const blob = item.getAsFile();
        console.log("Pasted file:", blob);
      }
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
    const thumbnailDiv = document.getElementById("thumbnail-div");
    const thumbnails = thumbnailDiv.getElementsByTagName("img");
    let imageUrls = [];
    for (let thumbnail of thumbnails) {
      let imageUrl = thumbnail.src;
      imageUrls.push(imageUrl);
    }
    submitChatMessage(messageToSend, form, imageUrls);
    document.getElementById("message-input").value = "";
    thumbnailDiv.innerHTML = "";
  }

  const throttledHandleChatCompletionFormSubmission = throttle(
    handleChatCompletionFormSubmission,
    2000
  );

  function submitChatMessage(message, form, images = []) {
    appendMessageToChatBox(message, "user-message", null, images);
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
      toggleButtonState();
      processStreamedResponse(response);
    } else {
      response.text().then((text) => processNonStreamedResponse(text));
    }
  }

  function processStreamedResponse(response) {
    requestAnimationFrame(() => {
      isInterrupted = false;
      const reader = response.body.getReader();
      readStreamedResponseChunk(reader);
    });
  }

  function readStreamedResponseChunk(reader) {
    if (isInterrupted) {
      console.log("Response processing was interrupted.");
      finalizeStreamedResponse();
      var conversationId = document
        .getElementById("convo-title")
        .getAttribute("data-conversation-id");
      locateNewMessages(conversationId);
      return;
    }
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
      appendMessageToChatBox(chunk, "error");
    } else {
      appendStreamedResponse(chunk, chatBox);
    }
  }

  function processNonStreamedResponse(text) {
    requestAnimationFrame(() => {
      if (text.includes("An error occurred:")) {
        appendMessageToChatBox(text, "error");
      } else {
        try {
          const data = JSON.parse(text);
          appendMessageToChatBox(data.message, "assistant-message");
          var conversationId = document
            .getElementById("convo-title")
            .getAttribute("data-conversation-id");
          locateNewMessages(conversationId);
        } catch (error) {
          showToast("Unexpected response format: " + text, "error");
        }
      }
      window.isWaitingForResponse = false;
    });
  }

  function handleChatCompletionError(error) {
    requestAnimationFrame(() => {
      showToast("Fetch Error: " + error.message, "error");
      console.error("Fetch error:", error);
    });
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
      .catch((error) => showToast("Error: " + error.message, "error"));
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
      system_prompt: data.system_prompt
    });
  }

  function updateConversationListUI(conversationId, conversationTitle) {
    requestAnimationFrame(() => {
      const conversationHistoryDiv = document.getElementById(
        "conversation-history"
      );
      const fragment = document.createDocumentFragment();

      const newConvoEntry = createConversationEntry(
        conversationId,
        conversationTitle
      );

      fragment.appendChild(newConvoEntry);

      conversationHistoryDiv.appendChild(fragment);
      chatBox.innerHTML = "";
    });
  }

  function createConversationEntry(conversationId, conversationTitle) {
    const newConvoEntry = document.createElement("div");
    newConvoEntry.classList.add("conversation-entry");
    newConvoEntry.setAttribute("data-conversation-id", conversationId);
    newConvoEntry.setAttribute("data-conversation-title", conversationTitle);
    newConvoEntry.innerHTML = `<p class="text-entry">${conversationTitle}</p> <span class="delete-conversation" onclick="deleteConversation(${conversationId})"><i class="fas fa-trash-alt"></i></span>`;
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
      .then((data) => {
        processUpdatePreferencesResponse(data);

        setupImageUpload();
      })
      .catch((error) => showToast("Error: " + error.message, "error"));
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
      showToast(data.message, "success");
    } else {
      showToast(data.message, "error");
      console.error(data.errors);
    }
  }

  function setupWindowClick() {
    window.addEventListener("click", function (event) {
      closePreferencePopupOnClick(event);
    });
  }

  function closePreferencePopupOnClick(event) {
    requestAnimationFrame(() => {
      const popup = document.getElementById("preference-popup");
      if (popup && event.target == popup) {
        popup.classList.remove("show");
      }
    });
  }
});
