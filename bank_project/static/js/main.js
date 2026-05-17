/* ===================================================
   NovaBank — Main JavaScript
   =================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Money Formatter ----
    function novaFormatMoney(value) {
        return parseFloat(value).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // ---- Theme Toggle ----
    const themeToggle = document.getElementById('themeToggle');

    function navScrollBackground() {
        const navbar = document.querySelector('.nova-nav');
        if (!navbar) return;
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (window.scrollY > 50) {
            navbar.style.background = isLight ? 'rgba(255, 255, 255, 0.98)' : 'rgba(0, 0, 0, 0.94)';
            navbar.style.borderBottomColor = isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.06)';
        } else {
            navbar.style.background = '';
            navbar.style.borderBottomColor = '';
        }
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('nova-theme', next);
            navScrollBackground();
        });
    }

    // ---- Password Toggle (eye icon) ----
    document.querySelectorAll('.password-toggle').forEach(btn => {
        btn.addEventListener('click', function () {
            const wrapper = this.closest('.password-wrapper');
            const input = wrapper.querySelector('input');
            const icon = this.querySelector('i');

            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('bi-eye', 'bi-eye-slash');
                this.style.color = 'var(--gold)';
            } else {
                input.type = 'password';
                icon.classList.replace('bi-eye-slash', 'bi-eye');
                this.style.color = '';
            }
        });
    });

    // ---- Scroll Reveal ----
    const revealElements = document.querySelectorAll('.reveal');
    if (revealElements.length > 0) {
        const revealOnScroll = () => {
            revealElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.top < window.innerHeight - 80) {
                    el.classList.add('visible');
                }
            });
        };
        window.addEventListener('scroll', revealOnScroll);
        revealOnScroll(); // trigger on load
    }

    // ---- Navbar Scroll Effect ----
    window.addEventListener('scroll', navScrollBackground);

    // ---- Stats Counter Animation ----
    const statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length > 0) {
        const animateCounter = (el) => {
            const target = parseFloat(el.getAttribute('data-value'));
            const duration = 2000;
            const start = performance.now();
            const isDecimal = target % 1 !== 0;

            const update = (now) => {
                const elapsed = now - start;
                const progress = Math.min(elapsed / duration, 1);
                // Ease out cubic
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = target * eased;

                if (isDecimal) {
                    el.textContent = novaFormatMoney(current);
                } else {
                    el.textContent = Math.floor(current).toLocaleString('en-US');
                }

                if (progress < 1) {
                    requestAnimationFrame(update);
                } else {
                    if (isDecimal) {
                        el.textContent = novaFormatMoney(target);
                    } else {
                        el.textContent = target.toLocaleString('en-US');
                    }
                }
            };
            requestAnimationFrame(update);
        };

        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        statNumbers.forEach(el => statsObserver.observe(el));
    }

    // ---- Hero Particles (subtle floating dots) ----
    const canvas = document.getElementById('hero-particles');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let particles = [];
        const particleCount = 50;

        const resizeCanvas = () => {
            canvas.width = canvas.parentElement.offsetWidth;
            canvas.height = canvas.parentElement.offsetHeight;
        };
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        class Particle {
            constructor() {
                this.reset();
            }
            reset() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 0.5;
                this.speedX = (Math.random() - 0.5) * 0.3;
                this.speedY = (Math.random() - 0.5) * 0.3;
                this.opacity = Math.random() * 0.3 + 0.05;
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) {
                    this.reset();
                }
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(245, 166, 35, ${this.opacity})`;
                ctx.fill();
            }
        }

        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }

        const animateParticles = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.update();
                p.draw();
            });
            requestAnimationFrame(animateParticles);
        };
        animateParticles();
    }

    // ---- Smooth Scroll for anchor links ----
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ---- Format all displayed MAD amounts with thousand separators ----
    (function formatAllMadAmounts() {
        const pattern = /(-?\d+\.\d{2})\s*MAD/g;
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
        const nodes = [];
        let node;
        while ((node = walker.nextNode())) {
            if (/\d+\.\d{2}\s*MAD/.test(node.textContent)) {
                nodes.push(node);
            }
        }
        nodes.forEach(n => {
            n.textContent = n.textContent.replace(pattern, (_, num) => {
                return novaFormatMoney(parseFloat(num)) + ' MAD';
            });
        });
    })();

    // ---- Live amount input preview (formats as you type) ----
    document.querySelectorAll('input[name="amount"]').forEach(function (input) {
        const preview = document.createElement('div');
        preview.style.cssText = 'font-size:1.5rem;font-weight:700;color:var(--nova-gold,#D4AF37);margin-top:6px;min-height:2rem;letter-spacing:0.02em;transition:opacity 0.2s;';
        input.parentNode.insertBefore(preview, input.nextSibling);

        input.addEventListener('input', function () {
            const val = parseFloat(this.value);
            if (!isNaN(val) && val > 0) {
                preview.textContent = novaFormatMoney(val) + ' MAD';
                preview.style.opacity = '1';
            } else {
                preview.textContent = '';
                preview.style.opacity = '0';
            }
        });
    });

});
