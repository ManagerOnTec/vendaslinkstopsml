# 📋 Logs Melhorados para Rastreamento de Extração

## 🎯 Objetivo

Adicionar logs **detalhados** que mostram:
- ✅ **DE ONDE** cada preço foi extraído (qual seletor/estratégia)
- ✅ **POR QUAL PROCESSO** foi obtido (TreeWalker, RegEx, JSON-LD, CSS, etc)
- ✅ **QUANTAS TENTATIVAS** foram necessárias
- ✅ Se é **faixa de preço** ou **preço simples**
- ✅ Se **desconto foi detectado**

## 📊 Formato de Log Implementado

### Shopee - Faixa de Preço
```
✅ Shopee: Mochila Grande De Lona 50 Litros Reforçada Para Viagens
   💰 Preço: R$ 39,99
      └─ Estratégia: TreeWalker (Faixa) | Tentativas: 3
   📌 Preço Original: R$ 43,99
      └─ Extraído da faixa (desconto detectado)
   🖼️  Imagem: ✅ OK
```

### Shopee - Preço Simples
```
✅ Shopee: Mochilas Viagem Impermeável Reforçada Com Cabo
   💰 Preço: R$ 149,90
      └─ Estratégia: TreeWalker (Simples) | Tentativas: 1
   📌 Preço Original: (sem desconto)
   🖼️  Imagem: ✅ OK
```

### Shopee - Fallback RegEx
```
✅ Shopee: Produto com Extração Problemática
   💰 Preço: R$ 79,99
      └─ Estratégia: RegEx Fallback (Faixa) | Tentativas: 5
   📌 Preço Original: R$ 99,90
      └─ Extraído da faixa (desconto detectado)
```

### Mercado Livre - Estratégia 1 (Melhor Preço)
```
✅ Mercado Livre: Notebook Gamer Intel i7
   💰 Preço: R$ 199,90
      └─ Estratégia: Melhor Preço (Estratégia 1)
   📌 Preço Original: (sem desconto)
   🏷️  Categoria: Informática
```

### Mercado Livre - Estratégia 2 (Ofertas com Desconto)
```
✅ Mercado Livre: Teclado Gaming RGB
   💰 Preço: R$ 89,99
      └─ Estratégia: Ofertas (Estratégia 2)
   📌 Preço Original: R$ 129,90
      └─ Desconto detectado
   🏷️  Categoria: Periféricos
```

### Amazon - JSON-LD (Mais Confiável)
```
Amazon (JSON-LD): ✅ Smartphone Samsung Galaxy S24
   💰 Preço: R$ 1.299,00
      └─ Estratégia: Schema.org JSON-LD (mais confiável)
   🏷️  Categoria: Eletrônicos
```

### Amazon - CSS Fallback
```
Amazon (CSS Fallback): ✅ Smart TV LG 55 polegadas
   💰 Preço: R$ 459,99
      └─ Estratégia: CSS Selectors (.a-price-whole, span.a-offscreen, etc)
   🏷️  Categoria: Televisores
```

## 🔍 Informações Rastreadas

### Para Shopee:

| Campo | Informação |
|-------|-----------|
| **Estratégia** | `TreeWalker (Faixa)` \| `TreeWalker (Simples)` \| `RegEx Fallback (Faixa)` \| `RegEx Fallback (Simples)` |
| **Tentativas** | Número de pontos de texto verificados antes de encontrar preço válido |
| **Faixa** | Se tem hífen com 2 preços → separa em `preco` (menor) + `preco_original` (maior) |
| **Desconto** | Indica se `preco_original` foi extraído da faixa |

### Para Mercado Livre:

| Campo | Informação |
|-------|-----------|
| **Estratégia** | `Melhor Preço (Estratégia 1)` \| `Ofertas (Estratégia 2)` \| `Preço do Vendedor (Estratégia 3)` |
| **Prioridade** | Segue ordem: 1 → 2 → 3, usa primeira que funcionar |
| **Desconto** | Indica se `preco_original` foi encontrado |

### Para Amazon:

| Campo | Informação |
|-------|-----------|
| **Método** | `Schema.org JSON-LD (mais confiável)` - obtém valor estruturado do HTML |
| **Fallback** | `CSS Selectors` - busca elementos visuais no DOM |
| **Confiabilidade** | JSON-LD > CSS (JSON-LD não depende de layout dinâmico) |

## 🛠️ Implementação Técnica

### Shopee (JavaScript)

