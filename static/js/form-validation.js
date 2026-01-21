/**
 * Admin Form Validation Library
 * Handles real-time and submission-time validation for dashboard forms.
 */

document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Find inputs with validation requirements
        const inputs = form.querySelectorAll('input[required], input[type="email"], input[data-pattern], select[required], textarea[required]');
        
        // Add real-time validation on input/change
        inputs.forEach(input => {
            input.addEventListener('input', () => validateField(input));
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('change', () => validateField(input));
        });

        // Add submission validation
        form.addEventListener('submit', function(e) {
            let isValid = true;
            inputs.forEach(input => {
                if (!validateField(input)) {
                    isValid = false;
                }
            });

            // Specific check for password matching
            const password = form.querySelector('input[name="password"]');
            const confirmPassword = form.querySelector('input[name="confirm_password"]');
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                showError(confirmPassword, "Passwords do not match");
                isValid = false;
            }

            // Specific check for Product Variants (ensure at least one row has data)
            const variantPrices = form.querySelectorAll('input[name="variant_price[]"]');
            if (variantPrices.length > 0) {
                let hasOneValidVariant = false;
                variantPrices.forEach(priceInput => {
                    if (priceInput.value !== '') hasOneValidVariant = true;
                });
                if (!hasOneValidVariant) {
                    alert("Please add at least one product variant with a price.");
                    isValid = false;
                }
            }

            if (!isValid) {
                e.preventDefault();
                e.stopPropagation();
                
                // Scroll to first error
                const firstError = form.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    });

    function validateField(input) {
        const value = input.value.trim();
        let errorMsg = "";

        // Required check
        if (input.hasAttribute('required') && value === "") {
            errorMsg = "This field is required";
        } 
        // Email check
        else if (input.type === 'email' && value !== "") {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                errorMsg = "Please enter a valid email address";
            }
        }
        // Phone check (10 digits)
        else if ((input.name === 'phone' || input.name === 'business_phone') && value !== "") {
            const phoneRegex = /^\d{10}$/;
            if (!phoneRegex.test(value)) {
                errorMsg = "Please enter a valid 10-digit number";
            }
        }
        // Numeric check
        else if (input.type === 'number' && value !== "") {
            if (parseFloat(value) < 0) {
                errorMsg = "Value cannot be negative";
            }
        }
        // Custom pattern check
        else if (input.dataset.pattern && value !== "") {
            const regex = new RegExp(input.dataset.pattern);
            if (!regex.test(value)) {
                errorMsg = input.dataset.error || "Invalid format";
            }
        }

        if (errorMsg) {
            showError(input, errorMsg);
            return false;
        } else {
            clearError(input);
            return true;
        }
    }

    function showError(input, msg) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentNode.appendChild(feedback);
        }
        feedback.textContent = msg;
    }

    function clearError(input) {
        input.classList.remove('is-invalid');
        // input.classList.add('is-valid'); // Optional: Add a green valid state
        
        const feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.textContent = "";
        }
    }
});
