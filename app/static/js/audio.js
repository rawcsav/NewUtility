function getCsrfToken() {
  return document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
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

function handlePreferencesFormSubmission(formId, endpoint) {
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
  });
}

// Handle form submissions for TTS and Whisper preferences
handlePreferencesFormSubmission(
  "tts-preferences-form",
  "/audio/tts_preferences",
);
handlePreferencesFormSubmission(
  "whisper-preferences-form",
  "/audio/whisper_preferences",
);

const utilityIcons = document.querySelectorAll(".utility-toggle i");
const utilities = document.querySelectorAll(".utility");
const ttsPreferencesForm = document.getElementById("tts-preferences-form");
const whisperPreferencesForm = document.getElementById(
  "whisper-preferences-form",
);
let languageOption;

utilityIcons.forEach((icon) => {
  icon.addEventListener("click", function () {
    const selectedUtility = this.dataset.utility;
    utilities.forEach((utility) => {
      utility.style.display = "none"; // Hide all utilities by default
    });
    document.getElementById(selectedUtility + "-utility").style.display =
      "flex"; // Show the selected utility

    // Hide both preferences forms by default
    if (ttsPreferencesForm) ttsPreferencesForm.style.display = "none";
    if (whisperPreferencesForm) whisperPreferencesForm.style.display = "none";

    // Show the appropriate preferences form based on the selected utility
    if (selectedUtility === "tts") {
      ttsPreferencesForm.style.display = "flex";
    } else if (
      selectedUtility === "transcription" ||
      selectedUtility === "translation"
    ) {
      whisperPreferencesForm.style.display = "flex";
      // Initialize the language option selector when whisperPreferencesForm is visible
      languageOption =
        languageOption ||
        whisperPreferencesForm.querySelector(".form-group.language");
      // Toggle language option based on utility
      languageOption.style.display =
        selectedUtility === "transcription" ? "flex" : "none";

      // Call setupPromptToggle for WhisperPreferencesForm radio buttons here
      setupPromptToggle(
        "#whisper-preferences-form",
        "prompt_option",
        "#manual-prompt-group",
        "#generate-prompt-group",
      );
    }
  });
});

// Trigger click on the first utility icon to display the initial utility
if (utilityIcons.length > 0) utilityIcons[0].click();

function toggleDetails(jobId, jobType) {
  var detailsElement = document.getElementById(jobType + "-details-" + jobId);
  var isVisible = detailsElement.style.display === "block";
  detailsElement.style.display = isVisible ? "none" : "block";
}

// Function to append a transcription job to the transcription history list
function appendTranscriptionJobToHistory(job) {
  const historyList = document
    .getElementById("transcription-history")
    .querySelector("ul");
  const newHistoryEntry = document.createElement("li");
  newHistoryEntry.className = "history-entry";
  newHistoryEntry.dataset.jobId = job.id;
  newHistoryEntry.setAttribute(
    "onclick",
    `toggleDetails('${job.id}', 'transcription')`,
  );
  newHistoryEntry.innerHTML = `
    <div class="history-summary">
      ${job.created_at} - ${job.input_filename}
    </div>
    <div class="history-details" id="transcription-details-${job.id}" style="display: none">
      <p>Language: ${job.language}</p>
      <p>Model: ${job.model}</p>
      <p>Temperature: ${job.temperature}</p>
      <p>Prompt: ${job.prompt}</p>
      <a href="${job.download_url}" download>
        <i class="fas fa-download"></i> Download Transcription
      </a>
    </div>
  `;
  historyList.appendChild(newHistoryEntry);
}

// Function to append a translation job to the translation history list
function appendTranslationJobToHistory(job) {
  const historyList = document
    .getElementById("translation-history")
    .querySelector("ul");
  const newHistoryEntry = document.createElement("li");
  newHistoryEntry.className = "history-entry";
  newHistoryEntry.dataset.jobId = job.id;
  newHistoryEntry.setAttribute(
    "onclick",
    `toggleDetails('${job.id}', 'translation')`,
  );
  newHistoryEntry.innerHTML = `
    <div class="history-summary">
      ${job.created_at} - ${job.input_filename}
    </div>
    <div class="history-details" id="translation-details-${job.id}" style="display: none">
      <p>Model: ${job.model}</p>
      <p>Temperature: ${job.temperature}</p>
      <p>Prompt: ${job.prompt}</p>
      <a href="${job.download_url}" download>
        <i class="fas fa-download"></i> Download Translation
      </a>
    </div>
  `;
  historyList.appendChild(newHistoryEntry);
}

// Function to append a TTS job to the TTS history list
function appendTtsJobToHistory(job) {
  const historyList = document
    .getElementById("tts-history")
    .querySelector("ul");
  const newHistoryEntry = document.createElement("li");
  newHistoryEntry.className = "history-entry";
  newHistoryEntry.dataset.jobId = job.id;
  newHistoryEntry.setAttribute("onclick", `toggleDetails('${job.id}', 'tts')`);
  newHistoryEntry.innerHTML = `
    <div class="history-summary">
      ${job.created_at} - ${job.voice}
    </div>
    <div class="history-details" id="tts-details-${job.id}" style="display: none">
      <p>Model: ${job.model}</p>
      <p>Speed: ${job.speed}</p>
      <audio controls>
        <source src="${job.download_url}" type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
      <a href="${job.download_url}" download>Download Audio</a>
    </div>
  `;
  historyList.appendChild(newHistoryEntry);
}
