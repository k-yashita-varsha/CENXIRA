let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const dots = document.querySelectorAll('.nav-dot');
const container = document.querySelector('.slides-container');
const totalSlides = slides.length;
let isAnimating = false;

function updateSlide() {
    isAnimating = true;
    
    // Update active slide class for CSS animations
    slides.forEach((slide, index) => {
        if (index === currentSlide) {
            slide.classList.add('active');
        } else {
            slide.classList.remove('active');
        }
    });

    // Move the container
    container.style.transform = `translateY(-${currentSlide * 100}%)`;

    // Update dots
    dots.forEach((dot, index) => {
        dot.classList.toggle('active', index === currentSlide);
    });

    // Update footer counter
    document.querySelector('.slide-counter').textContent = `${currentSlide + 1} / ${totalSlides}`;

    setTimeout(() => {
        isAnimating = false;
    }, 800);
}

function nextSlide() {
    if (currentSlide < totalSlides - 1) {
        currentSlide++;
        updateSlide();
    }
}

function prevSlide() {
    if (currentSlide > 0) {
        currentSlide--;
        updateSlide();
    }
}

// User Interaction
window.addEventListener('wheel', (e) => {
    if (isAnimating) return;
    if (e.deltaY > 0) nextSlide();
    else prevSlide();
});

window.addEventListener('keydown', (e) => {
    if (isAnimating) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight' || e.key === ' ') nextSlide();
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') prevSlide();
});

dots.forEach((dot, index) => {
    dot.addEventListener('click', () => {
        if (isAnimating) return;
        currentSlide = index;
        updateSlide();
    });
});

// Initial load
updateSlide();
