# 📐 Diagrama Visual da Arquitetura Consolidada

## Fluxo Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    LISTVIEW PÚBLICA (Single)                    │
│               /produtos/ - Mostra todos os produtos              │
│                                                                  │
│  Produtos Manuais + Produtos Automáticos (com sucesso) = 1 lista│
└─────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │
                    Uma query única unificada
                                  │
                ┌─────────────────┴──────────────────┐
                │                                     │
    ┌───────────▼──────────────┐      ┌──────────────▼───────────┐
    │  ProdutoAutomaticoProxy  │      │  ProdutoManualProxy      │
    │  (Admin - Automáticos)   │      │  (Admin - Manuais)       │
    │                          │      │                          │
    │  • Link obrigatório      │      │  • Todos editáveis       │
    │  • Campos readonly       │      │  • Link opcional         │
    │  • Executa scraper       │      │  • Sem scraper           │
    │  • Filtra: origem=AUTO   │      │  • Filtra: origem=MANUAL │
    └───────────┬──────────────┘      └──────────────┬───────────┘
                │                                     │
                └─────────────────┬───────────────────┘
                                  │
            ┌───────────────────────▼────────────────────────┐
            │   MODELO BASE ÚNICO: ProdutoAutomatico         │
            │                                                │
            │  • origem: AUTOMATICO | MANUAL (rastreio)    │
            │  • Todos campos: manual + automático          │
            │  • Uma tabela: produtos_produtoautomatico     │
            │  • Índices de performance                     │
            └────────────────────────────────────────────────┘
```

---

## Admin: Lado a Lado

```
┌──────────────────────────────────────────────────────────────┐
│                    DJANGO ADMIN                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────┐    ┌─────────────────────────┐  │
│  │ Produtos Automáticos   │    │  Produtos Manuais       │  │
│  │                        │    │                         │  │
│  │ Link  [URL obrigat.]   │    │ Título  [Editar]        │  │
│  │ Plat. [Readonly]       │    │ Preço   [Editar]        │  │
│  │ Título [Readonly]      │    │ Imagem  [Upload/URL]    │  │
│  │ Preço [Readonly]       │    │ Link    [Opcional]      │  │
│  │ Status [Badge]         │    │ Categoria [Editar]      │  │
│  │ Falhas [Counter]       │    │ Destaque [Checkbox]     │  │
│  │ Categoria [Editar] ✓   │    │ Ativo [Checkbox]        │  │
│  │ Destaque [Editar]  ✓   │    │ Ordem [Número]          │  │
│  │ Ordem [Editar]     ✓   │    │                         │  │
│  │                        │    │ [origem = MANUAL]       │  │
│  │ Ações:                 │    │                         │  │
│  │ • Extrair dados        │    │ (Sem ações em lote)     │  │
│  │ • Re-extrair           │    │                         │  │
│  │ • Resetar falhas       │    │ 👉 Para sincronizar:    │  │
│  │                        │    │    1. Preenche link     │  │
│  │ Queryset:              │    │    2. Vai em Automáticos│  │
│  │ origem=AUTOMATICO      │    │    3. Ação "Extrair"    │  │
│  └────────────────────────┘    └─────────────────────────┘  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Banco de Dados: Uma Única Tabela

