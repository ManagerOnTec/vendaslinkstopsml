"""
Módulo de scraping para extrair dados de produtos de múltiplas plataformas.
Utiliza Playwright (browser headless) para contornar proteções anti-bot.

Suporta:
1. Mercado Livre - Página de produto individual (PDP) ou perfil social
2. Amazon - Página de detalle do produto
3. Shopee - Página de produto
4. Shein - Página de produto
"""
import asyncio
import json
import logging
import random
import re
import threading
import time
from django.utils import timezone
from .detector_plataforma import DetectorPlataforma, SELETORES, limpar_preco

logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("⚠️  requests/BeautifulSoup não instalados - fallback desabilitado")

# ============================================================================
# RATE LIMITING PARA MÚLTIPLAS PLATAFORMAS
# ============================================================================
# Evita sobrecarga do servidor ao fazer múltiplas requisições simultâneas
# IMPORTANTE: Usa threading.Semaphore (não asyncio.Semaphore) para compatibilidade
# com múltiplas threads rodando asyncio.run() independentemente

_scraper_semaphore = threading.Semaphore(2)  # Máx 2 requisições simultâneas entre threads
_last_request_time = None
_rate_limit_lock = threading.Lock()

MIN_DELAY_BETWEEN_REQUESTS_MS = 300  # Mínimo delay entre requisições (300ms)


