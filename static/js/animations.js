const AnimationsModule = {
    init() {
        this.scrollAnimations();
        this.parallax();
        this.scrollToTop();
        this.lazyLoadImages();
        this.countUp();
    },

    // Scroll-triggered animations
    scrollAnimations() {
        const elements = document.querySelectorAll('[data-animate]');

        if (elements.length === 0) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const animation = entry.target.dataset.animate;
                    const delay = entry.target.dataset.delay || 0;

                    setTimeout(() => {
                        entry.target.classList.add(`animate-${animation}`);
                    }, delay);

                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });

        elements.forEach(el => observer.observe(el));
    },

    // Parallax effect
    parallax() {
        const parallaxElements = document.querySelectorAll('[data-parallax]');

        if (parallaxElements.length === 0) return;

        window.addEventListener('scroll', AuroraMart.throttle(() => {
            const scrolled = window.pageYOffset;

            parallaxElements.forEach(el => {
                const speed = parseFloat(el.dataset.parallax) || 0.5;
                const yPos = -(scrolled * speed);
                el.style.transform = `translateY(${yPos}px)`;
            });
        }, 10));
    },

    // Scroll to top button
    scrollToTop() {
        // Create button if it doesn't exist
        let scrollButton = document.getElementById('scroll-to-top');

        if (!scrollButton) {
            scrollButton = document.createElement('button');
            scrollButton.id = 'scroll-to-top';
            scrollButton.innerHTML = '↑';
            scrollButton.className = 'btn-primary';
            scrollButton.style.cssText = `
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                width: 3rem;
                height: 3rem;
                border-radius: 50%;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 1000;
                font-size: 1.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
            `;
            document.body.appendChild(scrollButton);
        }

        // Show/hide on scroll
        window.addEventListener('scroll', AuroraMart.throttle(() => {
            if (window.pageYOffset > 300) {
                scrollButton.style.opacity = '1';
                scrollButton.style.visibility = 'visible';
            } else {
                scrollButton.style.opacity = '0';
                scrollButton.style.visibility = 'hidden';
            }
        }, 100));

        // Scroll to top on click
        scrollButton.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    },

    // Lazy load images
    lazyLoadImages() {
        const images = document.querySelectorAll('img[data-src]');

        if (images.length === 0) return;

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;

                    // Show loading placeholder
                    img.style.backgroundColor = '#f3f4f6';

                    // Load image
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');

                    img.onload = () => {
                        img.style.animation = 'fadeIn 0.5s ease-out';
                    };

                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    },

    // Count up animation for numbers
    countUp() {
        const counters = document.querySelectorAll('[data-count]');

        if (counters.length === 0) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const endValue = parseFloat(target.dataset.count);
                    const duration = parseInt(target.dataset.duration) || 2000;
                    const startValue = 0;
                    const increment = endValue / (duration / 16); // 60fps

                    let currentValue = startValue;

                    const counter = setInterval(() => {
                        currentValue += increment;

                        if (currentValue >= endValue) {
                            currentValue = endValue;
                            clearInterval(counter);
                        }

                        // Format number
                        if (target.dataset.format === 'currency') {
                            target.textContent = AuroraMart.formatCurrency(currentValue);
                        } else {
                            target.textContent = Math.floor(currentValue).toLocaleString();
                        }
                    }, 16);

                    observer.unobserve(target);
                }
            });
        }, {
            threshold: 0.5
        });

        counters.forEach(counter => observer.observe(counter));
    }
};

// Export
window.AnimationsModule = AnimationsModule;