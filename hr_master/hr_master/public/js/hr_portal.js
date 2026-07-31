/* HR Master — Recruiting Portal helpers */
(function () {
	"use strict";

	document.addEventListener("DOMContentLoaded", function () {
		// Auto-dismiss flash alerts after 5 seconds
		document.querySelectorAll(".hrp-alert[data-dismiss]").forEach(function (el) {
			setTimeout(function () {
				el.style.transition = "opacity 0.4s ease";
				el.style.opacity = "0";
				setTimeout(function () { el.remove(); }, 400);
			}, 5000);
		});

		// Confirm dialog for destructive / state-changing actions
		document.querySelectorAll("form[data-confirm]").forEach(function (form) {
			form.addEventListener("submit", function (e) {
				var message = form.getAttribute("data-confirm") || "Are you sure?";
				if (!window.confirm(message)) {
					e.preventDefault();
				}
			});
		});

		// Loading state on submit buttons
		document.querySelectorAll("form").forEach(function (form) {
			form.addEventListener("submit", function () {
				var btn = form.querySelector('button[type="submit"]');
				if (btn && !btn.disabled) {
					btn.disabled = true;
					btn.textContent = "Working…";
				}
			});
		});
	});
})();