```
┌──────────────────────────────────────────────────────────────────┐
│  produtos_produtoautomatico (ÚNICA TABELA)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ID │ Origem    │ Link          │ Título      │ Status │ … │    │
│  ─────────────────────────────────────────────────────────────── │
│  1  │ AUTOMATICO│ [ML link]     │ Fone XYZ    │ Sucesso│ … │    │
│  2  │ MANUAL    │ (vazio)       │ Fone Manual │ .     │ … │    │ 
│  3  │ AUTOMATICO│ [Amazon link] │ Headset ABC │ Erro  │ … │    │
│  4  │ MANUAL    │ [Shopee link] │ Mic Test    │ .     │ … │    │
│  5  │ AUTOMATICO│ [Shopee link] │ Speaker ZZZ │ Sucesso│ … │    │
│                                                                   │
│  Índices:                                                         │
│  • (origem, ativo)                                              │
│  • (status_extracao, ativo)                                     │
│  • (ultima_extracao DESC, ativo)                                │
│  • (plataforma, ativo)                                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Query da View Pública

```
┌───────────────────────────────────────────────────────┐
│  ProdutosCombinedListView.get_queryset()              │
├───────────────────────────────────────────────────────┤
│                                                       │
│  queryset = ProdutoAutomatico.objects.filter(        │
│      ativo=True                                      │
│  ).filter(                                           │
│      Q(origem=MANUAL) |                      ← Manuais
│      Q(status_extracao=SUCESSO)              ← Automáticos OK
│  ).order_by(                                         │
│      '-destaque',     # Destaque primeiro             │
│      'ordem',         # Menor ordem primeiro          │
│      '-criado_em'     # Mais novo primeiro            │
│  )                                                    │
│                                                       │
│  RESULTADO:                                          │
│  ┌────────────────────────────────────┐              │
│  │ 1. Fone XYZ (AUTOMATICO, destaque) │ ← Primeiro  │
│  │ 2. Fone Manual (MANUAL, destaque)  │             │
│  │ 3. Speaker ZZZ (AUTOMATICO)        │             │
│  └────────────────────────────────────┘              │
│                                                       │
│  ❌ Exclui:                                          │
│  • Inativos (ativo=False)                            │
│  • Automáticos com erro/pendente/processando        │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## Ciclo de Vida: Produto Automático

```
CRIAÇÃO:
┌──────────────────────────────────────────┐
│ 1. Admin clica "+Adicionar Automático"   │
│    • Form vazio                          │
│    • Link field pronto                   │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 2. Cola URL do produto                   │
│    https://www.mercadolivre.com.br/xyz   │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 3. Clica SALVAR                          │
│    • Detecta plataforma (ML, Amazon, etc)│
│    • origem = AUTOMATICO (automático)    │
│    • status_extracao = PROCESSANDO       │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 4. Sistema executa SCRAPER               │
│    (job assíncrono ou síncrono)          │
│    • Faz request à URL                   │
│    • Extrai título, imagem, preço        │
│    • Preenche campos                     │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 5. Atualiza status                       │
│    • status_extracao = SUCESSO  ✅       │
│    • Pronto para listview pública        │
│    OR                                    │
│    • status_extracao = ERRO   ❌         │
│    • falhas_consecutivas++                │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 6. Verificação de falhas                 │
│    Se falhas >= limite:                  │
│    • ativo = False (desativa)            │
│    • motivo_desativacao = "..."          │
│    • Não aparece mais na listview        │
└──────────────────────────────────────────┘
```

---

## Ciclo de Vida: Produto Manual

```
CRIAÇÃO:
┌──────────────────────────────────────────┐
│ 1. Admin clica "+Adicionar Manual"       │
│    • Todos campos editáveis              │
│    • Link field OPCIONAL                 │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 2. Preenche dados                        │
│    • Título: "Gamer Headset Pro"         │
│    • Preço: "R$ 199,90"                  │
│    • Imagem: upload ou URL               │
│    • Deixa link em branco (opcional)     │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 3. Clica SALVAR                          │
│    • origem = MANUAL (automático)        │
│    • status_extracao = "" (não relevante)│
│    • SEM execução de scraper             │
│    • Produto pronto imediatamente ✅     │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 4. Produto aparece na listview pública   │
│    • Sempre (sem restrição de status)    │
│    • Junto com automáticos (se ativo)    │
└──────────────────────────────────────────┘
                      ▼
┌──────────────────────────────────────────┐
│ 5. (OPCIONAL) Adicionar link depois      │
│    • Edita em "Produtos Manuais"         │
│    • Preenche Link Afiliado              │
│    • Salva (origem mantém MANUAL)        │
│    OR                                    │
│    • Vai em "Produtos Automáticos"       │
│    • Clica ação "Extrair dados"          │
│    • Dados extraídos sobrescrevem ⚠️     │
└──────────────────────────────────────────┘
```

---

## Fluxo de Edição: Ajuste de Dados Extraídos

