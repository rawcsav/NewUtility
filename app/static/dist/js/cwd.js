document.addEventListener("DOMContentLoaded", (event) => {
  let controller = new AbortController();
  let signal = controller.signal;

  function getCsrfToken() {
    return document
      .querySelector('meta[name="csrf-token"]')
      .getAttribute("content");
  }

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

  document.addEventListener("DOMContentLoaded", function () {
    const queryInput = document.getElementById("query");
    queryInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        queryDocument();
      }
    });
  });

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
      submitForm(formData, submitUrl)
        .then(successCallback)
        .catch(errorCallback);
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
    "docs-preferences-form",
    "/embedding/update-doc-preferences",
    handleResponse,
    (error) => showToast("Error: " + error.message, "error"),
  );

  let previousQuery = null;
  let previousResponse = null;

  function addToQueryHistory(query, response) {
    const queryResultsSection = document.getElementById(
      "query-results-section",
    );
    const currentQueryResponse = document.getElementById("current-query");

    // Create a new history entry
    const historyEntry = document.createElement("div");
    historyEntry.className = "history-entry";
    historyEntry.innerHTML = `
    <strong>Query:</strong> <pre>${query}</pre><br><br>
    <strong>Response:</strong> <pre>${response}</pre>
    <hr class="history-delimiter">  <!-- This is the delimiter -->
  `;

    // Insert the history entry before the current query-response
    queryResultsSection.insertBefore(historyEntry, currentQueryResponse);

    // Update the current query-response
    document.getElementById("user_query").textContent = "";
    document.getElementById("results").textContent = "";

    // Set the display of the query and response elements to none
    document.getElementById("user_query").parentNode.style.display = "none";
    document.getElementById("response_container").style.display = "none";
  }

  async function queryDocument() {
    document.getElementById("interruptButton").disabled = false;

    const query = document.getElementById("query").value.trim();
    if (query === "") {
      showToast("Query cannot be empty.", "warning");
      return;
    }

    const userQueryElement = document.getElementById("user_query");
    userQueryElement.parentNode.style.display = "block";
    userQueryElement.textContent = query;
    document.getElementById("query").value = "";

    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = "<pre></pre>";

    // Update previousQuery for the next iteration
    previousQuery = query;
    previousResponse = "";

    try {
      const response = await fetch("/cwd/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": getCsrfToken(),
        },
        body: `query=${encodeURIComponent(query)}`,
        signal: signal,
      });

      if (response.ok) {
        const reader = response.body.getReader();
        let decoder = new TextDecoder();
        const responseLabelContainer =
          document.getElementById("response_container");
        const resultsSpan = document.getElementById("results");
        responseLabelContainer.style.display = "block";
        while (true) {
          const { value, done } = await reader.read();
          if (done) {
            break;
          }
          resultsSpan.textContent += decoder.decode(value);
          previousResponse += decoder.decode(value);
        }

        // At this point, the whole response has been read
        document.getElementById("results").textContent = previousResponse;

        // Add the query and response to the history as soon as they are completed
        addToQueryHistory(previousQuery, previousResponse);

        // Reset previousResponse for the next request
        previousResponse = "";
      } else {
        showToast("Error occurred while querying.", "error");
      }
    } catch (error) {
      if (error.name === "AbortError") {
        showToast("Interrupted!", "warning");
      } else {
        showToast("Error occurred while querying.", "error");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const selectAllCheckbox = document.getElementById("select-all");
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", function () {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
          if (checkbox !== selectAllCheckbox) {
            checkbox.checked = selectAllCheckbox.checked;
          }
        });
      });
    }
  });

  function selectAll() {
    let selectAllCheckbox = document.getElementById("select-all");
    let checkboxes = document.querySelectorAll('input[type="checkbox"]');

    // Iterate over all checkboxes and set their checked state to match the "select all" checkbox
    checkboxes.forEach((checkbox) => {
      if (checkbox !== selectAllCheckbox) {
        // Ensure we're not toggling the "select all" checkbox itself
        checkbox.checked = selectAllCheckbox.checked;
      }
    });
  }

  // eslint-disable-next-line no-unused-vars
  function interruptQuery() {
    controller.abort();
    controller = new AbortController();
    signal = controller.signal;

    const resultsSpan = document.getElementById("results");
    if (resultsSpan.lastChild) {
      resultsSpan.removeChild(resultsSpan.lastChild);
    }

    document.getElementById("interruptButton").disabled = true;
    document.getElementById("queryButton").disabled = false;
  }
});
