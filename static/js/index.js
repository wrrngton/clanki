document.addEventListener('DOMContentLoaded', function() {
    const phrasesTextarea = document.getElementById('phrases-textarea');
    const fileUpload = document.getElementById('file-upload');
    const fileName = document.getElementById('file-name');
    const clearFileBtn = document.getElementById('clear-file');
    const submitBtn = document.getElementById('submit-btn');
    const submitText = document.getElementById('submit-text');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const useAiToggle = document.getElementById('use-ai');

    function updateSubmitButton() {
        const hasText = phrasesTextarea.value.trim().length > 0;
        const hasFile = fileUpload.files.length > 0;

        submitBtn.disabled = !(hasText || hasFile);
    }

    function handleInputChange() {
        const hasText = phrasesTextarea.value.trim().length > 0;
        const hasFile = fileUpload.files.length > 0;

        if (hasText) {
            fileUpload.disabled = true;
            fileUpload.parentElement.classList.add('disabled');
        } else {
            fileUpload.disabled = false;
            fileUpload.parentElement.classList.remove('disabled');
        }

        if (hasFile) {
            phrasesTextarea.disabled = true;
            phrasesTextarea.parentElement.classList.add('disabled');
        } else {
            phrasesTextarea.disabled = false;
            phrasesTextarea.parentElement.classList.remove('disabled');
        }

        updateSubmitButton();
    }

    phrasesTextarea.addEventListener('input', handleInputChange);

    fileUpload.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileName.textContent = this.files[0].name;
            clearFileBtn.style.display = 'inline-block';
        } else {
            fileName.textContent = '';
            clearFileBtn.style.display = 'none';
        }
        handleInputChange();
    });

    clearFileBtn.addEventListener('click', function() {
        fileUpload.value = '';
        fileName.textContent = '';
        clearFileBtn.style.display = 'none';
        handleInputChange();
    });

    function showLoading() {
        submitText.style.display = 'none';
        loadingSpinner.style.display = 'inline-flex';
        errorMessage.style.display = 'none'; // Hide any previous errors
        submitBtn.disabled = true;

        phrasesTextarea.disabled = true;
        fileUpload.disabled = true;
        clearFileBtn.disabled = true;
        useAiToggle.disabled = true;
    }

    function hideLoading() {
        submitText.style.display = 'inline';
        loadingSpinner.style.display = 'none';

        handleInputChange();
        useAiToggle.disabled = false;
        clearFileBtn.disabled = false;
    }

    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        hideLoading();
    }

    function downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    document.getElementById('translation-form').addEventListener('submit', function(e) {
        e.preventDefault();

        const hasText = phrasesTextarea.value.trim().length > 0;
        const hasFile = fileUpload.files.length > 0;

        if (!hasText && !hasFile) {
            showError('Please either enter phrases in the text area or upload a file.');
            return;
        }

        if (hasText && hasFile) {
            showError('Please use either the text area OR file upload, not both.');
            return;
        }

        showLoading();

        const formData = new FormData();

        if (hasText) {
            formData.append('phrases', phrasesTextarea.value);
        } else if (hasFile) {
            formData.append('file', fileUpload.files[0]);
        }

        formData.append('use_ai', useAiToggle.checked ? 'on' : 'off');

        fetch('/create-cards', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(text);
                });
            }

            return response.blob();
        })
        .then(blob => {
            downloadFile(blob, 'translation_cards.csv');
            hideLoading();

            phrasesTextarea.value = '';
            fileUpload.value = '';
            fileName.textContent = '';
            clearFileBtn.style.display = 'none';
            handleInputChange();
        })
        .catch(error => {
            showError(error.message || 'An error occurred while processing your request.');
        });
    });

    updateSubmitButton();
});
