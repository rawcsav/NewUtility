$(document).ready(function () {
  $("#password-reset-request-form").on("submit", function (event) {
    event.preventDefault();
    var form = $(this);
    $.ajax({
      url: form.attr("action"),
      type: form.attr("method"),
      data: form.serialize(),
      dataType: "json",
      success: function (response) {
        var messageContainer = $("#password-reset-request-message");
        messageContainer.text(response.message);
        if (response.status === "success") {
          messageContainer.removeClass("error").addClass("success");
        } else {
          messageContainer.removeClass("success").addClass("error");
        }
      },
      error: function (xhr, status, error) {
        var messageContainer = $("#password-reset-request-message");
        messageContainer.text("An error occurred: " + xhr.responseText);
        messageContainer.removeClass("success").addClass("error");
      }
    });
  });

  $("#password-reset-form").on("submit", function (event) {
    event.preventDefault();
    var form = $(this);
    $.ajax({
      url: form.attr("action"),
      type: form.attr("method"),
      data: form.serialize(),
      dataType: "json",
      success: function (response) {
        var messageContainer = $("#password-reset-message");
        messageContainer.text(response.message);
        if (response.status === "success") {
          messageContainer.removeClass("error").addClass("success");

          window.location.href = response.redirect;
        } else {
          messageContainer.removeClass("success").addClass("error");

          if (response.redirect) {
            setTimeout(function () {
              window.location.href = response.redirect;
            }, 3000);
          }
        }
      },
      error: function (xhr, status, error) {
        var messageContainer = $("#password-reset-message");
        messageContainer.text("An error occurred: " + xhr.responseText);
        messageContainer.removeClass("success").addClass("error");
      }
    });
  });
});
