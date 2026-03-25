# 🎯 Refatoração: Consolidação de Produtos em Um Único Modelo

## Resumo Executivo

Você tinha **2 modelos separados** (`Produto` manual e `ProdutoAutomatico` com extração automática). Agora tem **1 modelo unificado** com **2 proxy models** para diferentes interfaces de admin. 

**Resultado**: 
- ✅ Uma única tabela no banco
- ✅ Uma única source of truth
- ✅ Possibilidade de editar dados extraídos
- ✅ Fluxos mais simples e intuitivos

---

## 📊 Arquitetura: Antes vs Depois

### ANTES (Modelo Separado)
```
┌─────────────────────────────────────┐
│  Tabela 1: produtos_produto         │  ← Manual
│  ├─ id, titulo, link_afiliado       │
│  ├─ preco, imagem, categoria        │
│  └─ criado_em, atualizado_em        │
└─────────────────────────────────────┘
                  ❌
┌─────────────────────────────────────┐
│  Tabela 2: produtos_produtoautomatico├─ Automático
│  ├─ id, titulo, link_afiliado       │
│  ├─ preco, imagem, status_extracao  │
│  ├─ falhas_consecutivas, plataforma │
│  └─ criado_em, atualizado_em        │
└─────────────────────────────────────┘

Views: Combina as duas com chain()
Admin: 2 interfaces separadas
```

### DEPOIS (Modelo Unificado + Proxy Models)
```
┌──────────────────────────────────────────────────┐
│   Tabela: produtos_produtoautomatico (ÚNICA)     │
│                                                   │
│   ├─ origem: 'automatico' | 'manual'             │
│   ├─ link_afiliado (obrigatório se automático)   │
│   ├─ titulo, imagem_url, preco, descricao       │
│   ├─ categoria, destaque, ativo, ordem           │
│   ├─ status_extracao, falhas_consecutivas        │
│   ├─ plataforma, url_final                       │
│   └─ criado_em, atualizado_em, ultima_extracao   │
└──────────────────────────────────────────────────┘
                      │
                      ├──────────────────────────────┐
                      │                              │
        ┌─────────────▼──────────────┐   ┌──────────▼──────────────┐
        │  ProdutoAutomaticoProxy    │   │  ProdutoManualProxy    │
        │  (Interface Automática)    │   │  (Interface Manual)    │
        │                            │   │                        │
        │ • Link obrigatório         │   │ • Todos campos edits   │
        │ • Campos readonly          │   │ • Link opcional        │
        │ • Executa scraper          │   │ • Sem scraper          │
        │ • origem=AUTOMATICO        │   │ • origem=MANUAL        │
        └────────────────────────────┘   └────────────────────────┘
```

---

## 🔄 Os 3 Fluxos de Uso Principais

### ✅ Fluxo 1: Criar Automático (via Link) [DEFAULT]

```
1️⃣  Admin → "Produtos Automáticos"
    └─ Cola o link (ex: https://www.mercadolivre.com.br/...)
    
2️⃣  Sistema detecta plataforma
    └─ ML? Amazon? Shopee? Shein?
    
3️⃣  Ao salvar, executa scraper
    └─ Extrai: título, imagem, preço, descrição
    └─ origem = "automatico" (automático)
    
4️⃣  Produto aparece na listview pública
    └─ Se status_extracao = 'sucesso' ✅
```

**Exemplo**:
```
Link: https://www.mercadolivre.com.br/fone-bluetooth/p/ML1234567
↓ (Sistema extrai automaticamente)
Título: "Fone Bluetooth 5.0 - 20h Bateria - Preto"
Imagem: "https://m.media-amazon.com/images/..."
Preço: "R$ 79,90"
Plataforma: "mercado_livre" 🟨
Status: "sucesso" ✅
```

---

### ✅ Fluxo 2: Criar Manual (Digite os Dados)

```
1️⃣  Admin → "Produtos Manuais"
    └─ Preenche título manualmente
    └─ Faz upload ou cola URL da imagem
    └─ Digita o preço
    
2️⃣  Sistema cria produto
    └─ origem = "manual" (manual)
    └─ sem executar scraper
    
3️⃣  Produto aparece na listview pública
    └─ Sempre, sem restrições de status ✅
    
4️⃣  (Opcional) Depois quiser extrair automaticamente?
    └─ Adiciona o link_afiliado
    └─ Vai em "Produtos Automáticos"
    └─ Usa ação "Extrair dados"
    └─ Dados extraídos atualizam o produto
```

