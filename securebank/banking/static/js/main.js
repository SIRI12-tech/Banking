document.addEventListener('DOMContentLoaded', function() {
    // CSRF token handling
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
    const csrftoken = getCookie('csrftoken');

    function setCSRFToken(xhr) {
        if (csrftoken) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }

    // AJAX request helper function
    function ajaxRequest(url, method, data, successCallback, errorCallback) {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url, true);
        setCSRFToken(xhr);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                successCallback(JSON.parse(xhr.responseText));
            } else {
                errorCallback(xhr.statusText);
            }
        };
        xhr.onerror = function() {
            errorCallback('Network Error');
        };
        xhr.send(JSON.stringify(data));
    }

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
            
            // Add CSRF token to the form if it doesn't exist
            if (!form.querySelector('input[name="csrfmiddlewaretoken"]')) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrftoken;
                form.appendChild(csrfInput);
            }
        }, false);
    });

    // Loading animation functions
    function showLoading() {
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
        document.body.appendChild(loadingOverlay);
    }

    function hideLoading() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }

    // Show loading animation when submitting forms
    const allForms = document.querySelectorAll('form');
    allForms.forEach(form => {
        form.addEventListener('submit', function() {
            showLoading();
        });
    });

    // Hide loading animation when page is fully loaded
    window.addEventListener('load', function() {
        hideLoading();
    });

    // Show loading animation when clicking on links
    document.addEventListener('click', function(event) {
        const target = event.target.closest('a');
        if (target && !target.getAttribute('href').startsWith('#') && !target.getAttribute('href').startsWith('javascript:')) {
            showLoading();
        }
    });

    // Password strength meter functionality
    const passwordInput = document.getElementById('id_password1');
    if (passwordInput) {
        const passwordStrength = document.getElementById('password-strength');
        const passwordStrengthText = document.getElementById('password-strength-text');

        passwordInput.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            updatePasswordStrengthMeter(strength);
        });

        function calculatePasswordStrength(password) {
            let strength = 0;
            if (password.length >= 8) strength++;
            if (password.match(/[a-z]+/)) strength++;
            if (password.match(/[A-Z]+/)) strength++;
            if (password.match(/[0-9]+/)) strength++;
            if (password.match(/[$@#&!]+/)) strength++;
            return strength;
        }

        function updatePasswordStrengthMeter(strength) {
            passwordStrength.style.width = (strength / 5) * 100 + '%';
            
            switch (strength) {
                case 0:
                case 1:
                    passwordStrength.className = 'progress-bar bg-danger';
                    passwordStrengthText.textContent = 'Weak';
                    break;
                case 2:
                case 3:
                    passwordStrength.className = 'progress-bar bg-warning';
                    passwordStrengthText.textContent = 'Moderate';
                    break;
                case 4:
                case 5:
                    passwordStrength.className = 'progress-bar bg-success';
                    passwordStrengthText.textContent = 'Strong';
                    break;
            }
        }
    }

    // Transaction type toggle
    const transactionType = document.getElementById('id_transaction_type');
    const amountLabel = document.getElementById('amount-label');
    if (transactionType && amountLabel) {
        transactionType.addEventListener('change', function() {
            amountLabel.textContent = this.value === 'DEPOSIT' ? 'Deposit Amount' : 'Withdrawal Amount';
        });
    }

    // TOTP QR code display
    const setupTOTPBtn = document.getElementById('setup-totp-btn');
    const totpQRCode = document.getElementById('totp-qr-code');
    if (setupTOTPBtn && totpQRCode) {
        setupTOTPBtn.addEventListener('click', function() {
            ajaxRequest('/generate-totp-qr/', 'GET', null, function(response) {
                totpQRCode.src = response.qr_code_url;
                totpQRCode.classList.remove('d-none');
                setupTOTPBtn.classList.add('d-none');
            }, function(error) {
                console.error('Error generating TOTP QR code:', error);
            });
        });
    }
});