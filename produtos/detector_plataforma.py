"""
Detector de plataforma e funções de scraping multi-plataforma.
Suporta: Mercado Livre, Amazon, Shopee, Shein
"""
import re
from urllib.parse import urlparse


class DetectorPlataforma:
    """Detecta a plataforma de e-commerce pela URL."""

    PATTERNS = {
        'mercado_livre': [
            r'mercadolivre\.com\.br',
            r'meli\.la',
            r'mercadolibre\.com\.',  # Variações internacionais
        ],
        'amazon': [
            r'amzn\.to',
            r'amazon\.com\.br',
            r'amazon\.com(?!\.br)',
            r'amazon\.',
            r'amazon\.co\.uk',
            r'amazon\.de',
            r'amazon\.fr',
        ],
        'shopee': [
            r'shopee\.com\.br',
            r'shopee\.sg',
            r'shopee\.ph',
            r'shopee\.vn',
        ],
        'shein': [
            r'shein\.com\.br',
            r'shein\.com',
            r'shein\.co\.uk',
        ],
    }

    @classmethod
    def detectar(cls, url: str) -> str:
        """
        Detecta a plataforma pela URL.
        Retorna: 'mercado_livre', 'amazon', 'shopee', 'shein' ou 'outro'
        """
        url_lower = url.lower()
        
        for plataforma, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return plataforma
        
        return 'outro'

    @classmethod
    def eh_url_encurtada(cls, url: str) -> bool:
        """Verifica se é URL encurtada (amzn.to, meli.la, etc)."""
        url_lower = url.lower()
        encurtadores = [
            'amzn.to',
            'meli.la',
            'bit.ly',
            'tinyurl',
            'short.link',
        ]
        return any(enc in url_lower for enc in encurtadores)


# Seletores CSS por plataforma
SELETORES = {
    'mercado_livre': {
        'titulo': [
            'h1.ui-pdp-title',
            'h1',
            '[data-testid="product-title"]',
        ],
        'preco': [
            '.andes-money-amount__fraction',
            '.ui-pdp-price__main-container .ui-pdp-price__second-line',
            '[data-testid="price"]',
        ],
        'imagem': [
            'img.ui-pdp-image',
            '.ui-pdp-image-container img',
            '.ui-pdp__gallery [data-testid="image"]',
        ],
        'descricao': [
            '.ui-pdp-description__content',
            '[data-testid="product-description"]',
        ],
    },
    'amazon': {
        'titulo': [
            'h1 .product-title',
            'h1 span.a-size-large.a-spacing-none',
            '[data-cellid][data-a-color] h1',
            'h1',
        ],
        'preco': [
            '.a-price-whole',
            '.a-price.a-text-price.a-size-medium.a-color-price',
            '[data-a-color="price"]',
        ],
        'imagem': [
            'img.s-image',
            'img[alt*="product"]',
            '#landingImage',
        ],
        'descricao': [
            '#feature-bullets',
            '[data-feature-name*="about"]',
        ],
    },
    'shopee': {
        'titulo': [
            '.shopee-page-title',
            '[itemprop="name"]',
            'h1.nPopupTitle',
        ],
        'preco': [
            '.shopee-price-display',
            '[data-testid="product-price"]',
            '.shopee-product-rating',
        ],
        'imagem': [
            'img.shopee-zoom-image-wrapper-image',
            '[data-testid="product-images"] img',
            '.shopee-product-image',
        ],
        'descricao': [
            '.shopee-product-description',
            '[data-testid="product-description"]',
        ],
    },
    'shein': {
        'titulo': [
            '.productTitle',
            '[data-testid="product-name"]',
            'h1',
        ],
        'preco': [
            '.productPrice',
            '[data-testid="product-price"]',
            '.price-now',
        ],
        'imagem': [
            'img.productDetailImg',
            '[data-testid="product-image"]',
            '.productImg img',
        ],
        'descricao': [
            '.productDescription',
            '[data-testid="product-description"]',
        ],
    },
}


def extrair_com_fallback(page, seletores_list):
    """
    Tenta extrair usando uma lista de seletores CSS.
    Retorna o primeiro resultado não-vazio.
    """
    for seletor in seletores_list:
        try:
            elemento = page.query_selector(seletor)
            if elemento:
                text = elemento.text_content()
                if text and text.strip():
                    return text.strip()
        except Exception:
            pass
    return ''


def limpar_preco(texto_preco: str) -> str:
    """Limpa e formata preço extraído."""
    if not texto_preco:
        return ''
    
    # Remove espaços e caracteres especiais desnecessários
    preco = texto_preco.strip()
    preco = re.sub(r'[^\d,.]', '', preco)
    
    # Trata variações de separador decimal
    if ',' in preco and '.' in preco:
        # Se tem ambos, o último é decimal
        if preco.rfind(',') > preco.rfind('.'):
            # Formato brasileiro: 1.234,56
            preco = preco.replace('.', '').replace(',', '.')
        else:
            # Formato internacional: 1,234.56
            preco = preco.replace(',', '')
    else:
        # Apenas uma separação - pode ser ambígua
        # Assumir que é decimal se for < 3 casas após separador
        pass
    
    return preco
