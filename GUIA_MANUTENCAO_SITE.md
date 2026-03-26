# 🔧 SISTEMA DE MANUTENÇÃO DO SITE - GUIA COMPLETO

## ✅ O QUE FOI IMPLEMENTADO

### 1. **Modelo Django** (`SiteMaintenanceConfig`)
- Singleton: apenas 1 registro no banco
- Campos editáveis no admin:
  - ✓ Em Manutenção (checkbox)
  - ✓ Título customizável
  - ✓ Mensagem customizável (suporta HTML)
  - ✓ Tempo estimado (em minutos)
  - ✓ Email de contato
  - ✓ Data de início automática

### 2. **Admin Django**
- Interface dedicada em `/admin/produtos/sitemaintenanceconfig/`
- Design user-friendly com seções organizadas
- Mensagens de feedback ao ativar/desativar
- Redireciona automaticamente para edit (no list view)

### 3. **Middleware** (`produtos/middleware.py`)
- Intercepta requisições quando `em_manutencao=True`
- Retorna código HTTP **503 (Service Unavailable)**
- Permite acesso a:
  - `/admin/` (gerenciar config)
  - `/api/` (endpoints)
  - `/static/` (CSS, JS)
  - `/media/` (imagens)

### 4. **Template de Manutenção** (`templates/maintenance.html`)
- Design responsivo e moderno
- Animações suaves
- Exibe:
  - Ícone animado (🔧)
  - Título customizável
  - Mensagem com suporte a HTML
  - Tempo estimado
  - Email de contato (opcional)
  - Footer inspirador

### 5. **Banco de Dados**
- Migration criada: `0014_create_site_maintenance_config.py`
- Aplicada com sucesso ✓

---

## 🚀 COMO USAR

### **Ativar Modo de Manutenção**

1. Acesse: **http://seusite.com/admin/** (de qualquer máquina)
2. Vá em: **Produtos > Configuração de Manutenção do Site**
3. Preencha:
   - ☑ **Em Manutenção** → marque
   - **Título** → ex: "Sistema em Atualização"
   - **Mensagem** → ex: "Realizamos uma atualização programada..."
   - **Tempo estimado** → ex: 30 minutos
   - **Email de contato** (opcional)
4. Clique em **Salvar**
5. **Pronto!** Visitantes verão mensagem ao acessar o site

### **Desativar Modo de Manutenção**

1. Vá em: **Produtos > Configuração de Manutenção do Site**
2. Desmarque **Em Manutenção**
3. Clique em **Salvar**
4. **Site retorna ao normal** automaticamente

---

## 📝 EXEMPLOS DE MENSAGENS

### Exemplo 1: Manutenção Rápida
```
Título: "Manutenção em Progresso"
Mensagem: "Estamos realizando uma atualização rápida de segurança. Retorne em breve!"
Tempo: 15 minutos
```

### Exemplo 2: Atualização Grande
```
Título: "Melhorias Importantes"
Mensagem: "Estamos implementando novas funcionalidades e melhorias de performance.
Desculpe o incômodo! Voltaremos em breve com um site ainda melhor."
Tempo: 60 minutos
```

### Exemplo 3: Com HTML
```
Título: "Sistema em Manutenção"
Mensagem: "<p><strong>Estamos melhorando sua experiência!</strong></p>
<p>Realizamos uma atualização programada do sistema.</p>
<ul>
  <li>✓ Melhor performance</li>
  <li>✓ Segurança aprimorada</li>
  <li>✓ Novas funcionalidades</li>
</ul>
<p>Obrigado pela paciência!</p>"
Tempo: 45 minutos
```

---

## 🔒 QUEM PODE ACESSAR EM MANUTENÇÃO?

**Permitido acesso:**
- ✓ Admin (`/admin/`)
- ✓ APIs (`/api/*`)
- ✓ Assets (`/static/`, `/media/`)
- ✓ Arquivos especiais (`favicon.ico`, `robots.txt`)

**Bloqueado:**
- ✗ Index (`/`)
- ✗ Categoria (`/categoria/*`)
- ✗ Legal (`/legal/*`)
- ✗ Qualquer outra rota pública

---

## 📱 COMO FICA PARA O CLIENTE

Quando em manutenção, o visitante vê:

```
┌────────────────────────────────────────┐
│                                        │
│              🔧                        │
│                                        │
│  Sistema em Atualização Programada    │
│                                        │
│  Estamos realizando uma atualização    │
│  programada. Retorne em breve!         │
│                                        │
│  ⏱️  Tempo Estimado de Retorno         │
│      30 min                            │
│                                        │
│  💬 Email de contato (se configurado)  │
│                                        │
│  ✨ Voltaremos em breve com novidades  │
│     incríveis!                         │
│                                        │
└────────────────────────────────────────┘
```

