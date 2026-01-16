
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
