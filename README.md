# Vendas Links Tops ML

Site de listagem de produtos com links afiliados do Mercado Livre, desenvolvido em **Python + Django**, com frontend responsivo em **Bootstrap 5 via CDN** e gestão completa via **Django Admin**.

---

## Funcionalidades

### Duas Páginas Index

O site possui **duas páginas principais** com abordagens diferentes:

| Página | Descrição | Acesso |
|---|---|---|
| **Curadoria** | Produtos cadastrados manualmente com todos os dados preenchidos pelo admin | `/curadoria/` |
| **Ofertas ML** | Produtos automáticos — basta colar o link do ML e os dados são extraídos automaticamente | `/` (raiz) |

### Funcionalidades Gerais

O sistema oferece listagem automática de produtos ativos com ordenação por destaque e data, grid responsivo com 1 coluna no mobile, 2 colunas no tablet e 4 colunas no desktop, cards clicáveis com imagem, título, preço original riscado, preço atual e botão "Ver no Mercado Livre", filtro por categorias via barra de navegação, busca por título de produto, paginação configurável, anúncios AdSense gerenciáveis via admin (topo, entre produtos, rodapé), SEO básico com title dinâmico, meta description e Open Graph, lazy loading de imagens, botão scroll to top, espaço reservado para logo (navbar e footer) e variáveis de ambiente para dados sensíveis (pronto para GCP Cloud Run).

### Extração Automática de Dados (Ofertas ML)

A funcionalidade de **Produtos Automáticos** permite que o administrador cadastre apenas o **link afiliado** de um produto do Mercado Livre. O sistema utiliza **Playwright** (browser headless) para navegar até a página do produto e extrair automaticamente o título, imagem em alta resolução, preço atual, preço original (se houver desconto), descrição e URL final do produto. A extração pode ser executada individualmente ao salvar o produto ou em lote via ação do admin "Extrair/Atualizar dados do ML".

---

## Estrutura do Projeto

```
vendaslinkstopsml/
├── manage.py
├── requirements.txt
├── Dockerfile                  # Deploy GCP Cloud Run
├── Procfile                    # Deploy alternativo
├── .env                        # Variáveis de ambiente (local)
├── .env.example                # Referência de variáveis
├── seed_data.py                # Script de dados de demonstração
├── vendaslinkstopsml/
│   ├── settings.py             # Configurações com django-environ
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── produtos/
│   ├── models.py               # Produto, Categoria, Anuncio, ProdutoAutomatico
│   ├── admin.py                # Admin personalizado com filtros e ações
│   ├── views.py                # CBVs para ambas as páginas
│   ├── urls.py
│   ├── scraper.py              # Módulo de scraping do Mercado Livre
│   ├── context_processors.py   # Variáveis globais nos templates
│   └── templatetags/
│       └── produto_tags.py     # Filtros customizados
├── templates/
│   ├── base.html               # Template base com Bootstrap 5
│   └── produtos/
│       ├── lista.html          # Listagem manual (Curadoria)
│       └── lista_automatica.html  # Listagem automática (Ofertas ML)
├── static/
│   ├── css/style.css           # CSS customizado
│   ├── js/main.js              # JavaScript (scroll, lazy load, analytics)
│   └── images/
│       └── no-image.png        # Placeholder para produtos sem imagem
└── media/                      # Uploads de imagens (ImageField)
```

---

## Instalação Local

### 1. Clonar e configurar ambiente

```bash
cd vendaslinkstopsml
C:\path\to\python.exe -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar variáveis de ambiente

Copie o ficheiro de exemplo e edite:

```bash
cp .env.example .env
```

Edite o `.env` com os seus valores:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
SITE_NAME=Vendas Links Tops ML
SITE_DESCRIPTION=As melhores ofertas do Mercado Livre
GOOGLE_ADSENSE_ID=
```

### 3. Executar migrações e criar superusuário

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. (Opcional) Carregar dados de demonstração

```bash
python manage.py shell < seed_data.py
```

### 5. Coletar static files e iniciar servidor

```bash
python manage.py collectstatic --noinput
python manage.py runserver
```

Acesse: http://localhost:8000 (Ofertas ML) e http://localhost:8000/curadoria/ (Curadoria)

