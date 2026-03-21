/**
 * Vendas Links Tops ML - JavaScript Principal
 */

document.addEventListener('DOMContentLoaded', function () {

    // === Scroll to Top Button ===
    const scrollBtn = document.createElement('button');
    scrollBtn.className = 'scroll-top-btn';
    scrollBtn.innerHTML = '<i class="bi bi-chevron-up"></i>';
    scrollBtn.setAttribute('aria-label', 'Voltar ao topo');
    scrollBtn.setAttribute('title', 'Voltar ao topo');
    document.body.appendChild(scrollBtn);

    window.addEventListener('scroll', function () {
        if (window.scrollY > 300) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });

    scrollBtn.addEventListener('click', function () {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // === Lazy Loading de Imagens (fallback para navegadores antigos) ===
    if ('IntersectionObserver' in window) {
        const imgObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    imgObserver.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px'
        });

        document.querySelectorAll('img[data-src]').forEach(function (img) {
            imgObserver.observe(img);
        });
    }

    // === Animação de entrada dos cards ao scroll ===
    if ('IntersectionObserver' in window) {
        const cardObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    cardObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '20px'
        });

        document.querySelectorAll('.product-card').forEach(function (card, index) {
            if (index > 3) { // Só anima cards além dos 4 primeiros
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                cardObserver.observe(card);
            }
        });
    }

    // === Tracking de cliques em links afiliados (analytics) ===
    document.querySelectorAll('.product-card-link').forEach(function (link) {
        link.addEventListener('click', function () {
            const titulo = this.querySelector('.product-title');
            if (titulo && typeof gtag === 'function') {
                gtag('event', 'click', {
                    'event_category': 'affiliate_link',
                    'event_label': titulo.textContent.trim()
                });
            }
        });
    });

});