```javascript
// Rastreia estratégia e tentativas
let estrategiaUsada = '';
let tentativasCount = 0;

// TreeWalker para busca ordenada
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);

while (node = walker.nextNode()) {
    tentativasCount++;
    // ... validação ...
    if (encontrou) {
        estrategiaUsada = 'TreeWalker (Faixa)'; // ou Simples
        break;
    }
}

// Fallback com regex
if (!encontrou) {
    const matches = bodyText.match(/R\$\s*[\d.,\s\-]+/g);
    for (const match of matches) {
        tentFallback++;
        // ... validação ...
    }
    estrategiaUsada = 'RegEx Fallback (Faixa)'; // ou Simples
}

// Retornar com metadados
out._debug_preco = {
    estrategia: estrategiaUsada,
    tentativas: tentativasCount,
    original: precoOriginal || 'não encontrado'
};
```

### Mercado Livre (JavaScript)

```javascript
// Função retorna objeto com estratégia
const extractMLPrice = () => {
    // Estratégia 1
    if (encontrou_melhor_preco) {
        return { price, estrategiaUsada: 'Melhor Preço (Estratégia 1)' };
    }
    
    // Estratégia 2
    if (encontrou_oferta) {
        return { price, estrategiaUsada: 'Ofertas (Estratégia 2)' };
    }
    
    // Estratégia 3
    if (encontrou_vendedor) {
        return { price, estrategiaUsada: 'Preço do Vendedor (Estratégia 3)' };
    }
    
    return { price: '', estrategiaUsada: 'Nenhuma estratégia funcionou' };
};

// Atualizar retorno
out._debug_preco = {
    estrategia: precoResult.estrategiaUsada
};
```

### Python (Logging)

```python
# Log detalhado de preço
if dados.get('preco'):
    debug_info = result.get('_debug_preco', {})
    estrategia = debug_info.get('estrategia', 'desconhecida')
    logger.info(f"   💰 Preço: {dados['preco']}")
    logger.info(f"      └─ Estratégia: {estrategia}")
    
    if debug_info.get('tentativas'):
        logger.info(f"        Tentativas: {debug_info['tentativas']}")
```

## 📈 Benefícios dos Logs Melhorados

### 1. **Debug Fácil**
- Saber exatamente qual seletor/estratégia funcionou
- Entender por que um preço foi extraído ou não

### 2. **Rastreabilidade**
- Seguir caminho completo: tentativa 1 → 2 → 3 → fallback
- Validar que dados críticos foram encontrados

### 3. **Confiança**
- JSON-LD = dados estruturados ✅ mais confiável
- CSS = dados visuais ⚠️ pode falhar se layout mudar
- TreeWalker = busca ordenada ✅ determinística

### 4. **Monitoramento**
- Detectar quando fallback é usado frequentemente (sinal de problema)
- Identificar plataformas com extração instável

## 📝 Exemplo de Saída Completa no Console

```
INFO 2026-03-25 16:00:00,123 scraper 21644 16380 ✅ Shopee: Mochila Grande De Lona 50 Litros
INFO 2026-03-25 16:00:00,124 scraper 21644 16380    💰 Preço: R$ 39,99
INFO 2026-03-25 16:00:00,124 scraper 21644 16380       └─ Estratégia: TreeWalker (Faixa) | Tentativas: 3
INFO 2026-03-25 16:00:00,124 scraper 21644 16380    📌 Preço Original: R$ 43,99
INFO 2026-03-25 16:00:00,124 scraper 21644 16380       └─ Extraído da faixa (desconto detectado)
INFO 2026-03-25 16:00:00,124 scraper 21644 16380    🖼️  Imagem: ✅ OK

INFO 2026-03-25 16:00:15,456 scraper 21644 16380 ✅ Mercado Livre: Notebook Gamer
INFO 2026-03-25 16:00:15,457 scraper 21644 16380    💰 Preço: R$ 2.499,90
INFO 2026-03-25 16:00:15,457 scraper 21644 16380       └─ Estratégia: Melhor Preço (Estratégia 1)
INFO 2026-03-25 16:00:15,457 scraper 21644 16380    📌 Preço Original: (sem desconto)
INFO 2026-03-25 16:00:15,457 scraper 21644 16380    🏷️  Categoria: Informática
```

## ✅ Testes Validados

**7/7 testes de logging passaram:**
- ✅ Shopee com faixa de preço
- ✅ Shopee com preço simples
- ✅ Shopee com fallback RegEx
- ✅ ML com Estratégia 1 (Melhor Preço)
- ✅ ML com Estratégia 2 (Ofertas)
- ✅ Amazon com JSON-LD
- ✅ Amazon com CSS Fallback

## 🚀 Impacto em Produção

Os novos logs ajudam a:
1. **Depurar problemas** rapidamente ao identificar qual estratégia falhou
2. **Monitorar saúde** de scrapers (frequência de fallbacks)
3. **Validar dados** antes de salvar (confiança na origem)
4. **Alertar** quando muitas tentativas são necessárias