Admin: http://localhost:8000/admin/

---

## Deploy no GCP Cloud Run

### 1. Configurar variáveis de ambiente no Cloud Run

No console do GCP Cloud Run, defina as seguintes variáveis:

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave secreta do Django |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Domínio do Cloud Run |
| `DATABASE_URL` | URL do banco de dados (Cloud SQL) |
| `SITE_NAME` | Nome do site |
| `SITE_DESCRIPTION` | Descrição do site |
| `GOOGLE_ADSENSE_ID` | ID do Google AdSense (ex: ca-pub-XXXXX) |

### 2. Build e deploy

```bash
gcloud builds submit --tag gcr.io/SEU_PROJETO/vendaslinkstopsml
gcloud run deploy vendaslinkstopsml \
  --image gcr.io/SEU_PROJETO/vendaslinkstopsml \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**Nota importante para GCP Cloud Run**: O Playwright requer Chromium instalado no container. O Dockerfile já inclui a instalação do Chromium e suas dependências. Certifique-se de que o container tem memória suficiente (mínimo 512MB recomendado) para executar o browser headless.

---

## Gestão via Admin

### Produtos Manuais (Curadoria)

| Campo | Descrição |
|---|---|
| **Titulo** | Nome do produto |
| **Imagem** | Upload local OU URL externa (upload tem prioridade) |
| **Link Afiliado** | URL do Mercado Livre com seu código de afiliado |
| **Preço / Preço Original** | Preço atual e preço antes do desconto |
| **Categoria** | Organização por categorias |
| **Destaque** | Produtos em destaque aparecem primeiro |
| **Ativo** | Controla visibilidade no site |
| **Ordem** | Ordenação manual (menor = primeiro) |

### Produtos Automáticos (Ofertas ML)

| Campo | Descrição |
|---|---|
| **Link Afiliado** | Cole o link do produto do ML (único campo obrigatório) |
| **Categoria** | Opcional — organização por categorias |
| **Destaque / Ativo / Ordem** | Configuração manual |
| **Dados extraídos** | Título, imagem, preço, preço original, descrição (preenchidos automaticamente) |
| **Status da Extração** | Pendente, Processando, Sucesso ou Erro |

**Como usar**: Acesse Admin > Produtos Automáticos > Adicionar. Cole o link do produto do Mercado Livre e clique em Salvar. Os dados serão extraídos automaticamente. Para atualizar dados de vários produtos, selecione-os na lista e use a ação "Extrair/Atualizar dados do ML".

### Anúncios (AdSense)

| Campo | Descrição |
|---|---|
| **Nome** | Identificação interna |
| **Código HTML** | Cole o script do Google AdSense |
| **Posição** | Topo, Entre Produtos, Rodapé ou Lateral |
| **Ativo** | Controla exibição |

### Categorias

| Campo | Descrição |
|---|---|
| **Nome** | Nome da categoria |
| **Slug** | URL amigável (gerado automaticamente) |
| **Ativo / Ordem** | Controle de visibilidade e ordenação |

---

## Logo

✅ **Logo já está criada e configurada!**

A logo profissional foi gerada automaticamente em:
```
static/images/logo.png
```

**Características:**
- Sacola de compras com checkmark (confiança)
- Design minimalista e profissional
- PNG com transparência
- 200x200px (escalável)
- Cores: Azul (#1976D2) + Branco

A logo já está integrada em:
- **Navbar** (topo do site)
- **Footer** (rodapé)

**Para personalizar:**
Se quiser trocar a logo, substitua o arquivo em `static/images/logo.png` pela sua própria imagem PNG.

Para editar manualmente o código, procure `{% static 'images/logo.png' %}` em `templates/base.html`.

---

## Tecnologias

| Componente | Tecnologia |
|---|---|
| **Backend** | Python 3.11 + Django 5.x |
| **Frontend** | HTML5 + Bootstrap 5.3 (CDN) + CSS3 + JavaScript |
| **Scraping** | Playwright (Chromium headless) |
| **Servidor** | Gunicorn + WhiteNoise |
| **Banco de Dados** | SQLite (dev) / PostgreSQL (prod) |
| **Deploy** | Docker + GCP Cloud Run |
| **Gestão de Ambiente** | django-environ |
