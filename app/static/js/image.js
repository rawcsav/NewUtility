function resizeImage(image) {
  if (image.naturalWidth === 256 && image.naturalHeight === 256) {
    image.style.width = "256px";
    image.style.height = "256px";
  } else if (image.naturalWidth === 512 && image.naturalHeight === 512) {
    image.style.width = "512px";
    image.style.height = "512px";
  }
}
document.addEventListener("DOMContentLoaded", function () {
  function updateImageGenerationMessages(message, status) {
    var messageDiv = document.getElementById("image-generation-messages");
    messageDiv.textContent = message;
    messageDiv.className = status;
  }

  function toggleModelOptions(model) {
    const numberOfImagesContainer = document.getElementById(
      "number-of-images-container"
    );
    const dallE3Options = document.getElementById("dall-e-3-options");

    if (model === "dall-e-3") {
      dallE3Options.style.display = "flex";
      numberOfImagesContainer.style.display = "none";
    } else if (model === "dall-e-2") {
      dallE3Options.style.display = "none";
      numberOfImagesContainer.style.display = "flex";
    }
  }

  function updateSizeOptions(model) {
    const sizeSelect = document.getElementById("size");
    sizeSelect.innerHTML = "";
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

  function updateMaxImages(model) {
    const nInput = document.getElementById("n");
    nInput.max = model === "dall-e-2" ? 10 : 1;
    nInput.value = Math.min(nInput.value, nInput.max);
  }

  function updatePromptLength(model) {
    const promptInput = document.getElementById("prompt");
    promptInput.maxLength = model === "dall-e-2" ? 1000 : 4000;
  }

  document.getElementById("model").addEventListener("change", function (event) {
    const selectedModel = event.target.value;
    updateSizeOptions(selectedModel);
    updateMaxImages(selectedModel);
    updatePromptLength(selectedModel);
    toggleModelOptions(selectedModel);
  });

  const currentSelectedModel = document.getElementById("model").value;
  updateSizeOptions(currentSelectedModel);
  updateMaxImages(currentSelectedModel);
  updatePromptLength(currentSelectedModel);
  toggleModelOptions(currentSelectedModel);
  document
    .getElementById("image-generation-form")
    .addEventListener("submit", function (event) {
      event.preventDefault();
      showLoader(); // Call this to show the loader

      var formData = new FormData(this);

      fetch("/image/generate_image", {
        method: "POST",
        headers: {
          "X-CSRFToken": formData.get("csrf_token"),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: formData
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server returned an error response");
          }
          return response.json();
        })
        .then((data) => {
          if (data.error_message) {
            hideLoader(); // Call this to hide the loader once images are loaded
            console.error("Server error:", data.error_message);
            updateImageGenerationMessages(data.error_message, "error");
          } else {
            hideLoader(); // Call this to hide the loader once images are loaded
            var imageContainer = document.getElementById("generated-images");
            imageContainer.innerHTML = "";
            var iconsContainer = document.getElementById("icons-container");
            iconsContainer.innerHTML = ""; // Clear previous icons
            data.image_urls.forEach(function (imageUrl) {
              var downloadLink = document.createElement("a");
              downloadLink.href = `/image/download_image/${encodeURIComponent(
                imageUrl
              )}`; // Point href to the Flask download route
              downloadLink.innerHTML = '<i class="fas fa-download"></i>';
              downloadLink.className = "image-icon download-icon";
              iconsContainer.appendChild(downloadLink);

              var openLink = document.createElement("a");
              openLink.href = imageUrl;
              openLink.target = "_blank";
              openLink.innerHTML = '<i class="fas fa-external-link-alt"></i>';
              openLink.className = "image-icon open-icon";
              iconsContainer.appendChild(openLink);

              var img = document.createElement("img");
              img.onload = function () {
                resizeImage(img);
              };
              img.src = imageUrl;
              img.alt = "Generated Image";

              imageContainer.appendChild(img);
            });

            updateImageGenerationMessages(
              "Images generated successfully!",
              "success"
            );
          }
        })
        .catch((error) => {
          hideLoader(); // Call this to hide the loader once images are loaded

          console.error("Error:", error);
          updateImageGenerationMessages("Error: " + error.message, "error");
        });
    });
});
