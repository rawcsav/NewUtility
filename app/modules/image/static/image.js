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

  toast.style.display = "block";
  toast.style.opacity = "1";

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => {
      toast.style.display = "none";
    }, 600);
  }, 3000);
}

function resizeImage(image) {
  if (image.naturalWidth === 256 && image.naturalHeight === 256) {
    image.style.width = "256px";
    image.style.height = "256px";
  } else if (image.naturalWidth === 512 && image.naturalHeight === 512) {
    image.style.width = "512px";
    image.style.height = "512px";
  }
}

function showLoader() {
  const imageContainer = document.getElementById("generated-images");

  imageContainer.innerHTML =
    document.getElementById("loader-template").innerHTML;

  const loader = imageContainer.querySelector(".loader");
  if (loader) {
    loader.style.display = "block";
  }
}

function hideLoader() {
  const imageContainer = document.getElementById("generated-images");
  const loader = imageContainer.querySelector(".loader");
  if (loader) {
    loader.style.display = "none";
  }
}

document.addEventListener("DOMContentLoaded", function () {
  function toggleModelOptions(model) {
    const numberOfImagesContainer = document.getElementById(
      "number-of-images-container",
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
    nInput.max = model === "dall-e-2" ? 3 : 1;
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
      showLoader();
      var formData = new FormData(this);

      fetch("/image/", {
        method: "POST",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Server returned an error response");
          }
          return response.json();
        })
        .then((data) => {
          if (data.error_message) {
            hideLoader();
            console.error("Server error:", data.error_message);
            showToast(data.error_message, "error");
          } else {
            hideLoader();

            var lastImageMetadata =
              data.image_metadata[data.image_metadata.length - 1];
            var lastImageUrl = data.image_urls[data.image_urls.length - 1];

            var imageId = lastImageMetadata.id; // The ID of the newly generated image
            var displayMetadata = {
              Prompt: lastImageMetadata.prompt,
              Model: lastImageMetadata.model,
              Size: lastImageMetadata.size,
              Quality: lastImageMetadata.quality,
              Style: lastImageMetadata.style,
              Created_at: lastImageMetadata.created_at,
            };
            displayImage(imageId, lastImageUrl, displayMetadata);
            showToast("Image generated successfully!", "success");
            loadImageHistory();
          }
        })
        .catch((error) => {
          hideLoader();
          console.error("Error:", error);
          showToast("Error: " + error.message, "error");
        });
    });
  function loadImageHistory() {
    fetch("/image/history", {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        const carousel = document.getElementById("image-history-carousel");
        carousel.innerHTML = "";
        const limitedData = data.slice(-15);

        limitedData.forEach((item, index) => {
          const imgThumbnail = document.createElement("img");
          imgThumbnail.dataset.src = item.url;
          imgThumbnail.dataset.id = item.id; // Add this line
          imgThumbnail.className = "thumbnail lazy";
          imgThumbnail.alt = `Image History ${index + 1}`;
          imgThumbnail.onclick = () =>
            displayImage(item.id, item.url, {
              Prompt: item.prompt,
              Model: item.model,
              Size: item.size,
              Quality: item.quality,
              Style: item.style,
              Created_at: item.created_at,
            });
          carousel.appendChild(imgThumbnail);
        });

        initializeLazyLoading();
      })
      .catch((error) => {
        console.error("Error loading image history:", error);
      });
  }

  function displayImage(id, imageUrl, metadata) {
    const imageContainer = document.getElementById("generated-images");
    const infoContainer = document.getElementById("img-info-container");
    var iconsContainer = document.getElementById("icons-container");

    imageContainer.innerHTML = "";
    infoContainer.innerHTML = "";
    iconsContainer.innerHTML = "";

    const img = document.createElement("img");
    img.onload = function () {
      resizeImage(img);
    };
    img.src = imageUrl;
    img.alt = "Generated Image";
    imageContainer.appendChild(img);
    iconsContainer.innerHTML = "";
    addDownloadAndOpenIcons(id, iconsContainer);
    addMetadataToInfoContainer(metadata, infoContainer);
  }

  function addDownloadAndOpenIcons(id, container) {
    var downloadLink = document.createElement("a");
    downloadLink.href = `/image/download_image/${id}`;
    downloadLink.innerHTML = '<i class="fas fa-download"></i>';
    downloadLink.className = "image-icon download-icon";
    container.appendChild(downloadLink);

    var openLink = document.createElement("a");
    openLink.href = `/static/user_files/temp_img/${id}.webp`;
    openLink.target = "_blank";
    openLink.innerHTML = '<i class="fas fa-external-link-alt"></i>';
    openLink.className = "image-icon open-icon";
    container.appendChild(openLink);

    var deleteLink = document.createElement("a");
    deleteLink.href = "#"; // Prevent navigation
    deleteLink.innerHTML = '<i class="fas fa-trash"></i>'; // Use appropriate trash icon class
    deleteLink.className = "image-icon delete-icon";
    deleteLink.addEventListener("click", function (event) {
      event.preventDefault(); // Prevent the default anchor behavior
      markImageAsDeleted(id); // Call the function to mark the image as deleted
    });
    container.appendChild(deleteLink);
  }

  function markImageAsDeleted(imageId) {
    fetch(`/image/mark_delete/${imageId}`, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ delete: true }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        if (data.status === "success") {
          showToast("Image marked for deletion", "success");
          // Remove the image from the history carousel
          const thumbnailToRemove = document.querySelector(
            `img[data-id="${imageId}"]`,
          );
          if (thumbnailToRemove) {
            thumbnailToRemove.remove();
          }
          const displayedImage = document
            .getElementById("generated-images")
            .querySelector("img");
          if (displayedImage && displayedImage.src.includes(imageId)) {
            document.getElementById("generated-images").innerHTML = "";
            document.getElementById("icons-container").innerHTML = "";
            document.getElementById("img-info-container").innerHTML = "";
          }
        } else {
          showToast("Failed to mark image for deletion", "error");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showToast("Error: " + error.message, "error");
      });
  }

  function addMetadataToInfoContainer(metadata, container) {
    const metadataList = document.createElement("ul");
    metadataList.className = "image-metadata";

    Object.entries(metadata).forEach(([key, value]) => {
      const listItem = document.createElement("li");

      // Create a span for the key with the 'metadata-key' class
      const keySpan = document.createElement("span");
      keySpan.textContent = `${key}: `;
      keySpan.className = "metadata-key";
      listItem.appendChild(keySpan);

      // Create a span for the value and apply the 'metadata-value' class
      const valueSpan = document.createElement("span");
      valueSpan.textContent = value;
      valueSpan.className = "metadata-value"; // Apply the CSS class
      listItem.appendChild(valueSpan); // Append the value span to the list item

      metadataList.appendChild(listItem);
    });

    container.appendChild(metadataList);
  }

  function initializeLazyLoading() {
    const lazyImages = document.querySelectorAll(".lazy");

    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const image = entry.target;
          image.src = image.dataset.src;
          image.classList.remove("lazy");
          observer.unobserve(image);
        }
      });
    });

    lazyImages.forEach((image) => {
      imageObserver.observe(image);
    });
  }

  loadImageHistory();
});