---

## 🔧 DETALHES TÉCNICOS

### Arquivos criados/modificados:

```
✓ produtos/models.py           → Adicionado SiteMaintenanceConfig
✓ produtos/admin.py            → Adicionado SiteMaintenanceConfigAdmin
✓ produtos/middleware.py       → Novo! Middleware de manutenção
✓ templates/maintenance.html   → Novo! Template de manutenção
✓ vendaslinkstopsml/settings.py → Adicionado middleware à MIDDLEWARE
✓ produtos/migrations/0014_*   → Migration automática criada
```

### Classe SiteMaintenanceConfig:

```python
class SiteMaintenanceConfig(models.Model):
    em_manutencao = BooleanField()                 # Ativa/desativa
    titulo = CharField(max_length=200)             # Título exibido
    mensagem = TextField()                         # Mensagem HTML
    tempo_estimado_minutos = IntegerField()        # Tempo em minutos
    mostrar_tempo_estimado = BooleanField()        # Exibir tempo?
    email_contato = EmailField(blank=True)         # Email opcional
    data_inicio = DateTimeField(null=True)         # Registra quando iniciou
    criado_em = DateTimeField(auto_now_add=True)
    atualizado_em = DateTimeField(auto_now=True)
```

---

## ❓ PERGUNTAS FREQUENTES

### P: Como editar a mensagem de manutenção sem código?
**R:** Tudo via admin em `/admin/` - sem necessidade de código ou redeploy!

### P: A mensagem suporta HTML?
**R:** Sim! Use HTML básico: `<p>`, `<h2>`, `<h3>`, `<b>`, `<i>`, `<ul>`, `<li>`, `<br>`, etc.

### P: O admin fica acessível em manutenção?
**R:** Sim! `/admin/` é sempre acessível para você ativar/desativar a manutenção.

### P: APIs param também?
**R:** Não! `/api/*` continua funcionando (útil para apps mobile, webhooks, etc).

### P: Quanto tempo leva para entrar em efeito?
**R:** Imediato! Em menos de 1 segundo a mudança é aplicada.

### P: Se eu clicar em voltar também ativa a manutenção?
**R:** Sim! Todos os visitantes verão a página, independente de como acessarem.

---

## 🎯 FLUXO DE USO

```
1. Preparar para manutenção
   └─> Login no Admin
       └─> Produtos > Config Manutenção
           └─> Preencher Título, Mensagem, Tempo
               └─> Marcar ☑ Em Manutenção
                   └─> Salvar

2. Site em Manutenção
   └─> Visitantes veem página amigável
   └─> Admin ainda funciona
   └─> APIs continuam
   └─> Você pode editar a mensagem em tempo real

3. Retornar ao Normal
   └─> Desmarcar ☑ Em Manutenção
       └─> Salvar
           └─> Site volta ao normal automaticamente
```

---

## 🚨 IMPORTANTE

- **Sempre teste** em staging antes de usar em produção
- **Não delete** o registro de config (está protegido)
- **Customize a mensagem** conforme sua necessidade
- **Deixe email** se quiser que clientes entrem em contato
- **HTTP 503** é enviado (bom para buscadores entenderem que é manutenção)

---

## 📊 ESTRUTURA DO BANCO

```sql
-- Tabela criada automaticamente
CREATE TABLE produtos_sitemaintenanceconfig (
    id INTEGER PRIMARY KEY,
    em_manutencao BOOLEAN DEFAULT FALSE,
    titulo VARCHAR(200),
    mensagem TEXT,
    tempo_estimado_minutos INTEGER DEFAULT 30,
    mostrar_tempo_estimado BOOLEAN DEFAULT TRUE,
    email_contato VARCHAR(254) BLANK,
    data_inicio DATETIME NULL,
    criado_em DATETIME AUTO_NOW_ADD,
    atualizado_em DATETIME AUTO_NOW
);
```

Apenas 1 registro será criado automaticamente ao acessar o admin!

---

## 🎨 CUSTOMIZAÇÕES FUTURAS

Se quiser expandir:

- [ ] Adicionar página de countdown (regressiva)
- [ ] Adicionar notificação via email quando retornar
- [ ] Agendar manutenção automática (ativa em horário X)
- [ ] Exibir banner em vez de página completa
- [ ] Permitir bypass com senha (acesso VIP)
- [ ] Log de histórico de manutenções

Tudo editável via admin - **sem necessidade de redeploy!** 🚀

---

**Status**: ✅ IMPLEMENTADO E TESTADO
**Pronto para uso em PRODUÇÃO**
