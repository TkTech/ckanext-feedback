document.addEventListener("DOMContentLoaded", function () {
  // Star rating handler — radios are in natural DOM order (1..5). The fill
  // state is driven by JS toggling `.is-filled` on the labels so the CSS
  // can stay simple and the browser's built-in radio-group keyboard
  // navigation (Left/Right arrows) just works.
  var widget = document.querySelector(".feedback-rating-widget");
  if (widget) {
    var rateUrl = widget.getAttribute("data-rate-url");
    var fieldset = widget.querySelector(".feedback-stars");
    var radios = Array.prototype.slice.call(
      widget.querySelectorAll(".feedback-star-input")
    );
    var labels = Array.prototype.slice.call(
      widget.querySelectorAll(".feedback-star-label")
    );
    var avgEl = widget.querySelector(".feedback-avg");
    var countEl = widget.querySelector(".feedback-count");

    function applyFill(count) {
      labels.forEach(function (label, idx) {
        if (idx < count) {
          label.classList.add("is-filled");
        } else {
          label.classList.remove("is-filled");
        }
      });
    }

    function currentRating() {
      var checked = widget.querySelector(".feedback-star-input:checked");
      return checked ? parseInt(checked.value, 10) : 0;
    }

    // Initial paint based on the user's existing rating (if any).
    applyFill(currentRating());

    // Hover preview — fill up to the hovered label.
    labels.forEach(function (label, idx) {
      label.addEventListener("mouseenter", function () {
        applyFill(idx + 1);
      });
    });
    if (fieldset) {
      fieldset.addEventListener("mouseleave", function () {
        applyFill(currentRating());
      });
    }

    // Keyboard preview — when focus moves to a radio, light up to that one.
    radios.forEach(function (radio, idx) {
      radio.addEventListener("focus", function () {
        applyFill(idx + 1);
      });
    });
    if (fieldset) {
      fieldset.addEventListener("focusout", function (e) {
        // Only revert to the saved rating if focus actually left the
        // fieldset, not when it merely moved between radios inside it.
        if (!fieldset.contains(e.relatedTarget)) {
          applyFill(currentRating());
        }
      });
    }

    // Submit the rating on change.
    radios.forEach(function (radio) {
      radio.addEventListener("change", function () {
        if (!this.checked) return;
        var val = parseInt(this.value, 10);
        applyFill(val);

        var csrfInput = document.querySelector(
          'input[name="csrf_token"], input[name="_csrf_token"]'
        );
        var csrfToken = csrfInput ? csrfInput.value : "";

        var formData = new FormData();
        formData.append("rating", val);
        if (csrfToken) {
          formData.append("csrf_token", csrfToken);
          formData.append("_csrf_token", csrfToken);
        }

        fetch(rateUrl, {
          method: "POST",
          credentials: "same-origin",
          body: formData,
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (data.error) return;
            if (avgEl) avgEl.textContent = data.average;
            if (countEl) countEl.textContent = data.count;
            widget.setAttribute("data-user-rating", data.user_rating);
            applyFill(data.user_rating);
          });
      });
    });
  }

  // Server-side validation error list — focus it on load so screen readers
  // and sighted keyboard users land on the errors immediately.
  var errorList = document.querySelector(".feedback-form-errors");
  if (errorList) {
    errorList.setAttribute("tabindex", "-1");
    errorList.focus();
    errorList.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // reCAPTCHA loader.
  var form = document.querySelector(
    ".feedback-submission-form[data-recaptcha-sitekey]"
  );
  if (form) {
    var sitekey = form.getAttribute("data-recaptcha-sitekey");
    var container = document.getElementById("feedback-recaptcha");
    if (sitekey && container) {
      var script = document.createElement("script");
      script.src =
        "https://www.google.com/recaptcha/api.js?onload=feedbackRecaptchaReady&render=explicit";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);

      window.feedbackRecaptchaReady = function () {
        grecaptcha.render("feedback-recaptcha", { sitekey: sitekey });
      };
    }
  }
});
