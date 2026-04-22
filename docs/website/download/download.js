"use strict";
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".copy-hash[data-hash-id]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var id = btn.getAttribute("data-hash-id");
            var el = document.getElementById(id);
            if (!el) return;
            navigator.clipboard.writeText(el.textContent.trim()).then(function () {
                btn.textContent = "\u2713";
                setTimeout(function () { btn.textContent = "Copy"; }, 1500);
            });
        });
    });
});
