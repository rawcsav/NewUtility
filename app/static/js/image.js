document.addEventListener("DOMContentLoaded", function () {
  // Function to display messages related to image generation
  function updateImageGenerationMessages(message, status) {
    var messageDiv = document.getElementById("image-generation-messages");
    messageDiv.textContent = message; // Set the message text
    messageDiv.className = status; // Set the class for styling based on status
  }

  // Function to toggle visibility of DALL-E 3 additional options
  function toggleDallE3Options(model) {
    const dallE3Options = document.getElementById("dall-e-3-options");
    if (model === "dall-e-3") {
      dallE3Options.style.display = "flex"; // Show DALL-E 3 options
    } else {
      dallE3Options.style.display = "none"; // Hide DALL-E 3 options
    }
  }
  function updateSizeOptions(model) {
    const sizeSelect = document.getElementById("size");
    sizeSelect.innerHTML = ""; // Clear existing options
    const sizeOptions =
      model === "dall-e-2"
        ? ["256x256", "512x512", "1024x1024"]
        : ["1024x1024", "1792x1024", "1024x1792"];
    sizeOptions.forEach((size) => {
      const option = document.createElement("option");
      option.value = size;
      option.text = size;
      sizeSelect.appendChild(option);
    });
  }

  // Function to update the maximum 'n' value based on the selected model
  function updateMaxImages(model) {
    const nInput = document.getElementById("n");
    nInput.max = model === "dall-e-2" ? 10 : 1;
    nInput.value = Math.min(nInput.value, nInput.max); // Reset the value if it exceeds the max
  }

  // Function to update the maximum prompt length value based on the selected model
  function updatePromptLength(model) {
    const promptInput = document.getElementById("prompt");
    promptInput.maxLength = model === "dall-e-2" ? 1000 : 4000;
  }

  // Event listener for model selection changes
  document.getElementById("model").addEventListener("change", function (event) {
    const selectedModel = event.target.value;
    updateSizeOptions(selectedModel);
    updateMaxImages(selectedModel);
    updatePromptLength(selectedModel);
    toggleDallE3Options(selectedModel); // Toggle DALL-E 3 options
  });

  const currentSelectedModel = document.getElementById("model").value;
  updateSizeOptions(currentSelectedModel);
  updateMaxImages(currentSelectedModel);
  updatePromptLength(currentSelectedModel);
  toggleDallE3Options(currentSelectedModel); // Toggle DALL-E 3 options initially
  document
    .getElementById("image-generation-form")
    .addEventListener("submit", function (event) {
      event.preventDefault(); // Prevent the default form submission

      var formData = new FormData(this); // Create a FormData object from the form

      // Send the form data using the fetch API
      fetch("/image/generate_image", {
        method: "POST",
        headers: {
          "X-CSRFToken": formData.get("csrf_token"), // Include the CSRF token in the request headers
          "X-Requested-With": "XMLHttpRequest" // Indicate that this is an AJAX request
        },
        body: formData // Send the form data
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server returned an error response");
          }
          return response.json();
        })
        .then((data) => {
          if (data.error_message) {
            // Handle server-reported errors
            console.error("Server error:", data.error_message);
            updateImageGenerationMessages(data.error_message, "error");
          } else {
            // Handle success, update image URLs display
            console.log("Image generation successful:", data);

            // Assuming 'data' object has an 'image_urls' array containing URLs of the generated images
            var imageContainer = document.getElementById("generated-images");
            imageContainer.innerHTML = ""; // Clear existing images

            data.image_urls.forEach(function (imageUrl) {
              var img = document.createElement("img");
              img.src = imageUrl;
              imageContainer.appendChild(img);
            });

            updateImageGenerationMessages(
              "Images generated successfully!",
              "success"
            );
          }
        })
        .catch((error) => {
          // Handle errors related to making the request
          console.error("Error:", error);
          updateImageGenerationMessages("Error: " + error.message, "error");
        });
    });

  // Initialize the form with DALL-E 2 options by default
  updateSizeOptions("dall-e-3");
});