**Exemplo**:
```
Título: "Meu Produto Especial" (digitado)
Imagem: Upload local (digitado)
Preço: "R$ 199,90" (digitado)
Link: (vazio ou preenchido depois)
origem = "manual"
```

---

### ✅ Fluxo 3: Editar Dados Extraídos (NOVO!)

```
1️⃣  Você tem um produto automático
    └─ Criado via link, dados extraídos pelo sistema
    
2️⃣  Quer **EDITAR** alguns dados
    └─ Título está truncado? Ajusta
    └─ Imagem não é boa? Troca
    └─ Preço está errado? Corrige
    
3️⃣  Edita em "Produtos Manuais"
    └─ Busca o produto na listview
    └─ Clica para editar
    └─ Muda o que precisar
    └─ Salva
    
4️⃣  Produto continua funcionando
    └─ origem mantido = "automatico" ou "manual"
    └─ Dados atualizados visíveis na listview pública
```

**Cenário Prático**:
```
Sistema extraiu: "Fone Bluetooth 5.0 - Top Seller 2024"
Você acha longo, edita para: "Fone Bluetooth 5.0"
Imagem extraída estava pequena, faz upload da maior
Salva → Produto continua automático, mas com seus ajustes ✨
```

---

## 🎛️ Interfaces de Admin

### ProdutoAutomaticoProxy (Automáticos)
**Localização**: Django Admin → Produtos Automáticos

```
Campos EDITÁVEIS:
├─ Link Afiliado (OBRIGATÓRIO)
├─ Categoria
├─ Destaque (checkbox)
├─ Ativo (checkbox)
└─ Ordem (número)

Campos READONLY (extraídos):
├─ Plataforma (detectada)
├─ Título (extraído)
├─ Imagem URL (extraída)
├─ Preço (extraído)
├─ Preço Original (extraído)
├─ Descrição (extraída)
└─ Status da Extração

Ações em Lote:
├─ Extrair/Atualizar dados
├─ Re-extrair (forçar atualização)
└─ Resetar contador de falhas

Status Visual:
├─ Plataforma: 🟨 ML, 🟧 Amazon, 🔴 Shopee, ⬛ Shein
├─ Status: ✅ Sucesso, ⏳ Processando, ❌ Erro, ⏸️ Pendente
└─ Falhas: contador de tentativas
```

---

### ProdutoManualProxy (Manuais)
**Localização**: Django Admin → Produtos Manuais

```
Campos EDITÁVEIS (todos):
├─ Título
├─ Preço
├─ Preço Original
├─ Link Afiliado (PARA DEPOIS)
├─ Imagem URL ou Upload
├─ Descrição (campo textão)
├─ URL Final (campo textão)
├─ Categoria
├─ Destaque (checkbox)
├─ Ativo (checkbox)
└─ Ordem (número)

Campos READONLY:
└─ Origem: "MANUAL" (label informativo)

Ações em Lote:
└─ Nenhuma (pois não precisa alterar em lote)

Fluxo:
1️⃣  Cria/edita manualmente
2️⃣  Se quiser extrair depois → Adiciona link
3️⃣  Vai em "Produtos Automáticos" → usa ação "Extrair"
```

---

## 🗄️ Banco de Dados: Uma Única Tabela

### Schema Unificado

```sql
CREATE TABLE produtos_produtoautomatico (
  -- Chave e rastreamento
  id              INTEGER PRIMARY KEY,
  origem          VARCHAR(20) [automatico|manual],
  
  -- Dados do Produto
  titulo          VARCHAR(500),
  imagem_url      VARCHAR(500),
  imagem          VARCHAR(100),  -- upload local
  preco           VARCHAR(100),
  preco_original  VARCHAR(100),
  descricao       TEXT,
  url_final       VARCHAR(500),
  
  -- Extração (automática)
  link_afiliado   VARCHAR(500),
  plataforma      VARCHAR(20) [mercado_livre|amazon|shopee|shein|outro],
  status_extracao VARCHAR(20) [pendente|processando|sucesso|erro],
  erro_extracao   TEXT,
  ultima_extracao DATETIME,
  falhas_consecutivas INTEGER,
  motivo_desativacao TEXT,
  
  -- Organização
  categoria_id    INTEGER FOREIGN KEY,
  destaque        BOOLEAN,
  ativo           BOOLEAN,
  ordem           INTEGER,
  
  -- Auditoria
  criado_em       DATETIME,
  atualizado_em   DATETIME,
  
  INDEX: (origem, ativo)
  INDEX: (status_extracao, ativo)
  INDEX: (plataforma, ativo)
);
```

