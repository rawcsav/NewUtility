// Utility functions
const utils = {
  getCsrfToken() {
    return document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content");
  },

  checkForBot() {
    if (document.getElementById("middle-name")?.value) {
      console.error("Bot submission detected.");
      return true;
    }
    return false;
  },

  handleMessageContainer(containerId, message, type, isHTML = false) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (isHTML) {
      container.innerHTML = message;
    } else {
      container.textContent = message;
    }

    container.classList.remove("success", "error");
    container.classList.add(type);
  },

  handleRedirect(url, delay = 0) {
    if (url) {
      setTimeout(() => {
        window.location.href = url;
      }, delay);
    }
  },
};

// Form submission handlers
const formHandlers = {
  async submitForm(formData, endpoint) {
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "X-CSRFToken": utils.getCsrfToken(),
        },
        body: formData,
      });
      return await response.json();
    } catch (error) {
      console.error("Submission error:", error);
      throw error;
    }
  },

  handleAuthResponse(data, messageContainerId, options = {}) {
    const { redirectDelay = 0, unconfirmedTemplate } = options;

    switch (data.status) {
      case "success": {
        utils.handleMessageContainer(
          messageContainerId,
          data.message,
          "success",
        );
        utils.handleRedirect(data.redirect, redirectDelay);
        break;
      }

      case "unconfirmed": {
        if (unconfirmedTemplate) {
          utils.handleMessageContainer(
            messageContainerId,
            unconfirmedTemplate(data.redirect),
            "error",
            true,
          );
        }
        break;
      }

      case "error": {
        const errorMessage = data.errors
          ? Object.values(data.errors).flat().join("<br>")
          : data.message;
        utils.handleMessageContainer(
          messageContainerId,
          errorMessage,
          "error",
          true,
        );
        break;
      }

      default: {
        utils.handleMessageContainer(messageContainerId, data.message, "error");
      }
    }
  },

  handleError(error, messageContainerId, customMessage) {
    console.error("Error:", error);
    utils.handleMessageContainer(
      messageContainerId,
      customMessage || "An unexpected error occurred.",
      "error",
    );
  },
};

// Initialize auth forms
function initializeAuthForms() {
  // Login Form
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (utils.checkForBot()) return;

      const formData = new FormData(loginForm);
      const remember = document.getElementById("remember")?.checked;
      if (remember !== undefined) {
        formData.set("remember", remember ? "true" : "false");
      }

      try {
        const data = await formHandlers.submitForm(formData, "/auth/login");
        formHandlers.handleAuthResponse(data, "message-container", {
          unconfirmedTemplate: (redirect) =>
            `<p>Please confirm your email. <a href="${redirect}">Click here to confirm</a></p>`,
        });
      } catch (error) {
        formHandlers.handleError(
          error,
          "message-container",
          "An error occurred while trying to log in.",
        );
      }
    });
  }

  // Signup Form
  const signupForm = document.getElementById("signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (utils.checkForBot()) return;

      try {
        const data = await formHandlers.submitForm(
          new FormData(signupForm),
          "/auth/signup",
        );
        formHandlers.handleAuthResponse(data, "message-container");
      } catch (error) {
        formHandlers.handleError(
          error,
          "message-container",
          "An error occurred while trying to sign up.",
        );
      }
    });
  }

  // Email Confirmation Form
  const confirmEmailForm = document.getElementById("confirm-email-form");
  if (confirmEmailForm) {
    confirmEmailForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (utils.checkForBot()) return;

      try {
        const data = await formHandlers.submitForm(
          new FormData(confirmEmailForm),
          "/auth/confirm_email",
        );
        formHandlers.handleAuthResponse(data, "message-container", {
          redirectDelay: 5000,
        });
      } catch (error) {
        formHandlers.handleError(
          error,
          "message-container",
          "An error occurred while trying to confirm your email.",
        );
      }
    });
  }

  // Password Reset Forms
  function initializePasswordResetForms() {
    const passwordResetRequestForm = document.getElementById(
      "password-reset-request-form",
    );
    const passwordResetForm = document.getElementById("password-reset-form");

    async function handlePasswordResetSubmit(
      form,
      messageContainerId,
      shouldRedirect,
    ) {
      if (utils.checkForBot()) return;

      try {
        const data = await formHandlers.submitForm(
          new FormData(form),
          form.action,
        );
        formHandlers.handleAuthResponse(data, messageContainerId, {
          redirectDelay: shouldRedirect ? 3000 : 0,
        });
      } catch (error) {
        formHandlers.handleError(error, messageContainerId);
      }
    }

    if (passwordResetRequestForm) {
      passwordResetRequestForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handlePasswordResetSubmit(
          passwordResetRequestForm,
          "password-reset-request-message",
          false,
        );
      });
    }

    if (passwordResetForm) {
      passwordResetForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handlePasswordResetSubmit(
          passwordResetForm,
          "password-reset-message",
          true,
        );
      });
    }
  }

  initializePasswordResetForms();
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", initializeAuthForms);
