function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
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

function showToast(message, type) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = type;
  toast.style.display = "flex";
  toast.style.opacity = "1";
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.style.display = "none";
    }, 600);
  }, 3000);
}

function setupPromptToggle(formId, radioName, manualGroup, generateGroup) {
  const radioButtons = document.querySelectorAll(
    formId + ' input[name="' + radioName + '"]',
  );
  const manualPromptGroup = document.querySelector(manualGroup);
  const generatePromptGroup = document.querySelector(generateGroup);

  function setupRadioListeners() {
    radioButtons.forEach((radio) => {
      radio.addEventListener("change", (event) => {
        switch (event.target.value) {
          case "manual":
            manualPromptGroup.style.display = "flex";
            generatePromptGroup.style.display = "none";
            break;
          case "generate":
            manualPromptGroup.style.display = "none";
            generatePromptGroup.style.display = "flex";
            break;
          default:
            manualPromptGroup.style.display = "none";
            generatePromptGroup.style.display = "none";
            break;
        }
      });
    });
  }

  // Call the function to setup radio listeners when the form becomes visible
  // For instance, if this setup is triggered by a button click, you might call setupRadioListeners() as part of that click event handler
  setupRadioListeners();

  // Trigger change event on the checked radio button to ensure correct initial display
  const checkedRadioButton = document.querySelector(
    formId + ' input[name="' + radioName + '"]:checked',
  );
  if (checkedRadioButton) {
    checkedRadioButton.dispatchEvent(new Event("change"));
  }
}

function handleFormSubmission(formId, endpoint, isTTS = false) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(form);
    fetch(endpoint, {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          showToast(`${formId} completed successfully.`, "success");
        } else {
          showToast(`Error during ${formId}.`, "error");
        }
      })
      .catch((error) => {
        showToast("An unexpected error occurred." + error, "error");
      });
  });
}

// Handle form submissions for TTS, transcription, and translation
handleFormSubmission("tts-form", "/audio/generate_tts", true); // Pass 'true' for TTS form
handleFormSubmission("transcription-form", "/audio/transcription");
handleFormSubmission("translation-form", "/audio/translation");

// Modify the handlePreferencesFormSubmission function to include debouncing
function handlePreferencesFormSubmission(formId, endpoint) {
  const form = document.getElementById(formId);
  const debouncedSubmit = debounce(function () {
    const formData = new FormData(form);
    fetch(endpoint, {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken(),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          showToast(`Preferences updated successfully.`, "success");
        } else {
          showToast(`Error updating preferences.`, "error");
        }
      })
      .catch((error) => {
        showToast(
          "An unexpected error occurred while updating preferences." + error,
          "error",
        );
      });
  }, 2000); // 2000 milliseconds delay

  form.addEventListener("input", debouncedSubmit);
}

handlePreferencesFormSubmission(
  "tts-preferences-form",
  "/audio/tts_preferences",
);
handlePreferencesFormSubmission(
  "whisper-preferences-form",
  "/audio/whisper_preferences",
);

// Function to remove the 'active' class from all buttons
function removeActiveClassFromButtons() {
  document.querySelectorAll(".utility-toggle i").forEach((icon) => {
    icon.classList.remove("active");
  });
}

// Function to set a button as active
function setActiveButton(buttonElement) {
  removeActiveClassFromButtons();
  if (buttonElement) {
    buttonElement.classList.add("active");
  }
}

function displayUtility(utilityName) {
  // Hide all utilities
  const utilities = document.querySelectorAll(".utility");
  utilities.forEach((utility) => {
    utility.style.display =
      utility.id === `${utilityName}-utility` ? "flex" : "none";
  });

  // Handle TTS preferences form
  const ttsPreferencesForm = document.getElementById("tts-preferences-form");
  if (ttsPreferencesForm)
    ttsPreferencesForm.style.display = utilityName === "tts" ? "flex" : "none";

  // Handle Whisper preferences form
  const whisperPreferencesForm = document.getElementById(
    "whisper-preferences-form",
  );
  if (whisperPreferencesForm) {
    whisperPreferencesForm.style.display =
      utilityName === "transcription" || utilityName === "translation"
        ? "flex"
        : "none";

    // Update the form title based on the utility
    const formTitle = whisperPreferencesForm.querySelector("h3");
    if (formTitle) {
      formTitle.textContent =
        utilityName.charAt(0).toUpperCase() + utilityName.slice(1); // Capitalize the first letter
    }

    // Toggle the language option visibility
    const languageOption = whisperPreferencesForm.querySelector(
      ".form-group.language",
    );
    if (languageOption) {
      languageOption.style.display =
        utilityName === "transcription" ? "block" : "none";
    }
  }
}

