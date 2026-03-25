#!/usr/bin/env python
"""
TESTE DE INTEGRAÇÃO FINAL - ML + Shopee + Amazon
Valida que cada plataforma extrai corretamente sem quebrar as outras
"""

import asyncio
import sys
import logging
from datetime import datetime

# Configurar logging colorido
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_platform(platform_name: str, url: str, scraper_func):
    """Testa uma plataforma individual"""
    logger.info(f"\n{'='*70}")
    logger.info(f"🧪 TESTE: {platform_name}")
    logger.info(f"{'='*70}")
    logger.info(f"📍 URL: {url[:60]}...")
    
    try:
        logger.info(f"⏳ Extraindo dados...")
        dados = await scraper_func(url)
        
        logger.info(f"✅ Extração concluída!")
        logger.info(f"\n📊 Resultados:")
        logger.info(f"   Título: {dados.get('titulo', '-')[:60]}...")
        logger.info(f"   Preço: {dados.get('preco', '-')}")
        logger.info(f"   Preço Original: {dados.get('preco_original', '-')}")
        logger.info(f"   Imagem: {dados.get('imagem_url', '-')[:50]}...")
        logger.info(f"   Categoria: {dados.get('categoria', '-')}")
        
        # Validações básicas
        validacoes = {
            "✓ Título extraído": bool(dados.get('titulo')),
            "✓ Preço extraído": bool(dados.get('preco')),
            "✓ Imagem extraída": bool(dados.get('imagem_url')),
            "✓ URL final": bool(dados.get('url_final')),
        }
        
        logger.info(f"\n🔍 Validações:")
        for check, resultado in validacoes.items():
            status = "✅" if resultado else "⚠️ "
            logger.info(f"   {status} {check}")
        
        success = all(validacoes.values())
        return {
            'plataforma': platform_name,
            'sucesso': success,
            'dados': dados,
            'validacoes': validacoes
        }
        
    except Exception as e:
        logger.error(f"❌ ERRO em {platform_name}: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return {
            'plataforma': platform_name,
            'sucesso': False,
            'erro': str(e)[:100],
            'dados': {}
        }


async def main():
    """Executa testes em todas as plataformas"""
    from produtos.scraper import _extrair_dados_ml, _extrair_dados_shopee, _extrair_dados_amazon
    
    logger.info("\n" + "="*70)
    logger.info("🚀 TESTE DE INTEGRAÇÃO - TODAS PLATAFORMAS")
    logger.info("="*70)
    logger.info(f"🕐 Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # URLs de teste (use URLs reais que você quer testar)
    urls_teste = {
        "Mercado Livre": {
            "url": "https://produto.mercadolivre.com.br/MLB-1234567890-seu-produto",
            "func": _extrair_dados_ml,
            "skip": True  # Ajuste para False quando tiver URL real
        },
        "Shopee": {
            "url": "https://shopee.com.br/Luminaria-Redonda-LED-em-Arandela-de-parede-p-16950897-5bde5e1aefeb3f048f7c1c72e62e7ba0",
            "func": _extrair_dados_shopee,
            "skip": False
        },
        "Amazon": {
            "url": "https://www.amazon.com.br/seu-produto",
            "func": _extrair_dados_amazon,
            "skip": True  # Ajuste para False quando tiver URL real
        }
    }
    
    resultados = []
    
    for platform_name, config in urls_teste.items():
        if config['skip']:
            logger.warning(f"\n⏭️  PULANDO {platform_name} (sem URL de teste)")
            continue
        
        resultado = await test_platform(
            platform_name,
            config['url'],
            config['func']
        )
        resultados.append(resultado)
    
    # Resumo final
    logger.info(f"\n\n" + "="*70)
    logger.info("📋 RESUMO FINAL")
    logger.info("="*70)
    
    for resultado in resultados:
        status = "✅ PASSOU" if resultado['sucesso'] else "❌ FALHOU"
        logger.info(f"   {resultado['plataforma']}: {status}")
    
    total_sucesso = sum(1 for r in resultados if r['sucesso'])
    total = len(resultados)
    
    logger.info(f"\n🏁 Total: {total_sucesso}/{total} plataformas funcionando")
    
    if total_sucesso == total:
        logger.info("\n✅ TODAS AS PLATAFORMAS FUNCIONANDO!")
        return 0
    else:
        logger.warning(f"\n⚠️  {total - total_sucesso} plataforma(s) com problemas")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
