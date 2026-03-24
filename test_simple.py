#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste simplificado sem logs - apenas resultados."""

import os, sys, django, logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
logging.disable(logging.CRITICAL)
django.setup()

from produtos.models import ProdutoAutomatico, StatusExtracao
from produtos.scraper import processar_produto_automatico

url = "https://amzn.to/4sEGjin"
print(f"\nTestando: {url}")

produto, _ = ProdutoAutomatico.objects.get_or_create(
    link_afiliado=url,
    defaults={'ativo': True, 'titulo': 'TEMP', 'preco': '0'}
)

print("Processando...")
processar_produto_automatico(produto)
produto.refresh_from_db()

print(f"\n[RESULTADO]")
print(f"  Titulo:   {produto.titulo[:60] if produto.titulo else '(vazio)'}")
print(f"  Preco:    {produto.preco or '(vazio)'}")
print(f"  Imagem:   {'SIM' if produto.imagem_url else 'NAO'}")
print(f"  Plataforma: {produto.plataforma}")
print(f"  Status:   {produto.status_extracao}")
print(f"  Falhas:   {produto.falhas_consecutivas}")

sucesso = (
    produto.titulo and len(produto.titulo) > 5 and
    '<' not in (produto.titulo or '') and
    'R$' in (produto.preco or '') and
    produto.imagem_url and 'http' in produto.imagem_url and
    produto.plataforma == 'amazon' and
    produto.status_extracao == StatusExtracao.SUCESSO
)

print(f"\n{'SUCESSO' if sucesso else 'COM ERROS'}: {url}\n")
sys.exit(0 if sucesso else 1)
