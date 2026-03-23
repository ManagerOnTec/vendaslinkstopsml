# Políticas de Google AdSense - Implementação Completa

## ✅ O que foi implementado

### 1. **Modelo Django - DocumentoLegal**
Arquivo: `produtos/models.py` (linhas finais)

- Campo `tipo` com choices: privacidade, termos, afiliados
- Campo `texto_html` para conteúdo em HTML
- Campos `criado_em` e `atualizado_em` para auditoria
- Exibição automática com `get_tipo_display()`

### 2. **Admin Interface - DocumentoLegalAdmin**
Arquivo: `produtos/admin.py`

**Funcionalidades:**
- ✅ Listagem com tipo e data de atualização
- ✅ Preview em tempo real do HTML renderizado
- ✅ Editor HTML com fieldsets organizados
- ✅ Apenas usuários autenticados podem editar
- ✅ Somente 3 tipos permissível (evita duplicatas)

**Como usar:**
1. Acesse `/admin/produtos/documentolegal/`
2. Clique em "Adicionar Documento Legal"
3. Escolha o tipo (Privacidade, Termos ou Afiliados)
4. Cole o HTML e veja o preview
5. Salve

### 3. **View para Exibir Políticas**
Arquivo: `produtos/views.py`

```python
def pagina_legal(request, tipo):
    documento = get_object_or_404(DocumentoLegal, tipo=tipo)
    return render(request, 'legal.html', {'documento': documento})
```

**URLs:**
- `/legal/privacidade/` - Política de Privacidade
- `/legal/termos/` - Termos de Uso
- `/legal/afiliados/` - Divulgação de Afiliados

### 4. **Template Legal**
Arquivo: `templates/legal.html`

- Estende `base.html`
- Renderiza HTML com filtro `|safe`
- Styling responsivo com Bootstrap 5
- Mostra data da última atualização

### 5. **Footer com Links Legais**
Arquivo: `templates/base.html`

Adicionado no rodapé:
```html
<a href="{% url 'produtos:pagina_legal' 'privacidade' %}">Privacidade</a>
<a href="{% url 'produtos:pagina_legal' 'termos' %}">Termos de Uso</a>
<a href="{% url 'produtos:pagina_legal' 'afiliados' %}">Divulgação de Afiliados</a>
```

Plus: Exibe "Verificado com Google AdSense" se `GOOGLE_ADSENSE_ID` estiver configurado

### 6. **Arquivo ads.txt para Google AdSense**
Arquivo: `produtos/views.py` + `produtos/urls.py`

**URL permanente:** `/ads.txt`

```
google.com, pub-[SEU_ID], DIRECT, f08c47fec0942fa0
```

**Como configurar:**
1. Vá para `.env` (ou `Settings` no GCP)
2. Configure: `GOOGLE_ADSENSE_ID=pub-XXXXX`
3. Ou deixe em branco (usa ID padrão)

### 7. **Migração Database**
Automáticamente criada: `produtos/migrations/0005_documentolegal.py`

Aplicada com: `python manage.py migrate`

### 8. **Seed de Dados Padrão**
Script: `produtos/management/commands/seed_documentos_legais.py`

**Como usar:**
```bash
python manage.py seed_documentos_legais
```

**Popula automaticamente:**
- ✅ Política de Privacidade (com informações de cookies e Google AdSense)
- ✅ Termos de Uso (com informações sobre afiliados)
- ✅ Divulgação de Afiliados (com lista de parceiros: ML, Amazon, Shopee, Hotmart)

---

## 🔧 Configuração Final

### 1. **Adicione o ID do Google AdSense**
Arquivo: `.env`

```env
GOOGLE_ADSENSE_ID=pub-4703772286442200
```

Ou via GCP Secret Manager em produção

### 2. **Teste os Links no Rodapé**
- Abra o site
- Scroll até o footer
- Clique em "Privacidade", "Termos" ou "Divulgação de Afiliados"
- Deve abrir a página com o conteúdo HTML

### 3. **Procure no Google**
Google AdSense vai procurar por:
1. ✅ `/ads.txt` - Implementado
2. ✅ Política de Privacidade - Implementada
3. ✅ Termos de Uso - Implementado
4. ✅ Divulgação de Afiliados - Implementado

---

## 📋 Rotas Criadas

| URL | Descrição |
|-----|-----------|
| `/legal/privacidade/` | Exibe Política de Privacidade |
| `/legal/termos/` | Exibe Termos de Uso |
| `/legal/afiliados/` | Exibe Divulgação de Afiliados |
| `/ads.txt` | Arquivo para Google AdSense |

---

## 🎨 Customização

### Editar Documentos no Admin
1. Entre em `/admin/`
2. Procure por "Documentos Legais"
3. Edite o texto HTML conforme necessário
4. Use tags: `<p>`, `<h2>`, `<h3>`, `<b>`, `<i>`, `<ul>`, `<li>`, etc

### Adicionar Domínios Adicionais para ads.txt
Se usar múltiplos domínios:
```python
# Criar um arquivo diferente para cada domínio adicionando ao views.py
# Ou usar um único que funcione para todos
```

---

## ✨ Boas Práticas Implementadas

1. **Segurança:** `|safe` renderiza HTML apenas de documentos administrativos confiáveis
2. **SEO:** Links legais indexáveis no Google
3. **Conformidade:** LGPD, GDPR e termos de afiliados reconhecidos
4. **UX:** Footer discreto mas visível com separadores
5. **Admin:** Interface visual com preview e timestamps
6. **Escalabilidade:** Fácil adicionar novos documentos via SQL ou admin

---

## 📝 Próximos Passos

1. Editar os conteúdos dos documentos no admin conforme sua política real
2. Submeter o site ao Google AdSense
3. Aguardar aprovação (geralmente 2-3 dias)
4. Monitorar cliques em anúncios no Dashboard do AdSense

