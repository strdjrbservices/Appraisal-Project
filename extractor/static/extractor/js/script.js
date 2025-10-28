document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const loaderOverlay = document.getElementById('loader-overlay');

    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            loaderOverlay.style.display = 'flex';
        });
    }
});