function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFToken() {
    return getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Set up AJAX to always send CSRF token
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', '/set-csrf-cookie/', true);
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
            xhr.withCredentials = true;
            xhr.send();
        }
    });
})();