
// Initialize Lenis
const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smooth: true,
});

function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
}

requestAnimationFrame(raf);

// Initialize GSAP ScrollTrigger
gsap.registerPlugin(ScrollTrigger);

// Custom Cursor Logic
const cursorDot = document.querySelector('.cursor-dot');
const cursorOutline = document.querySelector('.cursor-outline');

window.addEventListener('mousemove', (e) => {
    const posX = e.clientX;
    const posY = e.clientY;

    // Dot - direct follow
    if (cursorDot) {
        cursorDot.style.left = `${posX}px`;
        cursorDot.style.top = `${posY}px`;
    }

    // Outline - delayed follow with GSAP
    if (cursorOutline) {
        cursorOutline.animate({
            left: `${posX}px`,
            top: `${posY}px`
        }, { duration: 500, fill: "forwards" });
    }
});

// Cursor Hover Interactions
const interactiveElements = document.querySelectorAll('a, button, .hover-target');

interactiveElements.forEach(el => {
    el.addEventListener('mouseenter', () => {
        if(cursorOutline) cursorOutline.classList.add('hovered');
    });
    el.addEventListener('mouseleave', () => {
        if(cursorOutline) cursorOutline.classList.remove('hovered');
    });
});

console.log("FootFront UI Loaded - Gen Z Edition");

/* Global Error Modal Logic */
window.showGlobalError = function(title, message) {
    const modal = document.getElementById('globalErrorModal');
    if(modal) {
        document.getElementById('globalErrorTitle').innerText = title || "SYSTEM ALERT";
        document.getElementById('globalErrorMessage').innerText = message || "An unknown error has occurred.";
        modal.classList.add('active');
    }
};

window.closeGlobalError = function() {
    const modal = document.getElementById('globalErrorModal');
    if(modal) {
        modal.classList.remove('active');
    }
};

window.parseFirebaseError = function(errorInput) {
    let message = "An authentication error occurred.";
    let rawStr = "";

    if (typeof errorInput === 'string') {
        rawStr = errorInput;
    } else if (errorInput && errorInput.message) {
        rawStr = errorInput.message;
    } else {
        rawStr = JSON.stringify(errorInput);
    }

    // Try to parse JSON if the string looks like it
    if (rawStr.trim().startsWith('{')) {
        try {
            const data = JSON.parse(rawStr);
            if (data.error && data.error.message) {
                rawStr = data.error.message;
            } else if (data.message) {
                rawStr = data.message;
            }
        } catch (e) {}
    }

    // Mapping codes to friendly messages
    const mapping = {
        "EMAIL_NOT_FOUND": "This email address is not registered.",
        "INVALID_PASSWORD": "The password you entered is incorrect.",
        "USER_DISABLED": "This account has been disabled.",
        "EMAIL_EXISTS": "An account with this email address already exists.",
        "TOO_MANY_ATTEMPTS_EXCEEDED": "Too many failed attempts. Please try again later.",
        "INVALID_EMAIL": "The email address provided is invalid.",
        "WEAK_PASSWORD": "The password provided is too weak.",
        "USER_NOT_FOUND": "No account found with these credentials.",
        "INVALID_LOGIN_CREDENTIALS": "Invalid login credentials. Please check your email and password.",
        "auth/user-not-found": "No account found with this email.",
        "auth/wrong-password": "Incorrect password. Please try again.",
        "auth/email-already-in-use": "This email is already in use by another account.",
        "auth/invalid-email": "Please enter a valid email address.",
        "auth/weak-password": "Password is too weak. Use a stronger one.",
        "auth/network-request-failed": "Network error. Please check your connection.",
        "auth/too-many-requests": "Too many requests. Please try again later.",
    };

    // Clean the error string (extracting code if it's like "CODE : Description")
    const cleanCode = rawStr.split(' : ')[0].split('] ').pop().trim();
    
    return mapping[cleanCode] || mapping[rawStr] || rawStr || message;
};
