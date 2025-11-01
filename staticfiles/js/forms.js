/* ========================================
   FORMS - Form validation and handling
   ======================================== */

const FormsModule = (function () {
    'use strict';

    // Form validation
    function initFormValidation() {
        const forms = document.querySelectorAll('form[novalidate]');

        forms.forEach(form => {
            const inputs = form.querySelectorAll('.form-control');

            inputs.forEach(input => {
                input.addEventListener('blur', function () {
                    validateField(this);
                });

                input.addEventListener('input', function () {
                    this.classList.remove('error');
                });
            });

            form.addEventListener('submit', function (e) {
                let isValid = true;
                inputs.forEach(input => {
                    if (!validateField(input)) {
                        isValid = false;
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                }
            });
        });
    }

    function validateField(field) {
        if (field.hasAttribute('required') && field.value.trim() === '') {
            field.classList.add('error');
            return false;
        }

        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                field.classList.add('error');
                return false;
            }
        }

        field.classList.remove('error');
        return true;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFormValidation);
    } else {
        initFormValidation();
    }

    return {
        init: initFormValidation,
        validate: validateField
    };
})();