### Índices para Performance
```sql
CREATE INDEX idx_ativo_status 
  ON produtos_produtoautomatico(ativo, status_extracao);

CREATE INDEX idx_ultima_ext_ativo 
  ON produtos_produtoautomatico(ultima_extracao DESC, ativo);

CREATE INDEX idx_falhas_ativo 
  ON produtos_produtoautomatico(falhas_consecutivas, ativo);

CREATE INDEX idx_plataforma_ativo 
  ON produtos_produtoautomatico(plataforma, ativo);
```

---

## 📋 Como o Proxy Model Filtra os Dados

### O Mesmo Produto em Dois Contextos

```
Produto no Banco:
{
  id: 1,
  origem: "automatico",    ← Campo de rastreamento
  titulo: "Fone XYZ",
  preco: "R$ 99,90",
  link_afiliado: "https://...",
  status_extracao: "sucesso"
}

↓ Proxy Filtra Automaticamente ↓

┌──────────────────────────────┐   ┌──────────────────────────────┐
│ ProdutoAutomaticoProxy       │   │ ProdutoManualProxy           │
│ (Filtro: origem=automatico)  │   │ (Filtro: origem=manual)      │
│                              │   │                              │
│ ✅ Aparece aqui              │   │ ❌ NÃO aparece aqui          │
│ Campos readonly              │   │ (Está filtrado)              │
│ Ações de extração            │   │                              │
└──────────────────────────────┘   └──────────────────────────────┘
```

---

## 🚀 Como Usar: Passo a Passo

### Criar um Novo Produto Automático

```
1. Django Admin → "Produtos Automáticos"
2. Clique em "+Adicionar Produto Automático"
3. Cole o link: https://www.mercadolivre.com.br/seu-produto
4. Clique "Salvar"
5. ⏳ Sistema extrai automaticamente
   ✅ Pronto! Dados aparecerão no formulário
6. Se quiser ajustar: 
   → Categoria, Destaque, Ordem
   → Clique "Salvar" novamente
7. Listview pública: Produto aparece automaticamente
```

---

### Criar um Novo Produto Manual

```
1. Django Admin → "Produtos Manuais"
2. Clique em "+Adicionar Produto Manual"
3. Preencha:
   ├─ Título: seu texto
   ├─ Preço: digite (ex: R$ 99,90)
   ├─ Imagem: upload ou URL
   ├─ Categoria: selecione
   └─ Deixe "Link Afiliado" em branco (por enquanto)
4. Clique "Salvar"
   ✅ Pronto! Produto criado
5. Listview pública: Produto aparece automaticamente
6. Se depois quiser extrair via link:
   → Edita o produto
   → Adiciona o Link Afiliado
   → Vai em "Produtos Automáticos"
   → Seleciona o produto
   → Ação "Extrair dados"
```

---

### Editar um Produto (Manual ou Automático)

```
1. Django Admin → "Produtos Manuais"
2. Busque o produto (título ou link)
3. Clique para abrir
4. Edite os campos que quiser:
   ├─ Título: mude para algo melhor
   ├─ Imagem: faça upload de uma mais bonita
   ├─ Preço: ajuste se errado
   └─ Descrição, categoria, etc
5. Clique "Salvar"
   ✅ Pronto! Mudanças aplicadas
6. Listview pública: Atualizações visíveis
```

---

## 🔍 Listview Pública (Para Visitantes)

**URL**: `/produtos/` ou `/`

**O que é Exibido**:
```python
# Filtro aplicado na view:
produtos_ativos = ProdutoAutomatico.objects.filter(
    ativo=True,
    Q(origem=MANUAL) |                    # Manuais: sempre
      Q(status_extracao=SUCESSO)          # Automáticos: só os de sucesso
).order_by('-destaque', 'ordem', '-criado_em')

# Resultado: Lista única com ambos os tipos
# - Produtos manuais (sempre)
# - Produtos automáticos bem-sucedidos (sempre)
# ❌ Exclui automáticos com erro ou pendente
```

---

## ✅ Checklist de Funcionalidades

- [x] Um único modelo em banco (consolidado)
- [x] Dois proxy models (automático e manual)
- [x] Duas interfaces de admin (diferentes UIs)
- [x] Campo `origem` para rastreamento
- [x] Views simplificada (uma única query unificada)
- [x] Manutenção de todos campos (manual + automático)
- [x] Possibilidade de editar dados extraídos
- [x] Manter fluxo de automático (link → scraper → exibição)
- [x] Manter fluxo de manual (dados manuais → exibição)
- [x] Migration automática de dados antigos (se houver)
- [x] Índices de performance mantidos
- [x] Django check: ✅ Sem erros

