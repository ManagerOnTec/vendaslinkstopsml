"""
Módulo de scraping para extrair dados de produtos do Mercado Livre.
Utiliza Playwright (browser headless) para contornar proteções anti-bot.

Suporta três tipos de página:
1. Página de produto individual (PDP) - extrai dados diretamente
2. Página de perfil social (afiliado) - extrai dados do produto em destaque
3. Outras páginas (busca, categoria) - extrai do primeiro produto listado
"""
import asyncio
import logging
import re
from django.utils import timezone

logger = logging.getLogger(__name__)


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


def extrair_dados_produto(url: str) -> dict:
    """Wrapper síncrono para a função assíncrona de extração.
    
    Funciona em threads do Django (sem event loop) e em contextos com loop já rodando.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Não há event loop na thread - criar um novo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Event loop já está rodando (contexto aninhado)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _extrair_dados_ml(url))
            return future.result(timeout=60)
    else:
        # Event loop existe mas não está rodando - usar normalmente
        return loop.run_until_complete(_extrair_dados_ml(url))


def processar_produto_automatico(produto):
    """Processa um ProdutoAutomatico: extrai dados do ML e atualiza o registro.
    
    Implementa desativação automática: após 5 falhas consecutivas, o produto
    é automaticamente desativado para economizar recursos.
    """
    from .models import StatusExtracao, Categoria
    from django.utils.text import slugify

    LIMITE_FALHAS = 2  # Constante de limite de falhas
    
    produto.status_extracao = StatusExtracao.PROCESSANDO
    produto.erro_extracao = ''
    produto.save(update_fields=['status_extracao', 'erro_extracao'])

    try:
        logger.info(f"🔄 Iniciando processamento do link: {produto.link_afiliado}")
        dados = extrair_dados_produto(produto.link_afiliado)

        # Detectar se o ML redirecionou para uma página diferente
        # (produto indisponível redireciona para busca/home)
        url_final = dados.get('url_final', '')
        link_original = produto.link_afiliado.lower()
        redirecionado = False

        # Se a URL final contém /search ou /busca, o produto foi redirecionado
        if url_final and ('/search' in url_final or '/busca' in url_final
                          or 'listado' in url_final):
            redirecionado = True
            logger.warning(
                f'Produto {produto.id} redirecionado para busca: {url_final}'
            )

        # Se o tipo de página é 'other' e já temos dados anteriores,
        # manter os dados anteriores (produto pode estar indisponível)
        page_type = dados.get('page_type', '')
        if redirecionado and produto.titulo:
            # Manter dados existentes, apenas atualizar status
            produto.status_extracao = StatusExtracao.SUCESSO
            produto.erro_extracao = 'Produto possivelmente indisponível (redirecionado)'
            produto.ultima_extracao = timezone.now()
            
            # ✅ SUCESSO - Resetar falhas
            if produto.falhas_consecutivas > 0:
                produto.falhas_consecutivas = 0
                produto.motivo_desativacao = ''
            
            produto.save()
            logger.info(f'Dados mantidos para produto redirecionado: {produto.titulo}')
            return True

        # Processar categoria se extraída
        categoria_obj = None
        categoria_nome = dados.get('categoria', '').strip()
        
        logger.info(f"📦 Page Type: {page_type}")
        logger.info(f"📊 Categoria extraída inicialmente: '{categoria_nome}'")
        
        # Se não extraiu categoria, tentar um fallback simples
        if not categoria_nome:
            logger.info(f"⚠️ Tentando extrair categoria por fallback...")
            # Tentar extrair palavras-chave do título
            titulo = dados.get('titulo', '').lower()
            if titulo:
                # Dicionário de categorias comuns no ML
                categorias_keywords = {
                    'Eletrônicos': ['eletrônico', 'computador', 'smartphone', 'celular', 'notebook', 'tablet', 'fone', 'webcam', 'monitor', 'tv', 'smart'],
                    'Informática': ['notebook', 'computador', 'pc', 'processador', 'placa mãe', 'memória ram', 'ssd', 'teclado', 'mouse', 'impressora'],
                    'Esportes': ['bola', 'tênis', 'espor', 'yoga', 'fitness', 'piscina', 'corrida', 'bicicleta', 'academia'],
                    'Moda': ['roupa', 'calça', 'camiseta', 'jaqueta', 'sapato', 'blusa', 'vestido', 'tênis esportivo'],
                    'Casa': ['cama', 'mesa', 'cadeira', 'sofá', 'cortina', 'tapete', 'louça', 'utensílio de cozinha'],
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
            # Criar ou obter a categoria
            categoria_slug = slugify(categoria_nome)
            logger.info(f"🔍 Buscando/criando categoria com slug: '{categoria_slug}'")
            
            categoria_obj, criada = Categoria.objects.get_or_create(
                slug=categoria_slug,
                defaults={
                    'nome': categoria_nome,
                    'ativo': True,
                    'ordem': 999  # Vai pro final, admin pode reordenar
                }
            )
            if criada:
                logger.info(f"✨ Categoria CRIADA automaticamente: {categoria_nome} (ID: {categoria_obj.id})")
            else:
                logger.info(f"♻️ Categoria EXISTENTE utilizada: {categoria_nome} (ID: {categoria_obj.id})")
        else:
            logger.warning(f"⚠️ Nenhuma categoria foi extraída do link: {produto.link_afiliado}")
            logger.warning(f"   Página type: {page_type}")

        # Atualizar dados normalmente
        produto.titulo = dados.get('titulo', '') or produto.titulo
        produto.imagem_url = dados.get('imagem_url', '') or produto.imagem_url
        produto.preco = dados.get('preco', '') or produto.preco
        produto.preco_original = dados.get('preco_original', '') or produto.preco_original
        produto.descricao = dados.get('descricao', '') or produto.descricao
        produto.url_final = dados.get('url_final', '') or produto.url_final
        
        if categoria_obj:
            produto.categoria = categoria_obj
            logger.info(f"✅ Categoria ATRIBUÍDA ao produto: {produto.titulo[:50]}... -> {categoria_obj.nome}")
        else:
            logger.warning(f"ℹ️ Nenhuma categoria para atribuir ao produto: {produto.titulo[:50]}...")
        
        produto.status_extracao = StatusExtracao.SUCESSO
        produto.ultima_extracao = timezone.now()
        
        # ✅ SUCESSO - Resetar falhas consecutivas
        if produto.falhas_consecutivas > 0:
            produto.falhas_consecutivas = 0
            produto.motivo_desativacao = ''
            logger.info(f"🔄 Contador de falhas RESETADO para {produto.titulo[:50]}...")
        
        produto.save()

        logger.info(f"✅ Dados extraídos com sucesso para: {produto.titulo[:50]}...")
        logger.info(f"   📁 Categoria final: {produto.categoria.nome if produto.categoria else 'Nenhuma'}")
        logger.info(f"   💰 Preço: {produto.preco}")
        logger.info(f"   📷 Imagem: {bool(produto.imagem_url)}")
        return True

    except Exception as e:
        produto.status_extracao = StatusExtracao.ERRO
        produto.erro_extracao = str(e)
        
        # ❌ ERRO - Incrementar falhas consecutivas
        produto.falhas_consecutivas += 1
        logger.warning(f"⚠️ Falha #{produto.falhas_consecutivas}/2 para produto {produto.id}")
        
        # 🛑 Se atingiu limite, desativar automaticamente
        if produto.falhas_consecutivas >= LIMITE_FALHAS:
            produto.ativo = False
            produto.motivo_desativacao = (
                f'Desativado automaticamente após 2 falhas consecutivas. '
                f'Última tentativa: {timezone.now()}. Erro: {str(e)[:100]}'
            )
            logger.error(
                f"🛑 DESATIVADO PRODUTO {produto.id}: {produto.titulo[:50]}... "
                f"(após 2 falhas)"
            )
        
        produto.save(update_fields=['status_extracao', 'erro_extracao', 'falhas_consecutivas', 'ativo', 'motivo_desativacao'])
        logger.error(f"❌ Erro ao processar produto {produto.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
