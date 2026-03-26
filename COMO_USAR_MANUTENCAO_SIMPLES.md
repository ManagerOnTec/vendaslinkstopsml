# 🚀 GUIA RÁPIDO: Sistema de Manutenção Simplificado

## 📌 O QUE MUDOU?

**Antes**: Middleware interceptava TODAS as requisições globalmente  
**Agora**: Lógica simples no template Django (if/else)

**Benefácio**: Site SEMPRE fica de pé, apenas HTML muda

---

## 🎯 COMO USAR (3 PASSOS)

### ✅ Passo 1: Acessar Admin
Vá para: `https://seu-dominio.com/admin/`

### ✅ Passo 2: Abrir Configuração de Manutenção
Clique em: **Produtos → Site Maintenance Config**

Você verá um único registro (Singleton) com a configuração.

### ✅ Passo 3: Ativar/Desativar Manutenção

#### Para ATIVAR manutenção:
```
☑️ Site em Manutenção  ← MARQUE ESTE CHECKBOX
Título: Sistema em Manutenção (ou customize)
Mensagem: Estamos realizando atualizações...
Tempo Estimado: 30 (minutos)

[SALVAR]
```

#### Para DESATIVAR manutenção:
```
☐ Site em Manutenção  ← DESMARQUE ESTE CHECKBOX

[SALVAR]
```

---

## 🎨 O QUE O USUÁRIO VÊ?

### Modo MANUTENÇÃO ATIVADO (checkbox marcado)
```
┌──────────────────────────────────┐
│                                  │
│       🔧 Site em Atualização    │
│                                  │
│   Estamos realizando melhorias   │
│                                  │
│     Retorne mais tarde!          │
│                                  │
│  Obrigado pela paciência.        │
│                                  │
└──────────────────────────────────┘
```

🔴 Produtos: **OCULTOS**  
🔴 Análises: **OCULTAS**  
🔴 Busca: **OCULTA**  

✅ Admin: **ACESSÍVEL** (`/admin/`)  
✅ API: **ACESSÍVEL** (`/api/healthcheck/`, etc)  

---

### Modo MANUTENÇÃO DESATIVADO (checkbox desmarcado)
```
┌──────────────────────────────────┐
│ 📚 Análise e Recomendação       │
│ [Conteúdo editorial]             │
│                                  │
│ 🛍️  Grid de Produtos            │
│ [Todos os produtos exibidos]     │
│                                  │
│ 💬 FAQ, Anúncios, etc.          │
│ [Conteúdo normal]                │
│                                  │
└──────────────────────────────────┘
```

✅ Produtos: **VISÍVEIS**  
✅ Análises: **VISÍVEIS**  
✅ Busca: **FUNCIONAL**  

---

## ⚡ INSTANTÂNEO!

❌ **NÃO** precisa restartar Django  
❌ **NÃO** precisa fazer deploy novo  
✅ **SIM** muda em tempo real (refresh da página)

---

## 🔍 VERIFICAÇÕES

### Como saber que está funcionando?

#### Teste 1: Site OPERACIONAL
```
1. Desmarque "Site em Manutenção"
2. Clique SALVAR
3. Acesse: https://seu-dominio.com/
4. ✅ Deve ver grid de produtos
```

#### Teste 2: Modo MANUTENÇÃO
```
1. Marque "Site em Manutenção"
2. Clique SALVAR  
3. Acesse: https://seu-dominio.com/
4. ✅ Deve ver "Site em Atualização, Retorne Mais Tarde!"
```

#### Teste 3: Admin SEMPRE acessível
```
1. Marque "Site em Manutenção"
2. Clique SALVAR
3. Acesse: https://seu-dominio.com/admin/
4. ✅ DEVE funcionar normalmente
```

---

## 📋 CAMPOS CUSTOMIZÁVEIS

No admin, você pode customizar:

```
✎️ Título
   Padrão: "Sistema em Manutenção"
   Customizar para: "Atualizando Base de Dados"
   
✎️ Mensagem
   Padrão: "Estamos realizando uma atualização"
   Customizar para: "Desculpe! Base de dados em manutenção"
   
✎️ Tempo Estimado (minutos)
   Padrão: 30
   Customizar para: 60 (ou quanto for necessário)
   
✎️ Mostrar Tempo Estimado
   ☑️ Ativar: Mostra "Tempo estimado: X min"
   ☐ Desativar: Não mostra tempo

✎️ Email de Contato
   Opcional: email@seu-dominio.com
   (Para usuários entrarem em contato)
```

---

## 🛑 PROBLEMAS? SOLUÇÃO RÁPIDA

### Problema: Ver mensagem de manutenção quando não deve

**Solução**: 
```
1. Admin → Produtos → Site Maintenance Config
2. Verifique se checkbox "Site em Manutenção" está ☑️ MARCADO
3. Se sim, DESMARQUE ☐ e clique SALVAR
4. Refresh a página
```

### Problema: Não vê mudanças após marcar/desmarcar

**Solução**:
```
1. Verifique se clicou SALVAR após alterar
2. Fazer Ctrl+Shift+R (hard refresh do navegador)
3. Limpar cache (Settings → Clear Cache)
4. Se ainda não funcionar, reinicie: python manage.py runserver
```

---

## 📝 NOTAS TÉCNICAS

### Arquivos Modificados:
- ✅ `vendaslinkstopsml/settings.py` - Middleware removido
- ✅ `produtos/views.py` - Contexto adicionado
- ✅ `templates/produtos/lista.html` - If/else adicionado

### Nenhuma Migração Necessária!
Tabela `produtos_sitemaintenanceconfig` já existe e continua funcional.

### Compatibilidade:
- ✅ Django 5.2.12
- ✅ Python 3.11
- ✅ SQLite (dev) e Cloud SQL (prod)

---

## 🎯 RESUMO

| Ação | Antes | Agora |
|------|-------|-------|
| Ativar manutenção | Modificar middleware no código | ✅ 1 clique no admin |
| Tempo para mudar | Restart do servidor necessário | ✅ Instantâneo |
| Site fica de pé? | Sim | ✅ Sempre |
| Administrador acessa? | Depende do bypass | ✅ Sempre |
| Complexidade | Média (middleware) | ✅ Simples (template if/else) |

---

## 💬 PRECISA DE AJUDA?

Consulte o arquivo: `SIMPLIFICACAO_MANUTENCAO_RESUMO.md`

Para mais detalhes técnicos abra: `GUIA_MANUTENCAO_SITE.md`