// Event listener for utility icons
const utilityIcons = document.querySelectorAll(".utility-toggle i");
utilityIcons.forEach((icon) => {
  icon.addEventListener("click", function () {
    const selectedUtility = this.dataset.utility;
    displayUtility(selectedUtility);
    setActiveButton(this); // Set the clicked icon button as active
  });
});

// Initialize the first utility as active
if (utilityIcons.length > 0) {
  const firstUtilityIcon = utilityIcons[0];
  firstUtilityIcon.click();
  setActiveButton(firstUtilityIcon); // Highlight the first utility button as active
}

// Call setupPromptToggle for WhisperPreferencesForm radio buttons here
setupPromptToggle(
  "#transcription-form",
  "prompt_option",
  "#manual-prompt-group",
  "#generate-prompt-group",
);

// Call setupPromptToggle for WhisperPreferencesForm radio buttons here
setupPromptToggle(
  "#translation-form",
  "prompt_option",
  "#manual-prompt-group",
  "#generate-prompt-group",
);
// eslint-disable-next-line no-unused-vars
function toggleDetails(jobId, jobType) {
  var detailsElement = document.getElementById(jobType + "-details-" + jobId);
  var isVisible = detailsElement.style.display === "block";
  detailsElement.style.display = isVisible ? "none" : "block";
}

function appendJobHistory(job, jobType) {
  // Base URL adjustment based on actual server setup is required
  const baseUrl = window.location.origin;

  // Determine the download URL based on job type
  let downloadUrl;
  switch (jobType) {
    case "tts":
      downloadUrl = `${baseUrl}/audio/download_tts/${job.output_filename}`;
      break;
    case "transcription":
    case "translation":
      downloadUrl = `${baseUrl}/audio/download_whisper/${job.id}`;
      break;
    default:
      console.error("Invalid job type");
      return;
  }

  // Generate the job-specific details, excluding 'language' for 'translation' jobs
  let jobDetailsHtml = "";
  if (jobType === "tts") {
    jobDetailsHtml = `
      <p>Model: ${job.model}</p>
      <p>Speed: ${job.speed}</p>
      <audio controls>
          <source src="${downloadUrl}" type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
    `;
  } else if (jobType === "transcription") {
    jobDetailsHtml = `
      <p>Language: ${job.language}</p>
      <p>Model: ${job.model}</p>
      <p>Temperature: ${job.temperature}</p>
      <p>Prompt: ${job.prompt}</p>
    `;
  } else if (jobType === "translation") {
    jobDetailsHtml = `
      <p>Model: ${job.model}</p>
      <p>Temperature: ${job.temperature}</p>
      <p>Prompt: ${job.prompt}</p>
    `;
  }

  // Create the history entry HTML
  const historyEntryHtml = `
    <li class="history-entry" data-job-id="${job.id}" onclick="toggleDetails('${
      job.id
    }', '${jobType}')">
      <div class="history-summary">
        <span class="history-title">${
          jobType === "tts"
            ? job.voice
            : job.input_filename.substring(0, 10) +
              (job.output_filename && job.output_filename.length > 10
                ? "..."
                : "")
        }</span><br />
        <span class="history-time">${job.created_at}</span>
      </div>
      <div class="history-details" id="${jobType}-details-${
        job.id
      }" style="display: none">
        ${jobDetailsHtml}
        <a href="${downloadUrl}" download>Download ${
          jobType.charAt(0).toUpperCase() + jobType.slice(1)
        }</a>
      </div>
    </li>
  `;

  // Identify the parent element based on job type and append the new history entry
  const parentElementId = `${jobType}-history`;
  const parentElement = document.getElementById(parentElementId);
  if (parentElement) {
    parentElement
      .querySelector("ul")
      .insertAdjacentHTML("beforeend", historyEntryHtml);
  } else {
    console.error("Parent element not found for job type:", jobType);
  }
}

function updateAudioMessages(message, status) {
  var messageDiv = document.getElementById("update-text");
  messageDiv.innerHTML = message.replace(/\n/g, "<br>");
  messageDiv.className = status;
}

// eslint-disable-next-line no-undef
var socket = io("/audio");

// Listen for task progress updates
socket.on("task_progress", function (data) {
  updateAudioMessages(data.message, "information");
});

// Listen for task completion
socket.on("task_complete", function (data) {
  updateAudioMessages(data.message, "success");
  appendJobHistory(data.job_details, data.job_type);
});

// Listen for task errors
socket.on("task_update", function (data) {
  if (data.status === "error") {
    updateAudioMessages("Error: " + data.error, "error");
  }
});
