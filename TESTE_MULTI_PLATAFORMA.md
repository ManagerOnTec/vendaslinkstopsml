"""
GUIA DE TESTES - MULTI-PLATAFORMA NO DJANGO ADMIN
==================================================

PRÉ-REQUISITOS:
---------------
1. Django rodando localmente ou em produção
2. Acesso ao Django admin (/admin)
3. Products com URLs de diferentes plataformas

TESTE 1: Ação Renomeada (Verificação Visual)
---------------------------------------------
1. No admin, vá para: /admin/produtos/produtoautomatico/
2. Veja a listagem de produtos
3. No dropdown de "Ação": 
   ✓ ANTES: "Extrair/Atualizar dados do Mercado Livre"
   ✓ DEPOIS: "Extrair/Atualizar dados (Genérico - todas as plataformas)"
   ✓ Verificar: Ação agora menciona TODAS as plataformas (não apenas ML)

TESTE 2: Seleção de Apenas ML (Baseline)
-----------------------------------------
1. Selecionar produtos que têm links de Mercado Livre APENAS
2. Escolher ação: "Extrair/Atualizar dados (Genérico - todas as plataformas)"
3. Clicar: "Ir"
4. Verificar:
   ✓ Admin retorna mensagem: "X produto(s) enfileirado(s)..."
   ✓ Admin NÃO bloqueia (retorna rápido)
   ✓ Status dos produtos atualiza em background
   ✓ Dados extraídos corretamente (titulo, preço, imagem)

TESTE 3: Seleção de Apenas Amazon (Baseline)
----------------------------------------------
1. Selecionar produtos que têm links amazon APENAS
2. Escolher ação: "Extrair/Atualizar dados (Genérico - todas as plataformas)"
3. Clicar: "Ir"
4. Verificar:
   ✓ Admin retorna mensagem rápido
   ✓ Sem bloqueio
   ✓ Amazon scraper funciona
   ✓ Nenhum erro "service unavailable"

TESTE 4: CRÍTICO - Seleção Concomitante (ML + Amazon)
-----------------------------------------------------
Este é o teste que ANTES dava "503 Service Unavailable"

1. Selecionar produtos MIX:
   - Alguns com links de Mercado Livre
   - Alguns com links de Amazon
   - Alguns com links de Shopee/Shein (opcional)

2. Exemplo:
   □ Produto 1: amzn.to/... (Amazon)
   □ Produto 2: mercadolivre.com.br/... (ML)
   □ Produto 3: amzn.to/... (Amazon)
   □ Produto 4: shopee.com.br/... (Shopee)

3. Escolher ação: "Extrair/Atualizar dados (Genérico - todas as plataformas)"

4. Clicar: "Ir"

5. RESULTADO ESPERADO:
   ✓ Admin retorna IMEDIATAMENTE com mensagem:
     "✅ 4 produto(s) enfileirado(s) para extração. 
      Processamento acontecendo em background 
      (multi-plataforma: ML, Amazon, Shopee, Shein)..."
   ✓ NÃO bloqueia a requisição
   ✓ NÃO aparece "503 Service Unavailable"
   ✓ Processamento acontece em background
   ✓ Cada produto é extraído por seu scraper correto (ML ou Amazon ou Genérico)

6. Verificar após alguns segundos:
   ✓ Atualizar a página (/admin/produtos/produtoautomatico/)
   ✓ Os produtos têm títulos, preços, imagens preenchidas
   ✓ Status de extração é "sucesso"
   ✓ Contador de falhas = 0
   ✓ Campo "plataforma" mostra: "amazon", "mercado_livre", "shopee", "shein"

TESTE 5: Re-extrair (Ação Secondary)
------------------------------------
1. Selecionar vários produtos (mix de plataformas)
2. Escolher ação: "Re-extrair dados (forçar atualização - todas as plataformas)"
3. Clicar: "Ir"
4. Verificar:
   ✓ Status muda para "processando"
   ✓ Contador de falhas é zerado
   ✓ Admin retorna imediatamente
   ✓ Processamento em background
   ✓ Dados são atualizados

TESTE 6: Resetar Falhas (Ação Tertiary)
---------------------------------------
1. Selecionar produtos com status de erro ou desativados
2. Escolher ação: "Resetar contador de falhas e reativar"
3. Clicar: "Ir"
4. Verificar:
   ✓ Campo "falhas_consecutivas" = 0
   ✓ Campo "motivo_desativacao" = vazio
   ✓ Campo "ativo" = True (reativado!)
   ✓ Admin retorna mensagem: "X produto(s) reativado(s)..."

TESTE 7: Rate Limiting (Verificação de Performance)
--------------------------------------------------
1. Selecionar 10+ produtos (mix ML/Amazon)
2. Escolher ação: "Extrair/Atualizar dados..."
3. Clicar: "Ir"
4. Monitorar os logs:
   ✓ Deve aparecer delays de ~300ms entre requisições
   ✓ Máximo 2 requisições simultâneas (Semáforo)
   ✓ Nenhuma sobrecarga de servidor
   ✓ Nenhum erro de timeout

   Log esperado (em LOG_LEVEL=DEBUG):
   ```
   Rate limiting: aguardando 0.17s
   Rate limiting: aguardando 0.42s
   Rate limiting: aguardando 0.18s
   ...
   ```

TESTE 8: Verificação de Campo "plataforma"
------------------------------------------
Após qualquer extração, dentro de admin, ver:

1. Ir para um produto
2. Campo "Plataforma": (somente-leitura)
   ✓ Deve mostrar: "amazon", "mercado_livre", "shopee", "shein", "outro"
   ✓ Deve ser auto-preenchido via URL detection
   ✓ Não pode ser editado manualmente (read-only)

3. Filtro de Admin:
   ✓ No lado esquerdo, aparecem filtros:
      - Ativo (Sim/Não)
      - Status de Extração
      - Plataforma (com opções: Amazon, M. Livre, Shopee, Shein, Outro)
   ✓ Conseguir filtrar por plataforma

TESTE 9: Integração com Management Command
------------------------------------------
Se usar `python manage.py atualizar_produtos_ml`:
1. Executar: python manage.py atualizar_produtos_ml
2. Verificar:
   ✓ Método ainda funciona (compatível)
   ✓ Processa ML, Amazon, Shopee, Shein
   ✓ Usa mesmo scraper que o admin tá usando

TESTE 10: Admin Save Individual
-------------------------------
1. Abrir um produto existente no admin
2. Deixar campo de link afiliado como está
3. Clicar: "Salvar"
4. Verificar:
   ✓ Trá acionada extração automática (conforme código atual)
   ✓ Dados são extraídos
   ✓ Formulário retorna com dados preenchidos
   ✓ Sem bloqueios

VERIFICAÇÃO FINAL - ERROR HANDLING:
----------------------------------

Teste com URLs inválidas/quebradas:
1. Criar produto com URL inválida: https://exemplo.com/produto-inexistente
2. Selecionar e escolher "Extrair..."
3. Verificar:
   ✓ Admin retorna imediatamente (sem bloqueio mesmo com erro)
   ✓ Produto recebe status "erro"
   ✓ Contador de falhas incrementa
   ✓ Após 2 falhas, produto é desativado automaticamente
   ✓ Campo "motivo_desativacao" preenchido

CHECKLIST DE SUCESSO:
---------------------
✓ Seleção única ML funciona
✓ Seleção única Amazon funciona
✓ Seleção simultânea ML+Amazon funciona SEM 503
✓ Re-extrair funciona
✓ Resetar falhas funciona
✓ Rate limiting entre requisições (300ms)
✓ Máximo 2 requisições simultâneas
✓ Admin nunca bloqueia (retorna imediatamente)
✓ Plataforma detectada automaticamente
✓ Criptografia compatível com BD
✓ Sem "service unavailable" mesmo com 10+ produtos
✓ Todos os campos extraídos (título, preço, imagem, descrição)

TROUBLESHOOTING:
---------------
Se admin bloqueia = worker thread não iniciou
  Solução: Verificar se task_queue.py está importado em admin.py

Se "service unavailable" persiste = rate limiting não está funcionando
  Solução: Verificar logs de rate limiting
  Debug: python manage.py shell
         from produtos.task_queue import *
         print(get_queue_size())  # Deve ser < 3

Se plataforma não é detectada = detector_plataforma.py com erro
  Solução: Verificar URL está em padrão correto
  
Se apenas ML/Amazon não funciona = scraper específico com erro
  Solução: Ver logs de erro em produtos/scraper.py
"""
