(function () {
  "use strict";

  const input = document.getElementById("id_avatar");
  const preview = document.getElementById("avatar-preview");
  const fallback = document.getElementById("avatar-preview-fallback");
  if (!input || !preview || !fallback) {
    return;
  }

  let previewUrl = null;
  input.addEventListener("change", function () {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
    const file = input.files && input.files[0];
    if (!file || !file.type.startsWith("image/")) {
      return;
    }
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    fallback.hidden = true;
  });

  window.addEventListener("beforeunload", function () {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  });
})();