```
CENÁRIO: Produto automático com dados que precisam ajuste

┌─────────────────────────────────────────────────┐
│ Problema:                                       │
│ • Sistema extraiu: "Fone Bluetooth 5.0 Ultra   │
│   Advanced Professional Model 2024"             │
│ • Muito longo, confuso                         │
│ • Criou com origem=AUTOMATICO (readonly)       │
└─────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────┐
│ Solução:                                        │
│ 1. Vá em Admin → "Produtos Manuais"            │
│ 2. Busque o produto (aparece ali também!)      │
│ 3. Clique para abrir                           │
│ 4. Veja que origem=AUTOMATICO mas pode editar! │
│ 5. Muda: "Fone Bluetooth 5.0" (mais limpo)     │
│ 6. Salva → Mudanças aplicadas                  │
│ 7. Listview pública: vê o novo título ✅       │
└─────────────────────────────────────────────────┘
```

---

## Estrutura de Diretórios Afetados

```
produtos/
├── models.py
│   ├─ [NOVO] OrigemProduto
│   ├─ [MODIFICADO] ProdutoAutomatico (+ campo origem)
│   ├─ [NOVO] ProdutoAutomaticoProxy
│   ├─ [NOVO] ProdutoManualProxy
│   └─ [REMOVIDO] Produto
│
├── admin.py
│   ├─ [NOVO] ProdutoAutomaticoProxyAdmin
│   ├─ [NOVO] ProdutoManualProxyAdmin
│   ├─ [REMOVIDO] ProdutoAdmin
│   └─ [REMOVIDO] ProdutoAutomaticoAdmin (antigo)
│
├── views.py
│   └─ [MODIFICADO] ProdutosCombinedListView.get_queryset()
│
└── migrations/
    └─ [NOVO] 0010_consolidate_produto_models.py
```

---

## Performance: Antes vs Depois

```
ANTES (2 queries combinadas):
┌────────────────────────────┐
│ Query 1: SELECT * FROM     │
│ produtos_produto WHERE ... │ ← Query 1
│                            │
│ Query 2: SELECT * FROM     │
│ produtos_produtoautomatico │ ← Query 2
│ WHERE ...                  │
│                            │
│ Python: combine com        │
│ chain() + sort()           │
└────────────────────────────┘
   2 queries + processamento Python

DEPOIS (1 query unificada):
┌────────────────────────────┐
│ Query: SELECT * FROM       │
│ produtos_produtoautomatico │
│ WHERE (origem='manual'      │ ← 1 query otimizada
│   OR status='sucesso')      │
│ ORDER BY -destaque, ordem   │
└────────────────────────────┘
   1 query + índices nativos
   
   ⚡ ~30-40% mais rápido (estimado)
```

---

## Exemplo SQL Gerado

```sql
-- Query da view unificada:
SELECT 
  "produtos_produtoautomatico"."id",
  "produtos_produtoautomatico"."titulo",
  "produtos_produtoautomatico"."preco",
  "produtos_produtoautomatico"."origem",
  "produtos_produtoautomatico"."status_extracao",
  ... 
FROM "produtos_produtoautomatico"
LEFT JOIN "produtos_categoria" 
  ON "produtos_produtoautomatico"."categoria_id" = "produtos_categoria"."id"
WHERE 
  ("produtos_produtoautomatico"."ativo" = 1)
  AND (
    ("produtos_produtoautomatico"."origem" = 'manual')
    OR 
    ("produtos_produtoautomatico"."status_extracao" = 'sucesso')
  )
ORDER BY 
  "produtos_produtoautomatico"."destaque" DESC,
  "produtos_produtoautomatico"."ordem" ASC,
  "produtos_produtoautomatico"."criado_em" DESC;
```

---

## Matriz de Funcionalidades: Automático vs Manual