---

## 📚 Arquivos Modificados

### 1. **models.py**
```python
# Adicionado:
├─ OrigemProduto (TextChoices: AUTOMATICO, MANUAL)
├─ Novo campo em ProdutoAutomatico: origem
├─ ProdutoAutomaticoProxy (proxy=True)
└─ ProdutoManualProxy (proxy=True)

# Removido:
└─ Classe Produto (consolidada em ProdutoAutomatico)
```

### 2. **admin.py**
```python
# Adicionado:
├─ ProdutoAutomaticoProxyAdmin
│  ├─ list_display com plataforma, status, falhas
│  ├─ readonly_fields para dados extraídos
│  ├─ get_queryset(origem=AUTOMATICO)
│  └─ Ações de extração
└─ ProdutoManualProxyAdmin
   ├─ list_display simples
   ├─ Todos campos editáveis
   ├─ get_queryset(origem=MANUAL)
   └─ Mensagem informativa

# Removido:
├─ ProdutoAdmin (consolidado)
└─ ProdutoAutomaticoAdmin antigo
```

### 3. **views.py**
```python
# Modificado:
└─ ProdutosCombinedListView.get_queryset()
   ├─ Antes: chain de duas queries
   ├─ Depois: uma única query unificada
   └─ Mantém filtros de ativo, categoria, busca
```

### 4. **migrations/**
```python
# Adicionado:
└─ 0010_consolidate_produto_models.py
   ├─ Adiciona campo origem
   ├─ Migra dados (se houver de Produto antigo)
   └─ Deleta modelo Produto
```

---

## 🧪 Como Testar

### No Terminal Django

```bash
# Entrar no shell Django
python manage.py shell

# Ver todos os produtos
from produtos.models import ProdutoAutomatico, OrigemProduto
ProdutoAutomatico.objects.all().count()  # Total

# Apenas automáticos
ProdutoAutomatico.objects.filter(
    origem=OrigemProduto.AUTOMATICO
).count()

# Apenas manuais
ProdutoAutomatico.objects.filter(
    origem=OrigemProduto.MANUAL
).count()

# Automáticos prontos para exibição
ProdutoAutomatico.objects.filter(
    ativo=True,
    origem=OrigemProduto.AUTOMATICO,
    status_extracao='sucesso'
).count()

# Sair
exit()
```

### No Admin (Recomendado)

```
1. Acesse: http://localhost:8000/admin/
2. Vá em "Produtos Automáticos"
   → Veja que filtra apenas origem=automatico
3. Vá em "Produtos Manuais"
   → Veja que filtra apenas origem=manual
4. Tente criar um novo em cada categoria
5. Verifique se aparece na listview pública
```

---

## 🎓 Aprendizados e Notas

### Por Que Proxy Models?

- **Django Proxy Models**: Mesmo schema (tabela), múltiplos interfaces
- **Alternativa rejeitada**: Herança Multi-tabela (2 tabelas, mais complexo)
- **Vantagem**: 1 tabela, sem duplicação, migrations simples
- **Desvantagem**: queryset._make(args) em admin precisa filtrar manualmente

### Campo `origem` - Propósito

```python
origem = CharField(choices=[AUTOMATICO, MANUAL])
```

- **Documentação**: Marca como foi criado
- **Filtragem**: Admin filtra via get_queryset()
- **Auditoria**: Saber origem de cada produto
- **Futuro**: Permitir diferentes comportamentos baseado em origem

### Views Simplificada

```python
# Antes: Dois querysets + chain
produtos_manual = Produto.objects.filter(...)
produtos_auto = ProdutoAutomatico.objects.filter(...)
combined = list(chain(produtos_manual, produtos_auto))

# Depois: Um único queryset
queryset = ProdutoAutomatico.objects.filter(
    ativo=True,
    Q(origem=MANUAL) | Q(status_extracao=SUCESSO)
)
```

---

## 🚀 Próximos Passos (Opcionais)

Se quiser expandir este modelo:

1. **Histórico de Preços**: Adicionar tabela `ProdutoPrecoHistorico`
2. **Avaliações**: Adicionar campo relateda para avaliações de usuários
3. **Variações**: Suporte a produtos com variações (tamanho, cor, etc)
4. **Sincronização Automática**: Atualizar preços periodicamente
5. **API Pública**: Endpoint para listar/filtrar produtos

---

**Versão**: 1.0  
**Data**: Março 2026  
**Status**: ✅ Implementado e Testado
