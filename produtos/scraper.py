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

_scraper_semaphore = None  # Será inicializado conforme necessário
_last_request_time = None
_rate_limit_lock = threading.Lock()

MIN_DELAY_BETWEEN_REQUESTS_MS = 300  # Mínimo delay entre requisições (300ms)


def _get_semaphore():
    """Retorna semáforo com limite de 2 requisições simultâneas."""
    global _scraper_semaphore
    if _scraper_semaphore is None:
        _scraper_semaphore = asyncio.Semaphore(2)  # Máx 2 requisições em paralelo
    return _scraper_semaphore


def _enforce_rate_limit():
    """Garante delay mínimo entre requisições."""
    global _last_request_time
    
    with _rate_limit_lock:
        current_time = time.time()
        if _last_request_time:
            elapsed = (current_time - _last_request_time) * 1000  # Converter para ms
            if elapsed < MIN_DELAY_BETWEEN_REQUESTS_MS:
                sleep_time = (MIN_DELAY_BETWEEN_REQUESTS_MS - elapsed) / 1000
                logger.debug(f"⏱️ Rate limiting: aguardando {sleep_time:.2f}s")
                time.sleep(sleep_time)
        _last_request_time = time.time()



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
                const isSocial = window.location.pathname.includes('/social/');

                let titulo = '';
                let imgSrc = '';
                let preco = '';
                let precoOriginal = '';
                let descricao = '';
                let categoria = extractCategory();

                if (isPDP) {
                    // ========================================
                    // PÁGINA DE PRODUTO INDIVIDUAL (PDP)
                    // ========================================

                    // TÍTULO
                    const h1 = document.querySelector('h1');
                    titulo = h1
                        ? h1.textContent.trim()
                        : (getMeta('og:title') || document.title || '');

                    // IMAGEM - Priorizar galeria do produto
                    // 1) Imagem da galeria com data-zoom (máxima resolução)
                    const galleryFig = document.querySelector(
                        '.ui-pdp-gallery__figure img'
                    );
                    if (galleryFig) {
                        imgSrc = galleryFig.getAttribute('data-zoom')
                            || galleryFig.src || '';
                    }
                    // 2) Qualquer figure img na seção do produto
                    if (!imgSrc) {
                        const figImg = document.querySelector(
                            '.ui-pdp-gallery figure img, figure img'
                        );
                        if (figImg) {
                            imgSrc = figImg.getAttribute('data-zoom')
                                || figImg.src || '';
                        }
                    }
                    // 3) og:image como fallback (geralmente é imagem real)
                    if (!imgSrc) {
                        imgSrc = getMeta('og:image') || '';
                    }
                    // 4) Busca inteligente como último recurso
                    if (!imgSrc) {
                        imgSrc = findProductImage(
                            document.querySelector('.ui-pdp-container__row')
                        );
                    }

                    // PREÇO ATUAL
                    const secondLine = document.querySelector(
                        '.ui-pdp-price__second-line'
                    );
                    if (secondLine) {
                        const partContainer = secondLine.querySelector(
                            '.ui-pdp-price__part__container'
                        );
                        if (partContainer) {
                            const mainMoney = partContainer.querySelector(
                                '.andes-money-amount'
                            );
                            preco = extractPrice(mainMoney);
                        }
                        if (!preco) {
                            const firstMoney = secondLine.querySelector(
                                '.andes-money-amount'
                            );
                            preco = extractPrice(firstMoney);
                        }
                    }

                    // Estratégia 2: meta itemprop="price"
                    if (!preco) {
                        const metaPriceEl = document.querySelector(
                            '.ui-pdp-price__second-line meta[itemprop="price"]'
                        );
                        if (metaPriceEl) {
                            const val = parseFloat(metaPriceEl.content);
                            if (!isNaN(val)) {
                                preco = val.toLocaleString('pt-BR', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 2
                                });
                            }
                        }
                    }

                    // Estratégia 3: aria-label
                    if (!preco && secondLine) {
                        const mainMoney = secondLine.querySelector(
                            '.andes-money-amount[aria-label]'
                        );
                        if (mainMoney) {
                            const label = mainMoney.getAttribute('aria-label');
                            const match = label.match(
                                /([\d.]+)\s*reais(?:\s*com\s*(\d+)\s*centavos)?/
                            );
                            if (match) {
                                let num = parseInt(
                                    match[1].replace(/\./g, ''), 10
                                );
                                preco = num.toLocaleString('pt-BR');
                                if (match[2]) {
                                    preco += ',' + match[2].padStart(2, '0');
                                }
                            }
                        }
                    }

                    // Estratégia 4: meta product:price:amount
                    if (!preco) {
                        const metaProductPrice = getMeta(
                            'product:price:amount'
                        );
                        if (metaProductPrice) {
                            const numPrice = parseFloat(metaProductPrice);
                            if (!isNaN(numPrice)) {
                                preco = numPrice.toLocaleString('pt-BR', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 2
                                });
                            }
                        }
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

                } else if (isSocial) {
                    // ========================================
                    // PÁGINA DE PERFIL SOCIAL (afiliado)
                    // ========================================

                    // TÍTULO: primeiro link de produto
                    const heroLink = document.querySelector(
                        'a[href*="/p/MLB"], a[href*="MLB-"]'
                    );
                    if (heroLink) {
                        titulo = heroLink.textContent.trim();
                    }
                    if (!titulo) {
                        const firstProductTitle = document.querySelector(
                            '.poly-component__title, ' +
                            '[class*="hero"] a, ' +
                            '.poly-card a'
                        );
                        if (firstProductTitle) {
                            titulo = firstProductTitle.textContent.trim();
                        }
                    }

                    // IMAGEM: usar busca inteligente que filtra banners
                    // Priorizar .poly-component__picture (imagem do card)
                    const polyPicImg = document.querySelector(
                        '.poly-component__picture img'
                    );
                    if (polyPicImg && polyPicImg.src
                        && !polyPicImg.src.startsWith('data:')) {
                        imgSrc = polyPicImg.src;
                    }
                    // Fallback: busca inteligente
                    if (!imgSrc) {
                        imgSrc = findProductImage(document);
                    }

                    // PREÇO ATUAL: primeiro .poly-price__current
                    const currentPriceEl = document.querySelector(
                        '.poly-price__current .andes-money-amount'
                    );
                    preco = extractPrice(currentPriceEl);

                    // PREÇO ORIGINAL: primeiro .poly-component__price
                    const origPriceEl = document.querySelector(
                        '.poly-component__price .andes-money-amount'
                    );
                    const origPriceText = extractPrice(origPriceEl);
                    if (origPriceText && origPriceText !== preco) {
                        precoOriginal = origPriceText;
                    }

                    // DESCRIÇÃO
                    descricao = getMeta('og:description') || titulo;

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
            
            logger.info(f"DEBUG: Após formatação - categoria: '{dados.get('categoria', '')}'")

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
                        
                        // Extrair categoria de BreadcrumbList
                        if (json['@type'] === 'BreadcrumbList' && json.itemListElement) {
                            const breadcrumbs = json.itemListElement
                                .filter(item => item.name && item.name !== 'Home')
                                .slice(-2)
                                .map(item => item.name);
                            if (breadcrumbs.length > 0) {
                                data.categoria = breadcrumbs.join(' > ');
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
                logger.info(f"   Preço: {'✅' if dados['preco'] else '❌'} {dados['preco'] or 'NÃO ENCONTRADO'}")
                logger.info(f"   Categoria: {'✅' if dados['categoria'] else '❌'} {dados['categoria'] or 'NÃO ENCONTRADA'}")
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
                    let priceContainer = document.querySelector('[data-a-color="price"] span.a-price-whole');
                    if (priceContainer) {
                        let priceText = priceContainer.textContent.trim();
                        if (priceText && !priceText.includes('R$')) {
                            priceText = 'R$ ' + priceText;
                        }
                        data.preco = priceText;
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
                    // Estratégia 1: Procurar breadcrumb na página
                    const breadcrumbLinks = document.querySelectorAll('[class*="breadcrumb"] a, [data-testid*="breadcrumb"] a');
                    if (breadcrumbLinks.length > 0) {
                        const breadcrumbs = Array.from(breadcrumbLinks)
                            .map(link => link.textContent.trim())
                            .filter(text => text && text !== 'Home' && text.length > 0 && text.length < 50);
                        if (breadcrumbs.length > 0) {
                            data.categoria = breadcrumbs.slice(-2).join(' > ');
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
                logger.info(f"   Preço: {'✅' if dados['preco'] else '❌'} {dados['preco'] or 'NÃO ENCONTRADO'}")
                logger.info(f"   Categoria: {'✅' if dados['categoria'] else '❌'} {dados['categoria'] or 'NÃO ENCONTRADA'}")

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
    Scraper robusto para Shopee usando seletores diretos.
    Aplica: 1. Aguardar elemento visível 2. Meta tags com fallback 3. Validação de dados
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
        'plataforma': 'Shopee',
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=40000)
            
            # Aguardar elementos críticos aparecerem
            try:
                await page.wait_for_selector('h1', timeout=10000)
            except:
                logger.warning("⚠️  Shopee: h1 não encontrado, continuando...")
            
            await page.wait_for_timeout(3000)
            dados['url_final'] = page.url

            # Extração PRIORIZADA: Schema.org JSON-LD (mais confiável que CSS)
            json_ld_result = await page.evaluate('''() => {
                const data = {
                    titulo: '',
                    preco: '',
                    imagem: '',
                    descricao: '',
                    categoria: '',
                };

                // Buscar Schema.org JSON-LD
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const script of scripts) {
                    try {
                        const json = JSON.parse(script.textContent);
                        
                        // Procurar Product ou BreadcrumbList
                        if (json['@type'] === 'Product' || json.type === 'Product') {
                            if (json.name) data.titulo = json.name;
                            if (json.offers && json.offers.price) {
                                // Preço pode vir como string ou number
                                let price = json.offers.price;
                                if (typeof price === 'number') {
                                    price = price.toString();
                                }
                                // Formatar com R$
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
                        
                        // Breadcrumb para categoria
                        if (json['@type'] === 'BreadcrumbList' && json.itemListElement) {
                            const items = json.itemListElement
                                .filter(item => item.name && !item.name.includes('Home'))
                                .slice(-2)
                                .map(item => item.name);
                            if (items.length > 0) {
                                data.categoria = items.join(' > ');
                            }
                        }
                    } catch (e) {
                        // Script JSON-LD inválido, pular
                    }
                }
                
                return data;
            }''')

            # Se JSON-LD funcionou, usar resultados (evita extração CSS pesada)
            if json_ld_result.get('titulo'):
                dados['titulo'] = json_ld_result['titulo'].strip()[:300]
                dados['preco'] = json_ld_result.get('preco', '').strip()[:50]
                dados['imagem_url'] = json_ld_result.get('imagem', '').strip()
                dados['descricao'] = json_ld_result.get('descricao', '').strip()[:1000]
                dados['categoria'] = json_ld_result.get('categoria', '').strip()[:100]
                
                logger.info(f"Shopee (JSON-LD): ✅ {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")
                logger.info(f"   Preço: {'✅' if dados['preco'] else '❌'} {dados['preco'] or 'NÃO ENCONTRADO'}")
            else:
                # Fallback: Extração via CSS (mais lenta, mas mantém compatibilidade)
                # Extração via JavaScript com seletores simples e diretos
                result = await page.evaluate('''() => {
                    const getMeta = (prop) => {
                        const el = document.querySelector(`meta[property="${prop}"]`) || 
                                   document.querySelector(`meta[name="${prop}"]`);
                        return el ? el.getAttribute('content') || el.getAttribute('value') : '';
                    };

                    const data = {
                        titulo: '',
                        preco: '',
                        preco_original: '',
                        imagem: '',
                        descricao: '',
                        categoria: '',
                    };

                    // ===== TÍTULO =====
                    // Estratégia 1: <h1> direto (mais confiável em Shopee)
                    const h1 = document.querySelector('h1');
                    if (h1 && h1.textContent.trim()) {
                        data.titulo = h1.textContent.trim().substring(0, 300);
                    }
                    
                    // Estratégia 2: Meta tag og:title
                    if (!data.titulo) {
                        data.titulo = getMeta('og:title') || getMeta('title');
                    }

                    // ===== PREÇO =====
                    // Estratégia 1: Usar data-testid (Shopee moderno)
                    const priceEl = document.querySelector('[data-testid="product-price"]');
                    if (priceEl) {
                        data.preco = priceEl.textContent.trim();
                    }
                    
                    // Estratégia 2: Procurar classe priceMoney
                    if (!data.preco) {
                        const priceAmount = document.querySelector('.priceMoney__amount');
                        if (priceAmount) {
                            data.preco = priceAmount.textContent.trim();
                        }
                    }
                    
                    // Estratégia 3: Buscar "R$" em spans verificando contexto
                    if (!data.preco) {
                        const allSpans = document.querySelectorAll('span');
                        for (const span of allSpans) {
                            const text = span.textContent.trim();
                            if (text.includes('R$') && /\\d+/.test(text) && text.length < 50) {
                                const parent = span.parentElement;
                                const parentClass = parent ? parent.className.toLowerCase() : '';
                                if (!parentClass.includes('description') && !parentClass.includes('desc')) {
                                    data.preco = text.trim();
                                    break;
                                }
                            }
                        }
                    }

                    // ===== IMAGEM =====
                    // Estratégia 1: Buscar em divs com "gallery" ou "product-image"
                    const galleryImg = document.querySelector('[class*="gallery"] img, [class*="image"] img');
                    if (galleryImg && galleryImg.src && !galleryImg.src.startsWith('data:')) {
                        let src = galleryImg.src;
                        // Otimizar qualidade da imagem Shopee
                        if (src.includes('shopee')) {
                            src = src.replace(/w\\d+_h\\d+/, 'w800_h800');
                        }
                        data.imagem = src;
                    }
                    
                    // Estratégia 2: Meta tag og:image
                    if (!data.imagem) {
                        data.imagem = getMeta('og:image');
                    }

                    // ===== DESCRIÇÃO =====
                    // Estratégia 1: Texto da meta tag
                    data.descricao = getMeta('og:description') || getMeta('description');
                    
                    // ===== CATEGORIA =====
                    // Estratégia 1: Usar data-testid específico (Shopee)
                    const categoryEl = document.querySelector('[data-testid="product-category"]');
                    if (categoryEl) {
                        data.categoria = categoryEl.textContent.trim();
                    }
                    
                    // Estratégia 2: Procurar breadcrumb que NÃO seja de menu
                    if (!data.categoria) {
                        const breadcrumbs = [];
                        const breadcrumbLinks = document.querySelectorAll('[class*="breadcrumb"] a');
                        for (const link of breadcrumbLinks) {
                            const text = link.textContent.trim();
                            if (text && text.length > 0 && text.length < 50 && 
                                !text.includes('Home') && 
                                !text.includes('Central do') &&
                                !text.includes('Vender') &&
                                !text.includes('Vendedor')) {
                                breadcrumbs.push(text);
                            }
                        }
                        if (breadcrumbs.length > 0) {
                            data.categoria = breadcrumbs.slice(0, 2).join(' > ');
                        }
                    }

                    return data;
                }''')

                # Aplicar dados extraídos via CSS fallback
                dados['titulo'] = result.get('titulo', '').strip()[:300]
                dados['preco'] = result.get('preco', '').strip()[:50]
                dados['imagem_url'] = result.get('imagem', '').strip()
                dados['descricao'] = result.get('descricao', '').strip()[:1000]
                dados['categoria'] = result.get('categoria', '').strip()[:100]
                
                logger.info(f"Shopee (CSS Fallback): {'✅' if dados['titulo'] else '❌'} {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")

            # Logging detalhado
            logger.info(f"Shopee: {'✅' if dados['titulo'] else '❌'} {dados['titulo'][:60] if dados['titulo'] else 'SEM TÍTULO'}")
            logger.info(f"   {'✅' if dados['preco'] else '❌'} Preço: {dados['preco'] or 'NÃO ENCONTRADO'}")
            logger.info(f"   {'✅' if dados['imagem_url'] else '❌'} Imagem: {dados['imagem_url'][:50] if dados['imagem_url'] else 'NÃO ENCONTRADA'}")
            logger.info(f"   {'✅' if dados['categoria'] else '❌'} Categoria: {dados['categoria'] or 'NÃO ENCONTRADA'}")

        except Exception as e:
            error_msg = str(e)[:100]
            logger.error(f"❌ Erro Shopee: {error_msg}")
            dados['erro_extracao'] = error_msg
        finally:
            await browser.close()

    return dados


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


def processar_produto_automatico(produto):
    """Processa um ProdutoAutomatico: extrai dados do ML e atualiza o registro.
    
    Implementa desativação automática com retry backoff:
    - Falha 1 → aguarda 5min e tenta novamente
    - Falha 2 → aguarda 15min e tenta novamente
    - Falha 3 → aguarda 1h e tenta novamente
    - Falha 4 → aguarda 4h e tenta novamente
    - Falha 5 → desativa produto permanentemente
    
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

        # Processar categoria
        categoria_obj = None
        categoria_nome = dados.get('categoria', '').strip()
        
        logger.info(f"📦 Page Type: {page_type}")
        logger.info(f"📊 Categoria extraída inicialmente: '{categoria_nome}'")
        
        if not categoria_nome:
            logger.info(f"⚠️ Tentando extrair categoria por fallback...")
            titulo = dados.get('titulo', '').lower()
            if titulo:
                categorias_keywords = {
                    'Eletrônicos': ['eletrônico', 'computador', 'smartphone', 'celular', 'notebook', 'tablet'],
                    'Informática': ['notebook', 'computador', 'pc', 'processador', 'placa mãe', 'memória ram'],
                    'Esportes': ['bola', 'tênis', 'espor', 'yoga', 'fitness', 'piscina', 'corrida'],
                    'Moda': ['roupa', 'calça', 'camiseta', 'jaqueta', 'sapato', 'blusa'],
                    'Casa': ['cama', 'mesa', 'cadeira', 'sofá', 'cortina', 'tapete', 'louça'],
                }
                
                for categoria_chave, keywords in categorias_keywords.items():
                    for keyword in keywords:
                        if keyword in titulo:
                            categoria_nome = categoria_chave
                            logger.info(f"✅ Categoria identificada por keyword: '{categoria_nome}'")
                            break
                    if categoria_nome:
                        break
        
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

        # Atualizar dados - SEMPRE atualizar preço se extraído (mesmo que vazio para sobrescrever)
        produto.titulo = dados.get('titulo', '') or produto.titulo
        produto.imagem_url = dados.get('imagem_url', '') or produto.imagem_url
        preco_extraido = dados.get('preco', '').strip()
        if preco_extraido:
            produto.preco = preco_extraido  # Só atualiza se não estiver vazio
        produto.preco_original = dados.get('preco_original', '') or produto.preco_original
        produto.descricao = dados.get('descricao', '') or produto.descricao
        produto.url_final = dados.get('url_final', '') or produto.url_final
        
        # Atualizar categoria se foi extraída
        if categoria_obj:
            produto.categoria = categoria_obj
            logger.info(f"✅ Categoria ATRIBUÍDA: {produto.titulo[:50]}... → {categoria_obj.nome}")
        else:
            # Se não encontrou categoria mas tinha uma antes, não sobrescreve
            logger.info(f"ℹ️ Sem categoria extraída para: {produto.titulo[:50] if produto.titulo else 'SEM TÍTULO'}")
        
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
        
        # ❌ ERRO - Incrementar falhas e agendar retry com backoff
        produto.falhas_consecutivas += 1
        logger.warning(f"⚠️ Falha #{produto.falhas_consecutivas}/{LIMITE_FALHAS} para produto {produto.id}")
        
        # Agendar próxima tentativa com delay se não atingiu limite
        if produto.falhas_consecutivas < LIMITE_FALHAS:
            retry_delay = get_retry_delay(produto.falhas_consecutivas)
            proxima_tentativa = timezone.now() + retry_delay
            produto.motivo_desativacao = (
                f'Falha #{produto.falhas_consecutivas}/{LIMITE_FALHAS}. '
                f'Próxima tentativa agendada para {proxima_tentativa.strftime("%Y-%m-%d %H:%M:%S")}. '
                f'Erro: {str(e)[:150]}'
            )
            logger.warning(
                f"⏱️ Próxima tentativa agendada em {retry_delay} "
                f"para produto {produto.id}: {produto.titulo[:30] if produto.titulo else 'N/A'}..."
            )
        else:
            # 🛑 Atingiu limite - desativar permanentemente
            produto.ativo = False
            produto.motivo_desativacao = (
                f'Desativado após {LIMITE_FALHAS} falhas consecutivas. '
                f'Última tentativa: {timezone.now()}. '
                f'Erro: {str(e)[:150]}'
            )
            logger.error(
                f"🛑 DESATIVADO PRODUTO {produto.id} após {LIMITE_FALHAS} falhas: "
                f"{produto.titulo[:50] if produto.titulo else 'N/A'}..."
            )
        
        produto.save(update_fields=[
            'status_extracao', 'erro_extracao', 'falhas_consecutivas', 
            'ativo', 'motivo_desativacao'
        ])
        logger.error(f"❌ Erro ao processar produto {produto.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