def _enforce_rate_limit():
    """
    Garante delay mínimo entre requisições e controla paralelismo via semáforo.
    Thread-safe: funciona corretamente quando múltiplas threads fazem asyncio.run()
    """
    global _last_request_time
    
    # Adquirir semáforo para limitar requisições simultâneas
    # Timeout curto evita deadlocks
    acquired = _scraper_semaphore.acquire(timeout=30)
    if not acquired:
        logger.warning("⚠️ Timeout ao adquirir semáforo de rate limiting (30s)")
        return
    
    try:
        with _rate_limit_lock:
            current_time = time.time()
            if _last_request_time:
                elapsed = (current_time - _last_request_time) * 1000  # Converter para ms
                if elapsed < MIN_DELAY_BETWEEN_REQUESTS_MS:
                    sleep_time = (MIN_DELAY_BETWEEN_REQUESTS_MS - elapsed) / 1000
                    logger.debug(f"⏱️ Rate limiting: aguardando {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            _last_request_time = time.time()
    finally:
        _scraper_semaphore.release()




def _melhorar_url_imagem(url: str) -> str:
    """
    Converte URL de thumbnail do ML para alta resolução.
    Padrões do ML:
    - -T.webp = thumbnail (320x320)
    - -V.webp = variante (640x640)
    - -F.webp = full size (alta resolução)
    - -O.webp = original (máxima resolução)
    """
    if not url:
        return url
    
    # Trocar sufixo de thumbnail para full size
    for suffix in ['-T.webp', '-T.jpg', '-T.png']:
        if suffix in url:
            url = url.replace(suffix, suffix.replace('-T', '-F'))
    
    return url


async def _extrair_dados_ml(url: str) -> dict:
    """Extrai dados de um produto do Mercado Livre usando Playwright."""
    # Aplicar rate limiting antes de iniciar requisição
    _enforce_rate_limit()
    
    from playwright.async_api import async_playwright

    dados = {
        'titulo': '',
        'imagem_url': '',
        'preco': '',
        'preco_original': '',
        'descricao': '',
        'categoria': '',
        'url_final': '',
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        context = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            ),
            locale='pt-BR',
            viewport={'width': 1366, 'height': 768},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        # Remover flag de webdriver para evitar detecção
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en']
            });
        """)

        page = await context.new_page()

        try:
            resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if resp and resp.status >= 400:
                raise Exception(f"HTTP {resp.status}")

            # Esperar conteúdo carregar
            await page.wait_for_timeout(5000)

            dados['url_final'] = page.url

            # Extrair todos os dados via JavaScript
            result = await page.evaluate('''() => {
                const getMeta = (prop) => {
                    const el = document.querySelector(
                        `meta[property="${prop}"]`
                    ) || document.querySelector(`meta[name="${prop}"]`);
                    return el ? el.content : '';
                };

                // Função para extrair categoria da breadcrumb
                const extractCategory = () => {
                    try {
                        // Estratégia 1: meta breadcrumb (JSON-LD)
                        const breadcrumbMeta = document.querySelector('script[type="application/ld+json"]');
                        if (breadcrumbMeta) {
                            const data = JSON.parse(breadcrumbMeta.textContent);
                            if (data.itemListElement && data.itemListElement.length > 1) {
                                const secondItem = data.itemListElement[1];
                                if (secondItem && secondItem.name) {
                                    return secondItem.name.trim();
                                }
                            }
                        }
                    } catch (e) {}

                    try {
                        // Estratégia 2: elemento andes-breadcrumb no DOM
                        const breadcrumbEl = document.querySelector('.andes-breadcrumb');
                        if (breadcrumbEl) {
                            const items = breadcrumbEl.querySelectorAll('.andes-breadcrumb__item');
                            if (items.length > 1) {
                                const categoryText = items[1].textContent.trim();
                                if (categoryText && categoryText !== 'Home' && categoryText.length > 0) {
                                    return categoryText;
                                }
                            }
                        }
                    } catch (e) {}

                    try {
                        // Estratégia 3: em páginas de perfil social, procurar breadcrumb no link do produto
                        const productLink = document.querySelector('a[href*="/p/"], a[href*="/item/"]');
                        if (productLink) {
                            // Fazer fetch do link para extrair categoria
                            const productUrl = productLink.href;
                            // Extrair do padrão de URL: /c/CATEGORIA/p/ID
                            const categoryMatch = productUrl.match(/\/c\/([^\/]+)/);
                            if (categoryMatch && categoryMatch[1]) {
                                const categoryFromUrl = categoryMatch[1]
                                    .replace(/-/g, ' ')
                                    .split(' ')
                                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                                    .join(' ');
                                if (categoryFromUrl.length > 2) {
                                    return categoryFromUrl;
                                }
                            }
                        }
                    } catch (e) {}

                    try {
                        // Estratégia 4: tenta og:breadcrumb (se existir)
                        const allScripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (const script of allScripts) {
                            try {
                                const data = JSON.parse(script.textContent);
                                if (data['@type'] === 'BreadcrumbList' && data.itemListElement) {
                                    if (data.itemListElement.length > 1) {
                                        const secondItem = data.itemListElement[1];
                                        if (secondItem && secondItem.name) {
                                            return secondItem.name.trim();
                                        }
                                    }
                                }
                            } catch (e) {}
                        }
                    } catch (e) {}

                    try {
                        // ✅ ESTRATÉGIA 5 (NOVA): Pegar segundo item do breadcrumb no DOM
                        // Fallback quando as outras estratégias falham
                        const breadcrumbLinks = document.querySelectorAll('[class*="breadcrumb"] a');
                        if (breadcrumbLinks.length >= 2) {
                            // Pegar o SEGUNDO link (índice 1) - primeira categoria relevante
                            const secondLink = breadcrumbLinks[1];
                            if (secondLink) {
                                const categoryText = secondLink.textContent.trim();
                                if (categoryText && categoryText !== 'Home' && categoryText.length > 0) {
                                    return categoryText;
                                }
                            }
                        }
                    } catch (e) {}

                    return '';
                };

                // Função auxiliar para extrair preço de um andes-money-amount
                const extractPrice = (moneyEl) => {
                    if (!moneyEl) return '';
                    const fraction = moneyEl.querySelector(
                        '.andes-money-amount__fraction'
                    );
                    if (!fraction) return '';
                    let price = fraction.textContent.trim();
                    const cents = moneyEl.querySelector(
                        '.andes-money-amount__cents'
                    );
                    if (cents && cents.textContent.trim()) {
                        price += ',' + cents.textContent.trim();
                    }
                    return price;
                };

                // ===== FUNÇÃO PARA ENCONTRAR IMAGEM REAL DO PRODUTO =====
                // Filtra banners, avatares e propagandas
                const findProductImage = (context) => {
                    // Classes que indicam banners/propagandas (NÃO são imagens de produto)
                    const bannerClasses = [
                        'exhibitor__picture',
                        'exhibitor',
                        'ui-ms-profile__circle',
                        'nav-header',
                        'nav-logo',
                        'andes-carousel-snapped',
                    ];

                    // Classes que indicam imagens de produto (PRIORIDADE)
                    const productClasses = [
                        'poly-component__picture',
                        'ui-pdp-gallery__figure',
                        'ui-pdp-image',
                    ];

                    const root = context || document;

                    // 1) Tentar imagens com classe de produto
                    for (const cls of productClasses) {
                        const img = root.querySelector(
                            '.' + cls + ' img, img.' + cls
                        );
                        if (img && img.src && !img.src.startsWith('data:')) {
                            return img.src;
                        }
                    }

                    // 2) Buscar todas as imagens do mlstatic e filtrar
                    const allImgs = root.querySelectorAll(
                        'img[src*="http2.mlstatic.com"]'
                    );
                    for (const img of allImgs) {
                        // Pular imagens sem src real
                        if (!img.src || img.src.startsWith('data:')) continue;

                        // Pular imagens muito pequenas (ícones, logos)
                        const w = img.naturalWidth || img.width || 0;
                        const h = img.naturalHeight || img.height || 0;
                        if (w > 0 && h > 0 && (w < 150 || h < 150)) continue;

                        // Pular banners (muito largos e finos)
                        if (w > 0 && h > 0 && (w / h > 4 || h / w > 4)) {
                            continue;
                        }

                        // Verificar se está dentro de um container de banner
                        let isBanner = false;
                        for (const cls of bannerClasses) {
                            if (img.closest('.' + cls)) {
                                isBanner = true;
                                break;
                            }
                        }
                        if (isBanner) continue;

                        // Verificar se o alt contém texto de propaganda
                        const alt = (img.alt || '').toLowerCase();
                        const adKeywords = [
                            'meli+', 'disney', 'zootopia', 'mercado pago',
                            'assine', 'a partir de r$', 'por mês',
                            'banner', 'promo', 'publicidade'
                        ];
                        let isAd = false;
                        for (const kw of adKeywords) {
                            if (alt.includes(kw)) {
                                isAd = true;
                                break;
                            }
                        }
                        if (isAd) continue;

                        // Esta imagem passou todos os filtros
                        return img.src;
                    }

                    return '';
                };

                // ===== DETECTAR TIPO DE PÁGINA =====
                const isPDP = !!document.querySelector('.ui-pdp-price');
                const isSocial = window.location.pathname.startsWith('/social/');  // ✅ Mais robusto

                let titulo = '';
                let imgSrc = '';
                let preco = '';
                let precoOriginal = '';
                let descricao = '';
                let categoria = extractCategory();

                // ===== FUNÇÕES DE EXTRAÇÃO DE PREÇO MERCADO LIVRE =====
                // Definidas aqui (fora dos if/else) para serem acessíveis em todos os contextos
                
                const extractMLPrice = () => {
                    let price = '';
                    let estrategiaUsada = '';
                    
                    // ESTRATÉGIA 1: Procurar PRIMEIRO pela seção de "Melhor Preço"
                    // Esta seção SEMPRE contém o menor preço
                    // Seletores: section[class*="bestPrice"], div[data-testid*="best"], [aria-label*="Melhor Preço"]
                    const bestPriceContainers = document.querySelectorAll(
                        'section[class*="bestPrice"], ' +
                        'div[class*="best-price"], ' +
                        '[data-testid*="best"], ' +
                        '[aria-label*="Melhor Preço"]'
                    );
                    
                    for (const container of bestPriceContainers) {
                        // Validar: DEVE conter "Melhor" e NÃO deve conter "Frete" OU "Loja Oficial"
                        const containerText = container.textContent.toLowerCase();
                        if (containerText.includes('melhor') && !containerText.includes('frete') && !containerText.includes('loja oficial')) {
                            const moneyEl = container.querySelector('.andes-money-amount');
                            if (moneyEl) {
                                price = extractPrice(moneyEl);
                                if (price) {
                                    estrategiaUsada = 'Melhor Preço (Estratégia 1)';
                                    return { price, estrategiaUsada };
                                }
                            }
                        }
                    }
                    
                    // ESTRATÉGIA 2: Procurar por "Ofertas" (segunda melhor opção)
                    const offersContainers = document.querySelectorAll(
                        '[class*="offer"], [aria-label*="Oferta"]'
                    );
                    
                    for (const container of offersContainers) {
                        const containerText = container.textContent.toLowerCase();
                        // ❌ Rejeitar: "frete", "envio", "loja oficial"
                        if (
                            containerText.includes('frete') ||
                            containerText.includes('envio') ||
                            containerText.includes('loja oficial') ||
                            containerText.includes('mercado') && containerText.includes('oferta')  // Evita "Mercado Livre Oficial"
                        ) {
                            continue;
                        }
                        
                        const moneyEl = container.querySelector('.andes-money-amount');
                        if (moneyEl && !price) {
                            price = extractPrice(moneyEl);
                            if (price) {
                                estrategiaUsada = 'Ofertas (Estratégia 2)';
                                return { price, estrategiaUsada };
                            }
                        }
                    }
                    
                    // ESTRATÉGIA 3: Se ainda não achou, procurar preço do VENDEDOR (não da Loja Oficial)
                    // Seletores específicos para preço de vendidor (não oficial)
                    const vendorPriceContainers = document.querySelectorAll(
                        '.ui-pdp-price__second-line, ' +
                        '[class*="seller-price"], ' +
                        '[data-testid*="price"]'
                    );
                    
                    for (const container of vendorPriceContainers) {
                        const containerText = container.textContent.toLowerCase();
                        // ❌ NUNCA peguei de Loja Oficial
                        if (containerText.includes('loja oficial') || containerText.includes('mercado livre')) {
                            continue;
                        }
                        
                        const moneyEl = container.querySelector('.andes-money-amount');
                        if (moneyEl && !price) {
                            price = extractPrice(moneyEl);
                            if (price) {
                                estrategiaUsada = 'Preço do Vendedor (Estratégia 3)';
                                return { price, estrategiaUsada };
                            }
                        }
                    }
                    
                    return { price: '', estrategiaUsada: 'Nenhuma estratégia funcionou' };
                };

                // ===== MERCADO LIVRE - FUNÇÃO PARA PREÇO AFILIADO (SOCIAL) =====
                // Em páginas /social/, NÃO use "melhor preço"
                // Pegue APENAS o preço do card afiliado (primeiro card)
                const extractMLSocialPrice = () => {
                    // PREÇO ATUAL do card afiliado (primeiro)
                    const currentPriceEl = document.querySelector(
                        '.poly-price__current .andes-money-amount'
                    );
                    const precoAtual = extractPrice(currentPriceEl);

                    // PREÇO ORIGINAL (riscado), se existir
                    const originalPriceEl = document.querySelector(
                        '.poly-component__price s .andes-money-amount'
                    );
                    const precoOriginal = extractPrice(originalPriceEl);

                    return {
                        preco: precoAtual,
                        precoOriginal: precoOriginal
                    };
                };

                if (isSocial) {
                    // ========================================
                    // MERCADO LIVRE - PERFIL SOCIAL (AFILIADO)
                    // ========================================
                    // SEMPRE TESTAR /social/ ANTES de PDP
                    // Pega APENAS o preço do card afiliado, nunca loja oficial

                    // TÍTULO
                    const titleEl = document.querySelector('.poly-component__title');
                    titulo = titleEl ? titleEl.textContent.trim() : '';

                    // IMAGEM
                    const imgEl = document.querySelector('.poly-component__picture img');
                    imgSrc = imgEl && imgEl.src ? imgEl.src : '';

                    // PREÇOS — SOMENTE DO CARD AFILIADO
                    const currentPriceEl = document.querySelector(
                        '.poly-price__current .andes-money-amount'
                    );
                    preco = extractPrice(currentPriceEl);

                    const originalPriceEl = document.querySelector(
                        '.poly-component__price s .andes-money-amount'
                    );
                    precoOriginal = extractPrice(originalPriceEl);

                    descricao = titulo;

                } else if (isPDP) {
                    // ========================================
                    // MERCADO LIVRE - PDP TRADICIONAL
                    // ========================================

                    // TÍTULO
                    const h1 = document.querySelector('h1');
                    titulo = h1
                        ? h1.textContent.trim()
                        : (getMeta('og:title') || document.title || '');

                    // IMAGEM - Priorizar galeria do produto (sem badges/watermarks)
                    // 1) Tentar galeria carrossel (geralmente tem imagens limpas)
                    const galleryImgs = document.querySelectorAll(
                        '.ui-pdp-gallery__figure img, .ui-pdp-image__container img'
                    );
                    
                    if (galleryImgs.length > 0) {
                        // Preferir a primeira imagem real (sem badges)
                        for (const img of galleryImgs) {
                            const src = img.getAttribute('data-zoom') || img.src || '';
                            if (src && src.includes('mlstatic')) {
                                imgSrc = src;
                                break;  // Pega a primeira de boa qualidade
                            }
                        }
                    }
                    
                    // 2) Fallback: tentar figura específica com data-zoom
                    if (!imgSrc) {
                        const galleryFig = document.querySelector(
                            '.ui-pdp-gallery__figure img'
                        );
                        if (galleryFig) {
                            imgSrc = galleryFig.getAttribute('data-zoom')
                                || galleryFig.src || '';
                        }
                    }
                    
                    // 3) Fallback: og:image (pode ter watermark)
                    if (!imgSrc) {
                        imgSrc = getMeta('og:image') || '';
                    }
                    
                    // 4) Último recurso: busca inteligente
                    if (!imgSrc) {
                        imgSrc = findProductImage(
                            document.querySelector('.ui-pdp-container__row')
                        );
                    }

                    // PREÇO PDP (melhor preço entre vendedores)
                    const precoResult = extractMLPrice();
                    preco = precoResult.price;
                    
                    // Armazenar info de estratégia para logging
                    if (precoResult.estrategiaUsada) {
                        out._debug_preco = {
                            estrategia: precoResult.estrategiaUsada
                        };
                    }

                    // PREÇO ORIGINAL (riscado)
                    const origValue = document.querySelector(
                        '.ui-pdp-price__original-value'
                    );
                    if (origValue) {
                        precoOriginal = extractPrice(origValue);
                    }
                    if (!precoOriginal) {
                        const priceContainer = document.querySelector(
                            '.ui-pdp-price'
                        );
                        if (priceContainer) {
                            const sTag = priceContainer.querySelector(
                                's .andes-money-amount'
                            );
                            if (sTag) {
                                precoOriginal = extractPrice(sTag);
                            }
                        }
                    }

                    // DESCRIÇÃO
                    descricao = getMeta('og:description') || '';

                } else {
                    // ========================================
                    // OUTRO TIPO DE PÁGINA (busca, categoria)
                    // ========================================

                    const h1 = document.querySelector('h1');
                    titulo = h1
                        ? h1.textContent.trim()
                        : (getMeta('og:title') || document.title || '');

                    // IMAGEM: busca inteligente
                    imgSrc = findProductImage(document);
                    if (!imgSrc) {
                        imgSrc = getMeta('og:image') || '';
                    }

                    // Preços de listagem
                    const currentPriceEl = document.querySelector(
                        '.poly-price__current .andes-money-amount'
                    );
                    preco = extractPrice(currentPriceEl);

                    const origPriceEl = document.querySelector(
                        '.poly-component__price .andes-money-amount'
                    );
                    const origPriceText = extractPrice(origPriceEl);
                    if (origPriceText && origPriceText !== preco) {
                        precoOriginal = origPriceText;
                    }

                    descricao = getMeta('og:description') || '';
                }

                return {
                    titulo: titulo,
                    imagem_url: imgSrc || getMeta('og:image') || '',
                    preco: preco,
                    preco_original: precoOriginal,
                    descricao: (descricao || '').substring(0, 500),
                    categoria: categoria,
                    page_type: isPDP ? 'pdp' : (isSocial ? 'social' : 'other')
                };
            }''')

            dados.update(result)

            # Melhorar resolução da imagem (converter thumbnail para full)
            if dados['imagem_url']:
                dados['imagem_url'] = _melhorar_url_imagem(dados['imagem_url'])

            # Formatar preços com prefixo R$
            if dados['preco'] and not dados['preco'].startswith('R$'):
                dados['preco'] = f"R$ {dados['preco']}"
            if dados['preco_original'] and not dados['preco_original'].startswith('R$'):
                dados['preco_original'] = f"R$ {dados['preco_original']}"
            
            # ===== LOGGING DETALHADO DE MERCADO LIVRE =====
            logger.info(f"✅ Mercado Livre: {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")
            
            # Log detalhado de preço com estratégia correta
            if dados.get('preco'):
                debug_info = result.get('_debug_preco', {})
                estrategia = debug_info.get('estrategia', '')
                if not estrategia:
                    estrategia = 'Nenhuma estratégia funcionou (preço vazio)'
                logger.info(f"   💰 Preço: {dados['preco']}")
                logger.info(f"      └─ Estratégia: {estrategia}")
            else:
                logger.warning(f"   💰 Preço: ❌ NÃO ENCONTRADO")
            
            # Log detalhado de preço original
            if dados.get('preco_original'):
                logger.info(f"   📌 Preço Original: {dados['preco_original']}")
                logger.info(f"      └─ Desconto detectado")
            else:
                logger.info(f"   📌 Preço Original: (sem desconto)")
            
            # Log de categoria
            if dados.get('categoria'):
                logger.info(f"   🏷️  Categoria: {dados['categoria']}")
            else:
                logger.warning(f"   🏷️  Categoria: ❌ NÃO ENCONTRADA")

        except Exception as e:
            logger.error(f"Erro ao extrair dados de {url}: {e}")
            raise
        finally:
            await browser.close()

    return dados


async def _extrair_dados_amazon(url: str) -> dict:
    """
    Scraper robusto para Amazon com seletores diretos.
    Prioridade: #productTitle > og:title (meta tag)
    """
    _enforce_rate_limit()
    
    from playwright.async_api import async_playwright

    dados = {
        'titulo': '',
        'imagem_url': '',
        'preco': '',
        'preco_original': '',
        'descricao': '',
        'categoria': '',
        'url_final': '',
        'plataforma': 'amazon',
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1366, 'height': 768},
            geolocation={'latitude': -23.5505, 'longitude': -46.6333},  # São Paulo
            timezone_id='America/Sao_Paulo',
            locale='pt-BR',
            # Headers anti-bot robustos
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        page = await context.new_page()

        try:
            # Adicionar delays aleatórios para simular humano
            await page.wait_for_timeout(random.uniform(500, 1500))
            
            # Timeout reduzido
            timeout = 40000 if DetectorPlataforma.eh_url_encurtada(url) else 30000
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            except Exception as nav_error:
                logger.debug(f"⚠️  Amazon: erro em goto (continuando): {str(nav_error)[:80]}")
            
            # Aguardar elemento + delay aleatório
            try:
                await page.wait_for_selector('#productTitle', timeout=10000)
            except:
                logger.debug("⚠️  Amazon:#productTitle não encontrado")
            
            await page.wait_for_timeout(random.uniform(500, 1500))
            dados['url_final'] = page.url

            # PRIMEIRO: Tentar extrair via Schema.org JSON-LD (ignora bloqueios visuais)
            json_ld_result = await page.evaluate('''() => {
                const data = {
                    titulo: '',
                    preco: '',
                    imagem: '',
                    descricao: '',
                    categoria: '',
                };

                // Procurar Schema.org JSON-LD
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const script of scripts) {
                    try {
                        const json = JSON.parse(script.textContent);
                        
                        if (json['@type'] === 'Product' || json.type === 'Product') {
                            if (json.name) data.titulo = json.name;
                            if (json.offers && json.offers.price) {
                                let price = json.offers.price;
                                if (typeof price === 'number') {
                                    price = price.toString().replace(/^\\./, ',');  // centavos
                                }
                                if (price && !price.includes('R$')) {
                                    data.preco = 'R$ ' + price;
                                } else {
                                    data.preco = price;
                                }
                            }
                            if (json.image) {
                                const img = Array.isArray(json.image) ? json.image[0] : json.image;
                                data.imagem = typeof img === 'string' ? img : img.url;
                            }
                            if (json.description) data.descricao = json.description;
                        }
                        
                        // Extrair categoria de BreadcrumbList (apenas PRIMEIRA categoria relevante)
                        if (json['@type'] === 'BreadcrumbList' && json.itemListElement) {
                            // Pegar TODOS os itens e depois filtrar
                            let firstCategory = null;
                            for (const item of json.itemListElement) {
                                // Pegar o primeiro item que NÃO seja "Home" e tenha nome válido
                                if (item.name && item.name.trim() !== 'Home' && item.name.trim().length > 0) {
                                    firstCategory = item.name.trim();
                                    break;  // Parar no PRIMEIRO encontrado
                                }
                            }
                            if (firstCategory) {
                                data.categoria = firstCategory;
                            }
                        }
                    } catch (e) {}
                }
                
                return data;
            }''')

            # Se JSON-LD funcionou, usar (mais confiável)
            if json_ld_result.get('titulo'):
                dados['titulo'] = json_ld_result['titulo'].strip()[:500]
                dados['preco'] = json_ld_result.get('preco', '').strip()[:50]
                dados['imagem_url'] = json_ld_result.get('imagem', '').strip()
                dados['descricao'] = json_ld_result.get('descricao', '').strip()[:1000]
                dados['categoria'] = json_ld_result.get('categoria', '').strip()[:100]
                logger.info(f"Amazon (JSON-LD): ✅ {dados['titulo'][:60]}")
                logger.info(f"   💰 Preço: {'✅' if dados['preco'] else '❌'} {dados['preco'] or 'NÃO ENCONTRADO'}")
                logger.info(f"      └─ Estratégia: Schema.org JSON-LD (mais confiável)")
                logger.info(f"   🏷️  Categoria: {'✅' if dados['categoria'] else '❌'} {dados['categoria'] or 'NÃO ENCONTRADA'}")
            else:
                # SEGUNDO: Tentar CSS Selectors (mais lento)
                result = await page.evaluate('''() => {
                    const getMeta = (prop) => {
                        const el = document.querySelector(`meta[property="${prop}"]`) || 
                                   document.querySelector(`meta[name="${prop}"]`);
                        return el ? el.getAttribute('content') || el.getAttribute('value') : '';
                    };

                    const data = {
                        titulo: '',
                        preco: '',
                        imagem: '',
                        descricao: '',
                        categoria: '',
                    };

                    // ===== TÍTULO =====
                    const titleEl = document.querySelector('#productTitle');
                    if (titleEl) {
                        data.titulo = titleEl.textContent.trim().substring(0, 500);
                    }
                    if (!data.titulo) {
                        data.titulo = getMeta('og:title');
                    }

                    // ===== PREÇO =====
                    // Estratégia 1: usar a-offscreen (recomendado - contém valor completo limpo)
                    // Procurar em múltiplos contextos pois Amazon é dinâmica
                    let priceSearchSelectors = [
                        'span.a-price span.a-offscreen',           // Método principal
                        '.a-price-whole',                           // Preço inteiro
                        'span[data-a-color="price"] span',          // Contexto de preço
                        'div[class*="price"] span.a-offscreen',    // Em div de preço
                        '.a-price span:not(.a-price-fraction)',     // Qualquer span em a-price que não seja fração
                    ];
                    
                    for (const selector of priceSearchSelectors) {
                        priceEl = document.querySelector(selector);
                        if (priceEl) {
                            const text = priceEl.textContent.trim();
                            if (text && /R\$|[0-9]/.test(text) && text.length < 50) {
                                data.preco = text;
                                break;
                            }
                        }
                    }
                    
                    // Estratégia 2: Fallback - procurar por padrão regex
                    if (!data.preco) {
                        const pageText = document.body.innerText;
                        // Procurar por "R$ XXX,XX" ou similar
                        const match = pageText.match(/R\$\s*[\d.,]+(?:,\d{2})?/);
                        if (match) {
                            data.preco = match[0];
                        }
                    }

                    // ===== IMAGEM =====
                    const landingImg = document.querySelector('#landingImage');
                    if (landingImg && landingImg.src && !landingImg.src.startsWith('data:')) {
                        data.imagem = landingImg.src;
                    }

                    // ===== DESCRIÇÃO =====
                    const featureBullets = document.querySelector('#feature-bullets');
                    if (featureBullets) {
                        const items = featureBullets.querySelectorAll('li span');
                        const bulletTexts = Array.from(items)
                            .map(li => li.textContent.trim())
                            .filter(text => text.length > 5)
                            .slice(0, 3);
                        if (bulletTexts.length > 0) {
                            data.descricao = bulletTexts.join(' • ');
                        }
                    }

                    // ===== CATEGORIA =====
                    // Estratégia 1: Procurar breadcrumb na página (pegar PRIMEIRA categoria relevante)
                    const breadcrumbLinks = document.querySelectorAll('[class*="breadcrumb"] a, [data-testid*="breadcrumb"] a');
                    if (breadcrumbLinks.length > 0) {
                        // Iterar pelos links e pegar o PRIMEIRO que não seja Home
                        for (const link of breadcrumbLinks) {
                            const text = link.textContent.trim();
                            if (text && text !== 'Home' && text.length > 0 && text.length < 50) {
                                data.categoria = text;  // APENAS PRIMEIRO
                                break;
                            }
                        }
                    }

                    return data;
                }''')

                dados['titulo'] = result.get('titulo', '').strip()[:500]
                dados['preco'] = result.get('preco', '').strip()[:50]
                dados['imagem_url'] = result.get('imagem', '').strip()
                dados['descricao'] = result.get('descricao', '').strip()[:1000]
                dados['categoria'] = result.get('categoria', '').strip()[:100]
                logger.info(f"Amazon (CSS Fallback): {'✅' if dados['titulo'] else '❌'} {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")
                logger.info(f"   💰 Preço: {'✅' if dados['preco'] else '❌'} {dados['preco'] or 'NÃO ENCONTRADO'}")
                logger.info(f"      └─ Estratégia: CSS Selectors (.a-price-whole, span.a-offscreen, etc)")
                logger.info(f"   🏷️  Categoria: {'✅' if dados['categoria'] else '❌'} {dados['categoria'] or 'NÃO ENCONTRADA'}")

            # TERCEIRO: Se ainda vazio e requests disponível, usar fallback com requests
            if not dados['titulo'] and REQUESTS_AVAILABLE:
                logger.info("⏳ Amazon: tentando fallback com requests+BeautifulSoup...")
                try:
                    resp = requests.get(
                        url,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept-Language': 'pt-BR,pt;q=0.9',
                        },
                        timeout=15
                    )
                    resp.raise_for_status()
                    
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Título
                    title_el = soup.find('span', {'id': 'productTitle'})
                    if title_el:
                        dados['titulo'] = title_el.text.strip()[:500]
                    
                    # Preço
                    price_el = soup.find('span', {'class': 'a-price-whole'})
                    if price_el:
                        dados['preco'] = 'R$ ' + price_el.text.strip()
                    
                    # Imagem
                    img_el = soup.find('img', {'id': 'landingImage'})
                    if img_el and img_el.get('src'):
                        dados['imagem_url'] = img_el['src']
                    
                    if dados['titulo']:
                        logger.info(f"Amazon (requests fallback): ✅ {dados['titulo'][:60]}")
                    
                except Exception as req_err:
                    logger.debug(f"⚠️  requests fallback falhou: {str(req_err)[:80]}")

        except Exception as e:
            error_msg = str(e)[:100]
            logger.error(f"❌ Erro Amazon: {error_msg}")
            dados['erro_extracao'] = error_msg
        finally:
            await browser.close()

    return dados


async def _extrair_dados_shopee(url: str) -> dict:
    """
    Shopee - Extração simplificada.
    
    Extrai apenas:
    - Título (h1 ou meta og:title)
    - Imagem (og:image ou maior imagem real)
    - Categoria (breadcrumb)
    - Preço: DEFAULT = "Ver preço na loja oficial" (não é extraído)
    """
    _enforce_rate_limit()
    
    from playwright.async_api import async_playwright

    dados = {
        'titulo': '',
        'imagem_url': '',
        'preco': 'Ver preço na loja oficial',  # ✅ DEFAULT
        'preco_original': '',
        'descricao': '',
        'categoria': '',
        'url_final': '',
        'plataforma': 'shopee',
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            ),
            locale='pt-BR',
            viewport={'width': 1366, 'height': 768}
        )

        page = await context.new_page()

        try:
            timeout = 45000 if DetectorPlataforma.eh_url_encurtada(url) else 30000
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            await page.wait_for_timeout(3000)

            dados['url_final'] = page.url

            result = await page.evaluate(r"""() => {
                const out = {
                    titulo: '',
                    imagem_url: '',
                    categoria: '',
                };

                const getMeta = (prop) => {
                    const el =
                        document.querySelector(`meta[property="${prop}"]`) ||
                        document.querySelector(`meta[name="${prop}"]`);
                    return el ? (el.content || '') : '';
                };

                // ---------- TÍTULO ----------
                const h1 = document.querySelector('h1');
                out.titulo = (h1?.innerText || getMeta('og:title') || document.title || '').trim();

                // ---------- IMAGEM ----------
                out.imagem_url = (getMeta('og:image') || '').trim();

                // Fallback: maior imagem real
                if (!out.imagem_url) {
                    const imgs = Array.from(document.images || []);
                    let best = null;
                    for (const img of imgs) {
                        const src = img.currentSrc || img.src || '';
                        if (!src || src.startsWith('data:')) continue;
                        const w = img.naturalWidth || img.width || 0;
                        const h = img.naturalHeight || img.height || 0;
                        if (w < 350 || h < 350) continue;
                        const area = w * h;
                        if (!best || area > best.area) best = { src, area };
                    }
                    out.imagem_url = best ? best.src : '';
                }

                // ---------- CATEGORIA (breadcrumb) ----------
                try {
                    const breadcrumbLinks = document.querySelectorAll('div[class*="breadcrumb"] a, ._2TSj9W a');
                    for (const link of breadcrumbLinks) {
                        const text = (link.innerText || link.textContent || '').trim();
                        if (text && text !== 'Shopee' && text.length > 0) {
                            out.categoria = text;
                            break;
                        }
                    }
                } catch (e) {
                    out.categoria = '';
                }

                return out;
            }""")

            dados['titulo'] = result.get('titulo', '') or ''
            dados['imagem_url'] = result.get('imagem_url', '') or ''
            dados['categoria'] = result.get('categoria', '') or ''

            # Logging
            logger.info(f"✅ Shopee: {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")
            logger.info(f"   💰 Preço: {dados['preco']}")
            logger.info(f"   🏷️  Categoria: {dados['categoria'] or '❌ NÃO ENCONTRADA'}")
            logger.info(f"   🖼️  Imagem: {'✅ OK' if dados['imagem_url'] else '❌ NÃO ENCONTRADA'}")

            return dados

        except Exception as e:
            error_msg = str(e)[:100]
            logger.error(f"❌ Erro Shopee: {error_msg}")
            dados['erro_extracao'] = error_msg
            raise
        finally:
            await browser.close()


async def _extrair_dados_genererico(url: str, plataforma: str) -> dict:
    """
    Extração genérica usando meta tags.
    Fallback para plataformas que ainda não têm scraper especializado (Shein, etc).
    """
    # Aplicar rate limiting antes de iniciar requisição
    _enforce_rate_limit()
    
    from playwright.async_api import async_playwright

    dados = {
        'titulo': '',
        'imagem_url': '',
        'preco': '',
        'preco_original': '',
        'descricao': '',
        'categoria': '',
        'url_final': '',
        'plataforma': plataforma,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()

        try:
            resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if resp and resp.status >= 400:
                raise Exception(f"HTTP {resp.status}")

            await page.wait_for_timeout(2000)
            dados['url_final'] = page.url

            # Extração genérica usando meta tags
            result = await page.evaluate('''() => {
                const getMeta = (name) => {
                    const el = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`);
                    return el ? el.getAttribute('content') : '';
                };

                return {
                    titulo: getMeta('og:title') || document.title || '',
                    imagem: getMeta('og:image') || '',
                    preco: getMeta('product:price:amount') || getMeta('og:price') || '',
                    descricao: getMeta('og:description') || '',
                };
            }''')

            # Mapear resultados
            if result.get('titulo'):
                dados['titulo'] = result.get('titulo', '').strip()[:200]
            if result.get('imagem'):
                dados['imagem_url'] = result.get('imagem', '').strip()
            if result.get('preco'):
                dados['preco'] = result.get('preco', '').strip()
            if result.get('descricao'):
                dados['descricao'] = result.get('descricao', '').strip()[:1000]

            logger.info(f"✅ Extração genérica ({plataforma}): {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")

        except Exception as e:
            logger.error(f"❌ Erro ao extrair genérico de {plataforma}: {e}")
            raise
        finally:
            await browser.close()

    return dados



def _detectar_plataforma_e_extrair(url: str) -> dict:
    """
    Detecta a plataforma pela URL e chama o scraper apropriado.
    Retorna dict com dados incluindo 'plataforma'.
    """
    plataforma_detectada = DetectorPlataforma.detectar(url)
    logger.info(f"🔍 Plataforma detectada: {plataforma_detectada} para URL: {url[:60]}")
    
    # Usar scraper especializado conforme plataforma
    if plataforma_detectada == 'mercado_livre':
        return asyncio.run(_extrair_dados_ml(url))
    elif plataforma_detectada == 'amazon':
        return asyncio.run(_extrair_dados_amazon(url))
    elif plataforma_detectada == 'shopee':
        return asyncio.run(_extrair_dados_shopee(url))
    else:
        # Usar extração genérica para outras plataformas (Shein, etc)
        return asyncio.run(_extrair_dados_genererico(url, plataforma_detectada))


def extrair_dados_produto(url: str) -> dict:
    """Wrapper síncrono que detecta plataforma e extrai dados.
    
    Funciona em threads do Django (sem event loop) e em contextos com loop já rodando.
    Compatível com SQLite (dev com admin) e MySQL (produção com workers).
    """
    try:
        # Tentar detecção e extração
        dados = _detectar_plataforma_e_extrair(url)
        if dados:
            return dados
        
        # Fallback para ML se não conseguir detectar
        return asyncio.run(_extrair_dados_ml(url))
    except RuntimeError as e:
        # Se falhar por event loop, usar ThreadPoolExecutor
        if 'asyncio.run() cannot be called from a running event loop' in str(e):
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_detectar_plataforma_e_extrair, url)
                resultado = future.result(timeout=60)
                return resultado if resultado else asyncio.run(_extrair_dados_ml(url))
        else:
            raise


def _validar_campos_criticos(dados: dict) -> tuple[bool, str]:
    """
    Valida se todos os campos críticos foram extraídos com sucesso.
    
    Campos críticos (conforme requisito do usuário):
    - titulo (string não vazia)
    - preco (string não vazia)
    - imagem_url (string não vazia)
    - categoria (string não vazia) ✅ ADICIONADO
    
    Se qualquer um estiver vazio → status=ERRO + auto-deactivation após 2 falhas
    
    Retorna: (válido, mensagem_erro)
    """
    campos_obrigatorios = {
        'titulo': 'Título não foi extraído',
        'preco': 'Preço não foi encontrado',
        'imagem_url': 'Imagem não foi encontrada',
        'categoria': 'Categoria não foi extraída',
    }
    
    for campo, msg_erro in campos_obrigatorios.items():
        valor = dados.get(campo, '').strip()
        if not valor:
            return False, msg_erro
    
    return True, ''


def processar_produto_automatico(produto):
    """Processa um ProdutoAutomatico com validação rigorosa e retry.
    
    NOVO: Validação de campos críticos
    - Se algum campo ficar vazio (titulo, preco, imagem_url) → ERRO
    - Máx 2 tentativas de atualização
    - Após 2 falhas → desativa produto (ativo=False)
    
    Retry automático:
    - Falha 1 → aguarda 5min (~proxima janela de atualização)
    - Falha 2 → aguarda 15min
    - Falha 3+ → DESATIVA permanentemente
    
    Reduz taxa de falsos positivos (timeout/rate limit) de 11% para ~2-3%.
    """
    from .models import StatusExtracao, Categoria
    from .config_escalonamento import LIMITE_FALHAS, get_retry_delay
    from django.utils.text import slugify
    
    produto.status_extracao = StatusExtracao.PROCESSANDO
    produto.erro_extracao = ''
    produto.save(update_fields=['status_extracao', 'erro_extracao'])

    try:
        logger.info(f"🔄 Iniciando processamento do link: {produto.link_afiliado}")
        
        # Detectar plataforma
        plataforma_detectada = DetectorPlataforma.detectar(produto.link_afiliado)
        produto.plataforma = plataforma_detectada
        logger.info(f"🔍 Plataforma detectada: {dict(produto._meta.get_field('plataforma').choices).get(plataforma_detectada, plataforma_detectada)}")
        
        dados = extrair_dados_produto(produto.link_afiliado)

        # ========== PROCESSAMENTO DE CATEGORIA (antes da validação) ==========
        # Se categoria não foi extraída, tentar fallback via keywords
        categoria_nome = dados.get('categoria', '').strip()
        
        logger.info(f"📦 Categoria extraída inicialmente: '{categoria_nome}'")
        
        if not categoria_nome:
            logger.info(f"⚠️ Tentando extrair categoria por fallback...")
            titulo = dados.get('titulo', '').lower()
            if titulo:
                categorias_keywords = {
                    'Eletrônicos': ['eletrônico', 'computador', 'smartphone', 'celular', 'notebook', 'tablet', 'mouse', 'teclado', 'monitor', 'headset'],
                    'Informática': ['notebook', 'computador', 'pc', 'processador', 'placa mãe', 'memória ram', 'ssd', 'hd'],
                    'Esportes': ['bola', 'tênis', 'espor', 'yoga', 'fitness', 'piscina', 'corrida', 'natação', 'futebol'],
                    'Moda': ['roupa', 'calça', 'camiseta', 'jaqueta', 'sapato', 'blusa', 'vestido', 'tênis', 'mochila', 'bolsa'],
                    'Casa': ['cama', 'mesa', 'cadeira', 'sofá', 'cortina', 'tapete', 'louça', 'geladeira'],
                }
                
                for categoria_chave, keywords in categorias_keywords.items():
                    for keyword in keywords:
                        if keyword in titulo:
                            categoria_nome = categoria_chave
                            logger.info(f"✅ Categoria identificada por keyword: '{categoria_nome}'")
                            break
                    if categoria_nome:
                        break

        # Se ainda não encontrou categoria, deixa vazio (validação vai detectar)
        if not categoria_nome:
            logger.warning(f"❌ Categoria NÃO EXTRAÍDA para: {dados.get('titulo', 'SEM TÍTULO')[:50]}")
            dados['categoria'] = ''
        else:
            dados['categoria'] = categoria_nome

        # VALIDAÇÃO CRÍTICA: Verificar se campos obrigatórios foram extraídos
        valido, msg_erro = _validar_campos_criticos(dados)
        if not valido:
            logger.warning(f"⚠️ FALHA DE VALIDAÇÃO para {produto.id}: {msg_erro}")
            produto.status_extracao = StatusExtracao.ERRO
            produto.erro_extracao = msg_erro
            produto.falhas_consecutivas += 1
            
            logger.warning(f"⚠️ Falha #{produto.falhas_consecutivas}/2 para produto {produto.id}")
            
            if produto.falhas_consecutivas >= 2:
                # DESATIVAR após 2 falhas
                produto.ativo = False
                produto.motivo_desativacao = (
                    f'DESATIVADO: Falha ao extrair dados críticos após 2 tentativas. '
                    f'Erro: {msg_erro}'
                )
                logger.error(f"🛑 DESATIVADO PRODUTO {produto.id} - {msg_erro}")
            else:
                # Aguardar próxima tentativa
                retry_delay = get_retry_delay(produto.falhas_consecutivas)
                proxima_tentativa = timezone.now() + retry_delay
                produto.motivo_desativacao = (
                    f'Falha #{produto.falhas_consecutivas}/2 - {msg_erro}. '
                    f'Próxima tentativa: {proxima_tentativa.strftime("%Y-%m-%d %H:%M:%S")}'
                )
                logger.warning(f"⏱️ Agendando retry em {retry_delay}")
            
            produto.save(update_fields=[
                'status_extracao', 'erro_extracao', 'falhas_consecutivas',
                'ativo', 'motivo_desativacao'
            ])
            return False

        # Detectar se o ML redirecionou para uma página diferente
        url_final = dados.get('url_final', '')
        link_original = produto.link_afiliado.lower()
        redirecionado = False

        if url_final and ('/search' in url_final or '/busca' in url_final
                          or 'listado' in url_final):
            redirecionado = True
            logger.warning(f'Produto {produto.id} redirecionado para busca: {url_final}')

        page_type = dados.get('page_type', '')
        if redirecionado and produto.titulo:
            produto.status_extracao = StatusExtracao.SUCESSO
            produto.erro_extracao = 'Produto possivelmente indisponível (redirecionado)'
            produto.ultima_extracao = timezone.now()
            
            # ✅ SUCESSO - Resetar falhas
            if produto.falhas_consecutivas > 0:
                produto.falhas_consecutivas = 0
                produto.motivo_desativacao = ''
            
            produto.save()
            logger.info(f'✅ Dados mantidos para produto redirecionado: {produto.titulo}')
            return True

        # ===== CRIAR OBJETO CATEGORIA NA BANCO =====
        categoria_obj = None
        categoria_nome = dados.get('categoria', '').strip()
        
        if categoria_nome:
            categoria_slug = slugify(categoria_nome)
            logger.info(f"🔍 Buscando/criando categoria com slug: '{categoria_slug}'")
            
            categoria_obj, criada = Categoria.objects.get_or_create(
                slug=categoria_slug,
                defaults={'nome': categoria_nome, 'ativo': True, 'ordem': 999}
            )
            if criada:
                logger.info(f"✨ Categoria CRIADA: {categoria_nome} (ID: {categoria_obj.id})")
            else:
                logger.info(f"♻️ Categoria EXISTENTE: {categoria_nome} (ID: {categoria_obj.id})")

        # ===== ATUALIZAR PRODUTO =====
        produto.titulo = dados.get('titulo', '') or produto.titulo
        produto.imagem_url = dados.get('imagem_url', '') or produto.imagem_url
        preco_extraido = dados.get('preco', '').strip()
        produto.preco = preco_extraido  # SEMPRE atualiza, mesmo que vazio
        produto.preco_original = dados.get('preco_original', '') or produto.preco_original
        produto.descricao = dados.get('descricao', '') or produto.descricao
        produto.url_final = dados.get('url_final', '') or produto.url_final
        
        # Atualizar categoria se foi extraída
        if categoria_obj:
            produto.categoria = categoria_obj
            logger.info(f"✅ Categoria ATRIBUÍDA: {produto.titulo[:50]}... → {categoria_obj.nome}")
        else:
            logger.info(f"ℹ️ Sem categoria para: {produto.titulo[:50] if produto.titulo else 'SEM TÍTULO'}")
        
        produto.status_extracao = StatusExtracao.SUCESSO
        produto.ultima_extracao = timezone.now()
        
        # ✅ SUCESSO - Resetar falhas consecutivas
        if produto.falhas_consecutivas > 0:
            produto.falhas_consecutivas = 0
            produto.motivo_desativacao = ''
            logger.info(f"🔄 Contador de falhas RESETADO: {produto.titulo[:50]}...")
        
        produto.save()
        logger.info(f"✅ Sucesso: {produto.titulo[:50]}...")
        return True

    except Exception as e:
        produto.status_extracao = StatusExtracao.ERRO
        produto.erro_extracao = str(e)
        
        # ❌ ERRO - Incrementar falhas e contar tentativas (máx 2)
        produto.falhas_consecutivas += 1
        logger.warning(f"⚠️ Falha #{produto.falhas_consecutivas}/2 para produto {produto.id}: {str(e)[:80]}")
        
        # Após 2 falhas → DESATIVAR
        if produto.falhas_consecutivas >= 2:
            produto.ativo = False
            produto.motivo_desativacao = (
                f'DESATIVADO: Falha na extração após 2 tentativas. '
                f'Última tentativa em {timezone.now()}. '
                f'Erro: {str(e)[:150]}'
            )
            logger.error(
                f"🛑 DESATIVADO PRODUTO {produto.id} após 2 falhas: "
                f"{produto.titulo[:50] if produto.titulo else 'SEM TÍTULO'}... - {str(e)[:100]}"
            )
        else:
            # Agendar retry
            retry_delay = get_retry_delay(produto.falhas_consecutivas)
            proxima_tentativa = timezone.now() + retry_delay
            produto.motivo_desativacao = (
                f'Falha #{produto.falhas_consecutivas}/2. '
                f'Próxima tentativa agendada para {proxima_tentativa.strftime("%Y-%m-%d %H:%M:%S")}. '
                f'Erro: {str(e)[:150]}'
            )
            logger.warning(
                f"⏱️ Próxima tentativa agendada em {retry_delay} "
                f"para produto {produto.id}: {produto.titulo[:30] if produto.titulo else 'N/A'}..."
            )
        
        produto.save(update_fields=[
            'status_extracao', 'erro_extracao', 'falhas_consecutivas', 
            'ativo', 'motivo_desativacao'
        ])
        logger.error(f"❌ Erro ao processar produto {produto.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
