/**
 * AuroraMart Hero Slideshow
 * Lightweight slider inspired by Codrops RevealSlideshow.
 */
(function () {
    const slider = document.querySelector('[data-hero-slider]');
    if (!slider) return;

    const slides = Array.from(slider.querySelectorAll('[data-hero-slide]'));
    if (slides.length <= 1) {
        slides[0]?.classList.add('is-active');
        return;
    }

    const dots = Array.from(slider.querySelectorAll('[data-hero-dot]'));
    const prevBtn = slider.querySelector('[data-hero-prev]');
    const nextBtn = slider.querySelector('[data-hero-next]');

    let current = 0;
    let timer = null;
    const interval = 3000;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function setActive(index) {
        if (index === current) return;

        slides[current].classList.remove('is-active');
        slides[current].setAttribute('aria-hidden', 'true');

        current = (index + slides.length) % slides.length;

        slides[current].classList.add('is-active');
        slides[current].setAttribute('aria-hidden', 'false');

        dots.forEach((dot, idx) => {
            dot.classList.toggle('is-active', idx === current);
            dot.setAttribute('aria-pressed', idx === current ? 'true' : 'false');
        });

    }

    function next() {
        setActive(current + 1);
    }

    function prev() {
        setActive(current - 1);
    }

    function startAutoplay() {
        if (prefersReducedMotion) return;
        stopAutoplay();
        timer = window.setInterval(next, interval);
    }

    function stopAutoplay() {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
    }

    slides.forEach((slide, idx) => {
        slide.setAttribute('aria-hidden', idx === current ? 'false' : 'true');
    });

    dots.forEach((dot, idx) => {
        dot.addEventListener('click', () => setActive(idx));
        dot.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                setActive(idx);
            }
        });
    });

    prevBtn?.addEventListener('click', prev);
    nextBtn?.addEventListener('click', next);

    slider.addEventListener('mouseenter', stopAutoplay);
    slider.addEventListener('mouseleave', startAutoplay);
    slider.addEventListener('focusin', stopAutoplay);
    slider.addEventListener('focusout', startAutoplay);

    slides[0].classList.add('is-active');
    dots[0]?.classList.add('is-active');
    dots[0]?.setAttribute('aria-pressed', 'true');
    startAutoplay();
})();