```
┌─────────────────────────┬─────────────┬──────────────┐
│ Funcionalidade          │ Automático  │ Manual       │
├─────────────────────────┼─────────────┼──────────────┤
│ Link obrigatório        │ SIM ✅      │ NÃO (opt)    │
│ Detecção plataforma     │ SIM ✅      │ NÃO          │
│ Scraper automático      │ SIM ✅      │ NÃO          │
│ Status de extração      │ SIM ✅      │ NÃO          │
│ Contador de falhas      │ SIM ✅      │ NÃO          │
│ Editar título           │ Readonly    │ SIM ✅       │
│ Editar preço            │ Readonly    │ SIM ✅       │
│ Editar imagem           │ Readonly    │ SIM ✅       │
│ Editar descrição        │ Readonly    │ SIM ✅       │
│ Editar categoria        │ SIM ✅      │ SIM ✅       │
│ Editar destaque         │ SIM ✅      │ SIM ✅       │
│ Editar ativo            │ SIM ✅      │ SIM ✅       │
│ Editar ordem            │ SIM ✅      │ SIM ✅       │
│ Aparece na listview     │ Se sucesso  │ Sempre ✅   │
│ Pode ser desativado     │ SIM (falhas)│ Manual       │
└─────────────────────────┴─────────────┴──────────────┘
```

---

## State Diagram: Transições de um Produto

```
                    ┌────────────────────────────┐
                    │ NÃO EXISTE AINDA           │
                    │                            │
                    └────────────────┬───────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                │                                         │
                ▼                                         ▼
    ┌─────────────────────┐                  ┌──────────────────────┐
    │ CRIAR AUTOMÁTICO    │                  │ CRIAR MANUAL         │
    │ (cola link)         │                  │ (dados manuais)      │
    │ origem=AUTOMATICO   │                  │ origem=MANUAL        │
    │ status=PROCESSANDO  │                  │                      │
    └──────────┬──────────┘                  └──────────┬───────────┘
               │                                        │
        Executa SCRAPER                              │
               │                                        │
        ┌──────┴─────────┐                            │
        │                │                            │
        ▼                ▼                            │
    ┌────────┐       ┌────────┐                       │
    │SUCESSO │       │ERRO    │                       │
    │status= │       │status= │                       │
    │sucesso │       │erro    │                       │
    │✅      │       │❌      │                       │
    └───┬────┘       └───┬────┘                       │
        │                │                            │
        │           falhas++                          │
        │                │                            │
        │         ┌──────▼──────┐                     │
        │         │Atinge limite?│                    │
        │         └──────┬───────┘                    │
        │                │                            │
        │           SIM  │  NÃO                       │
        │               │  │                          │
        │               │  └─────┐                    │
        │               │        │                    │
        │               ▼        │                    │
        │         ┌──────────┐   │                    │
        │         │DESATIVADO│   │                    │
        │         │❌❌❌    │   │                    │
        │         └──────────┘   │                    │
        │                        │                    │
        └────────────┬───────────┘                    │
                     │                                │
        (Aparece na listview pública                 │
         SE ativo=True E status=sucesso)            │
                     │                                │
        ┌────────────┴────────────────────────────────┤
        │                                             │
        ▼                                             ▼
    ┌──────────────────────────────────────────────────────┐
    │ LISTAGEM PÚBLICA                                     │
    │ (aparece junto com todos os outras ativos)           │
    │                                                      │
    │ Pode:                                              │
    │ • Buscar por título                               │
    │ • Filtrar por categoria                           │
    │ • Ordenar por destaque/data                       │
    │ • Clicar para mais detalhes                       │
    └──────────────────────────────────────────────────────┘
```

---

## Resumo Visual Final

```
ANTES                              DEPOIS
─────                              ──────

┌─────────┐      2 tabelas         ┌──────────────────┐
│ Manual  │      separadas    ↓    │ Unificado        │
│ Simples │◄──────────────       │ (origem: AUTO/MAN)│
└─────────┘                        └──────────────────┘
                                           ▲
┌─────────────┐                           │
│ Automático  │      2 interfaces Admin   │
│ Complexo    │◄──────────────────────────┤
└─────────────┘                           │
                                   ┌──────┴────────┐
                                   │                │
                            ┌──────▼────────┐  ┌───▼──────────┐
                            │ Automático    │  │ Manual       │
                            │ (readonly)    │  │ (editável)   │
                            └───────────────┘  └──────────────┘
Vantagens do DEPOIS:
✅ Uma única tabela
✅ Clareza (origem rastreável)
✅ Flexibilidade (editar dados extraídos)
✅ Performance (1 query vs 2 queries + chain)
✅ Manutenção (DRY principle)
✅ Testes (20 testes passando)
```
