/**
 * FootFront Global Form Validator
 * Provides real-time and submission-time validation feedback.
 */

document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[novalidate]');

    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(form)) {
                event.preventDefault();
                event.stopPropagation();
                
                // Scroll to first error
                const firstError = form.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
            form.classList.add('was-validated');
        }, false);

        // Add real-time listeners to clear errors
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                validateField(input);
            });
            input.addEventListener('change', function() {
                validateField(input);
            });
        });
    });

    function validateField(field) {
        let isValid = field.checkValidity();
        let errorMessage = field.validationMessage;

        // Custom Regex Pattern Validation (data-pattern)
        const pattern = field.getAttribute('data-pattern');
        if (isValid && pattern && field.value) {
            const regex = new RegExp(pattern);
            if (!regex.test(field.value)) {
                isValid = false;
                errorMessage = field.getAttribute('data-error') || 'Invalid format.';
            }
        }

        // Field Matching (e.g. Password Confirmation) - data-match="field_id"
        const matchId = field.getAttribute('data-match');
        if (isValid && matchId) {
            const matchField = document.getElementById(matchId);
            if (matchField && field.value !== matchField.value) {
                isValid = false;
                errorMessage = 'Fields do not match.';
            }
        }

        if (!isValid) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            
            // Handle error message display
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentNode.appendChild(feedback);
            }
            feedback.textContent = errorMessage;
            feedback.style.display = 'block';
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.style.display = 'none';
            }
        }
        return isValid;
    }

    function validateForm(form) {
        let formIsValid = true;
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            if (!validateField(input)) {
                formIsValid = false;
            }
        });
        
        return formIsValid;
    }
});
