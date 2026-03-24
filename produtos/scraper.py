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
import logging
import re
import threading
import time
from django.utils import timezone
from .detector_plataforma import DetectorPlataforma, SELETORES, limpar_preco

logger = logging.getLogger(__name__)

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
    Scraper especializado para produtos Amazon.
    Extrai: título, preço, imagem, descrição com seletores específicos.
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
        'plataforma': 'amazon',
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

            await page.wait_for_timeout(3000)
            dados['url_final'] = page.url

            # Extrair dados específicos da Amazon
            result = await page.evaluate('''() => {
                const data = {
                    titulo: '',
                    preco: '',
                    preco_original: '',
                    imagem: '',
                    descricao: '',
                };

                // ===== TÍTULO =====
                // Estratégia 1: data-a-color com h1
                let titleEl = document.querySelector('h1 span[data-a-color]');
                if (titleEl) {
                    data.titulo = titleEl.textContent.trim();
                } else {
                    // Estratégia 2: product-title em span
                    titleEl = document.querySelector('#productTitle');
                    if (titleEl) {
                        data.titulo = titleEl.textContent.trim();
                    } else {
                        // Estratégia 3: meta og:title
                        const metaTitle = document.querySelector('meta[property="og:title"]');
                        if (metaTitle) {
                            data.titulo = metaTitle.getAttribute('content').trim();
                        }
                    }
                }

                // ===== PREÇO =====
                // Estratégia 1: corePriceDisplay_desktop_feature_div (preço principal)
                let priceContainer = document.querySelector('[data-a-color="price"] span.a-price-whole');
                if (priceContainer) {
                    data.preco = priceContainer.textContent.trim();
                } else {
                    // Estratégia 2: a-price com classe de dinheiro
                    priceContainer = document.querySelector('.a-price.a-text-price.a-size-medium.a-color-price span.a-price-whole');
                    if (priceContainer) {
                        data.preco = priceContainer.textContent.trim();
                    } else {
                        // Estratégia 3: buscar em qualquer data attribute de preço
                        const allSpans = document.querySelectorAll('span[data-a-size]');
                        for (const span of allSpans) {
                            const text = span.textContent.trim();
                            if (text.match(/^[R$\\d,.\\.]+/) && text.length < 20) {
                                data.preco = text;
                                break;
                            }
                        }
                    }
                }

                // ===== IMAGEM =====
                // Estratégia 1: imagem principal (#landingImage)
                let imgEl = document.querySelector('#landingImage, img#landingImage');
                if (imgEl && imgEl.src && !imgEl.src.startsWith('data:')) {
                    data.imagem = imgEl.src;
                } else {
                    // Estratégia 2: primeira imagem grande no carrossel
                    imgEl = document.querySelector('img.s-image');
                    if (imgEl && imgEl.src && !imgEl.src.startsWith('data:')) {
                        data.imagem = imgEl.src;
                    } else {
                        // Estratégia 3: og:image meta tag
                        const metaImg = document.querySelector('meta[property="og:image"]');
                        if (metaImg) {
                            data.imagem = metaImg.getAttribute('content');
                        }
                    }
                }

                // ===== DESCRIÇÃO =====
                // Estratégia 1: Feature bullets
                let descEl = document.querySelector('#feature-bullets');
                if (descEl) {
                    const items = descEl.querySelectorAll('li span');
                    data.descricao = Array.from(items)
                        .map(li => li.textContent.trim())
                        .filter(text => text.length > 0)
                        .slice(0, 3)
                        .join(' • ');
                } else {
                    // Estratégia 2: og:description
                    const metaDesc = document.querySelector('meta[property="og:description"]');
                    if (metaDesc) {
                        data.descricao = metaDesc.getAttribute('content');
                    } else {
                        // Estratégia 3: meta name description
                        const metaDesc2 = document.querySelector('meta[name="description"]');
                        if (metaDesc2) {
                            data.descricao = metaDesc2.getAttribute('content');
                        }
                    }
                }

                return data;
            }''')

            dados['titulo'] = result.get('titulo', '').strip()[:500]
            dados['preco'] = result.get('preco', '').strip()
            
            # Remover duplicações no preço (pode vir duplicado do DOM)
            if dados['preco']:
                parts = dados['preco'].split('R$')
                dados['preco'] = parts[-1].strip() if parts else dados['preco']
                if not dados['preco'].startswith('R$'):
                    dados['preco'] = f"R$ {dados['preco']}" if dados['preco'] else ""
                else:
                    dados['preco'] = dados['preco'].strip()
            
            dados['preco_original'] = result.get('preco_original', '').strip()
            dados['imagem_url'] = result.get('imagem', '').strip()
            dados['descricao'] = result.get('descricao', '').strip()[:1000]

            logger.info(f"✅ Extração Amazon: {dados['titulo'][:60]}")
            logger.info(f"   💰 Preço: {dados['preco']}")
            logger.info(f"   📷 Imagem: {'✓' if dados['imagem_url'] else '✗'}")

        except Exception as e:
            logger.error(f"❌ Erro ao extrair de Amazon: {e}")
            raise
        finally:
            await browser.close()

    return dados


async def _extrair_dados_genererico(url: str, plataforma: str) -> dict:
    """
    Extração genérica usando meta tags.
    Fallback para plataformas que ainda não têm scraper especializado (Shopee, Shein, etc).
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
    else:
        # Usar extração genérica para outras plataformas
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

        # Atualizar dados
        produto.titulo = dados.get('titulo', '') or produto.titulo
        produto.imagem_url = dados.get('imagem_url', '') or produto.imagem_url
        produto.preco = dados.get('preco', '') or produto.preco
        produto.preco_original = dados.get('preco_original', '') or produto.preco_original
        produto.descricao = dados.get('descricao', '') or produto.descricao
        produto.url_final = dados.get('url_final', '') or produto.url_final
        
        if categoria_obj:
            produto.categoria = categoria_obj
            logger.info(f"✅ Categoria ATRIBUÍDA: {produto.titulo[:50]}... → {categoria_obj.nome}")
        
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
