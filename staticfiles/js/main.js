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

    // === Seção Análise e Recomendação - Auto collapse e toggle ===
    const analiseRecomendacao = document.getElementById('analiseRecomendacao');
    const analiseConteudo = document.getElementById('analiseConteudo');
    const btnToggleAnalise = document.getElementById('btnToggleAnalise');

    if (analiseRecomendacao && analiseConteudo && btnToggleAnalise) {
        let isExpanded = true;
        let autoCollapseTimer = null;
        const storageKey = 'analiseRecomendacaoExpanded';

        // Restaurar estado da sessão anterior
        const savedState = localStorage.getItem(storageKey);
        if (savedState === 'false') {
            isExpanded = false;
            collapseAnalise();
        }

        // Auto-recolher após 3 segundos - apenas se estiver expandido
        autoCollapseTimer = setTimeout(function () {
            if (isExpanded) {
                collapseAnalise();
                isExpanded = false;
                localStorage.setItem(storageKey, 'false');
            }
        }, 3000);

        // Click para expandir/recolher
        btnToggleAnalise.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Limpar o timeout de auto-collapse ao clicar
            if (autoCollapseTimer) {
                clearTimeout(autoCollapseTimer);
                autoCollapseTimer = null;
            }
            
            if (isExpanded) {
                collapseAnalise();
                isExpanded = false;
            } else {
                expandAnalise();
                isExpanded = true;
            }
            localStorage.setItem(storageKey, isExpanded);
        });

        function collapseAnalise() {
            // Sempre manter overflow hidden para a animação funcionar
            analiseConteudo.style.overflow = 'hidden';
            analiseConteudo.style.maxHeight = '0';
            analiseConteudo.style.opacity = '0';
            analiseConteudo.style.marginTop = '0';
            analiseConteudo.style.marginBottom = '0';
            analiseConteudo.style.paddingTop = '0';
            analiseConteudo.style.paddingBottom = '0';
            
            btnToggleAnalise.style.opacity = '0.6';
            btnToggleAnalise.innerHTML = '<i class="bi bi-chevron-down"></i>';
            btnToggleAnalise.title = 'Expandir análise e recomendações';
        }

        function expandAnalise() {
            // Calcular altura real do conteúdo
            analiseConteudo.style.overflow = 'hidden';
            analiseConteudo.style.maxHeight = 'none';
            const scrollHeight = analiseConteudo.scrollHeight;
            analiseConteudo.style.maxHeight = scrollHeight + 50 + 'px';
            
            analiseConteudo.style.opacity = '1';
            analiseConteudo.style.marginTop = '';
            analiseConteudo.style.marginBottom = '';
            analiseConteudo.style.paddingTop = '';
            analiseConteudo.style.paddingBottom = '';
            
            btnToggleAnalise.style.opacity = '1';
            btnToggleAnalise.innerHTML = '<i class="bi bi-chevron-up"></i>';
            btnToggleAnalise.title = 'Recolher análise e recomendações';
        }
    }

});
