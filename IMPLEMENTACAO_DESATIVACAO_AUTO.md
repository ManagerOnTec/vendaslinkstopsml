# 📋 Implementação: Desativação Automática por Falhas

## 🎯 Objetivo
Quando um produto automático falhar na atualização N vezes consecutivas, desativá-lo automaticamente para não desperdiçar recursos em links mortos.

---

## 1️⃣ PASSO 1: Adicionar Campo ao Modelo

**Arquivo**: `produtos/models.py`

Localize a classe `ProdutoAutomatico` e adicione este campo:

```python
class ProdutoAutomatico(models.Model):
    """Produto com dados extraídos automaticamente do Mercado Livre."""
    # ... campos existentes ...
    
    ultima_extracao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Extração"
    )
    
    # ⬇️ ADICIONE ESTE CAMPO:
    falhas_consecutivas = models.IntegerField(
        default=0,
        verbose_name="Falhas Consecutivas",
        help_text="Número de tentativas de atualização que falharam. Ao atingir limite, produto é desativado automaticamente."
    )
    motivo_desativacao = models.TextField(
        blank=True,
        verbose_name="Motivo da Desativação",
        help_text="Registra o motivo automático de desativação (ex: 5 falhas consecutivas)"
    )

    class Meta:
        verbose_name = "Produto Automático"
        verbose_name_plural = "Produtos Automáticos"
        ordering = ['-destaque', 'ordem', '-criado_em']
```

---

## 2️⃣ PASSO 2: Criar Migração

```bash
# Gerar migração
python manage.py makemigrations produtos

# Aplicar migração
python manage.py migrate
```

---

## 3️⃣ PASSO 3: Atualizar Admin

**Arquivo**: `produtos/admin.py`

Localize a classe `ProdutoAutomaticoAdmin` e atualize o `list_display` e `list_filter`:

```python
class ProdutoAutomaticoAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 
        'status_extracao', 
        'ativo', 
        'falhas_consecutivas',  # ⬅️ ADICIONE
        'preco',
        'atualizado_em'
    ]
    list_filter = [
        'ativo',
        'status_extracao',
        ('falhas_consecutivas', admin.NumericRangeFilter),  # ⬅️ ADICIONE
        'atualizado_em'
    ]
    readonly_fields = [
        'url_final',
        'ultima_extracao',
        'erro_extracao',
        'falhas_consecutivas',  # ⬅️ ADICIONE
        'motivo_desativacao',  # ⬅️ ADICIONE
        'criado_em',
        'atualizado_em',
    ]
    
    fieldsets = (
        ('Entrada do Usuário', {
            'fields': ('link_afiliado',)
        }),
        ('Dados Extraídos', {
            'fields': (
                'titulo', 'imagem_url', 'preco', 'preco_original',
                'descricao', 'url_final', 'categoria'
            )
        }),
        ('Status', {
            'fields': (
                'status_extracao', 'ativo', 'destaque', 'ordem',
                'falhas_consecutivas', 'motivo_desativacao'  # ⬅️ ADICIONE
            )
        }),
        ('Erros', {
            'fields': ('erro_extracao',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('ultima_extracao', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
```

---

## 4️⃣ PASSO 4: Atualizar Management Command

**Arquivo**: `produtos/management/commands/atualizar_produtos_ml.py`

Substitua a função `_executar_atualizacao` por esta versão melhorada:

```python
def _executar_atualizacao(
    self, agendamento=None, ids=None, apenas_ativos=True
):
    """Executa a atualização dos produtos com desativação por falhas."""
    inicio = time.time()
    
    # Constantes
    LIMITE_FALHAS = 5  # ⬅️ Desativa após N falhas consecutivas
    
    # Selecionar produtos
    queryset = ProdutoAutomatico.objects.all()
    if ids:
        queryset = queryset.filter(id__in=ids)
    elif apenas_ativos:
        queryset = queryset.filter(ativo=True)

    total = queryset.count()
    if total == 0:
        self.stdout.write(
            self.style.WARNING('Nenhum produto para atualizar.')
        )
        return

    self.stdout.write(f'Atualizando {total} produto(s)...')

    sucesso = 0
    erros = 0
    desativados = 0
    detalhes_list = []

    for produto in queryset:
        try:
            self.stdout.write(
                f'  [{sucesso + erros + 1}/{total}] '
                f'{produto.titulo[:50] or produto.link_afiliado[:50]}...'
            )
            result = processar_produto_automatico(produto)
            
            if result:
                # ✅ SUCESSO - Resetar contagem de falhas
                sucesso += 1
                if produto.falhas_consecutivas > 0:
                    produto.falhas_consecutivas = 0
                    produto.motivo_desativacao = ''
                    produto.save(update_fields=['falhas_consecutivas', 'motivo_desativacao'])
                
                detalhes_list.append(
                    f'✅ OK: {produto.titulo[:60]} -> {produto.preco}'
                )
            else:
                # ❌ ERRO - Incrementar falhas
                erros += 1
                produto.falhas_consecutivas += 1
                
                # Verificar se atingiu limite de falhas
                if produto.falhas_consecutivas >= LIMITE_FALHAS:
                    # 🛑 DESATIVAR AUTOMATICAMENTE
                    produto.ativo = False
                    produto.motivo_desativacao = (
                        f'Desativado automaticamente após {LIMITE_FALHAS} falhas '
                        f'consecutivas de atualização. Última tentativa: {timezone.now()}. '
                        f'Erro: {produto.erro_extracao[:100]}'
                    )
                    produto.save()
                    
                    desativados += 1
                    detalhes_list.append(
                        f'🛑 DESATIVADO: {produto.titulo[:60]} '
                        f'(após {LIMITE_FALHAS} falhas)'
                    )
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ⚠️  Produto desativado após {LIMITE_FALHAS} falhas: '
                            f'{produto.titulo[:50]}'
                        )
                    )
                else:
                    # Salvar incremento de falhas
                    produto.save(update_fields=['falhas_consecutivas', 'motivo_desativacao'])
                    detalhes_list.append(
                        f'❌ ERRO ({produto.falhas_consecutivas}/{LIMITE_FALHAS}): '
                        f'{produto.titulo[:60]} -> {produto.erro_extracao[:50]}'
                    )
        
        except Exception as e:
            erros += 1
            produto.falhas_consecutivas += 1
            
            # Desativar se atingir limite
            if produto.falhas_consecutivas >= LIMITE_FALHAS:
                produto.ativo = False
                produto.motivo_desativacao = (
                    f'Desativado automaticamente após {LIMITE_FALHAS} falhas '
                    f'consecutivas. Exceção: {str(e)[:100]}'
                )
                desativados += 1
            
            produto.save()
            
            detalhes_list.append(
                f'⚠️  EXCEÇÃO: {produto.id} -> {str(e)[:80]}'
            )
            logger.error(
                f'Erro ao atualizar produto {produto.id}: {e}'
            )

    duracao = time.time() - inicio
    
    # Registrar no banco de dados
    log = LogAtualizacao.objects.create(
        agendamento=agendamento,
        executado_em=timezone.now(),
        total=total,
        sucesso=sucesso,
        erros=erros,
        duracao_segundos=duracao,
        detalhes='\n'.join(detalhes_list)
    )

    # Output
    self.stdout.write('\n' + '='*60)
    self.stdout.write(self.style.SUCCESS(f'✅ Atualização concluída!'))
    self.stdout.write(f'   Total: {total} | Sucesso: {sucesso} | Erros: {erros} | Desativados: {desativados}')
    self.stdout.write(f'   Tempo: {duracao:.2f}s')
    
    if desativados > 0:
        self.stdout.write(
            self.style.ERROR(
                f'\n⚠️  {desativados} produto(s) foram DESATIVADOS por múltiplas falhas!'
            )
        )
    
    self.stdout.write('='*60 + '\n')
```

---

## 5️⃣ PASSO 5: (Opcional) Criar Ação de Admin para Resetar Falhas

**Arquivo**: `produtos/admin.py`

Adicione esta ação à classe `ProdutoAutomaticoAdmin`:

```python
def resetar_falhas_consecutivas(self, request, queryset):
    """Ação para resetar manualmente o contador de falhas."""
    atualizado = queryset.update(
        falhas_consecutivas=0,
        motivo_desativacao=''
    )
    self.message_user(
        request,
        f'{atualizado} produto(s) tiveram contador de falhas resetado.',
        messages.SUCCESS
    )

resetar_falhas_consecutivas.short_description = "Resetar contador de falhas"

class ProdutoAutomaticoAdmin(admin.ModelAdmin):
    # ... configurações existentes ...
    actions = ['resetar_falhas_consecutivas']  # ⬅️ ADICIONE
```

---

## 6️⃣ PASSO 6: (Opcional) Filtro no Admin para Ver Produtos Problemáticos

**Arquivo**: `produtos/admin.py`

Adicione um custom filter para filtrar por falhas:

```python
class FalhasFilter(admin.SimpleListFilter):
    """Filtro personalizado para produtos com múltiplas falhas."""
    title = 'Status de Falhas'
    parameter_name = 'falhas_status'

    def lookups(self, request, model_admin):
        return (
            ('sem_falhas', 'Sem falhas (0)'),
            ('poucas_falhas', 'Poucas falhas (1-2)'),
            ('muitas_falhas', 'Muitas falhas (3-4)'),
            ('critico', 'Crítico (5+)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'sem_falhas':
            return queryset.filter(falhas_consecutivas=0)
        elif self.value() == 'poucas_falhas':
            return queryset.filter(falhas_consecutivas__in=[1, 2])
        elif self.value() == 'muitas_falhas':
            return queryset.filter(falhas_consecutivas__in=[3, 4])
        elif self.value() == 'critico':
            return queryset.filter(falhas_consecutivas__gte=5)

class ProdutoAutomaticoAdmin(admin.ModelAdmin):
    # ... configurações existentes ...
    list_filter = [
        'ativo',
        'status_extracao',
        FalhasFilter,  # ⬅️ ADICIONE
        'atualizado_em'
    ]
```

---

## 📊 Comportamento Esperado

### Cenário 1: Link Ativo
```
Tentativa 1: ✅ Sucesso
→ falhas_consecutivas = 0
→ Produto permanece ativo
```

### Cenário 2: Link Morto
```
Tentativa 1: ❌ Erro
→ falhas_consecutivas = 1
→ Produto permanece ativo

Tentativa 2: ❌ Erro
→ falhas_consecutivas = 2
→ Produto permanece ativo

...

Tentativa 5: ❌ Erro
→ falhas_consecutivas = 5
→ 🛑 Produto DESATIVADO
→ motivo_desativacao = "Desativado automaticamente..."
```

### Cenário 3: Link Recuperado
```
Tentativa 1: ❌ Erro
→ falhas_consecutivas = 3

Tentativa 2: ✅ Sucesso
→ falhas_consecutivas = 0 (RESETADO)
→ Produto permanece ativo
```

---

## 🔧 Configurações Personalizáveis

### Alterar Limite de Falhas

No management command, mude:
```python
LIMITE_FALHAS = 5  # ⬅️ Mude para desativar mais/menos rapidamente
```

Sugestões:
- **3 falhas**: Mais agressivo, remove rapidinho
- **5 falhas**: Balanceado (recomendado) ✅
- **10 falhas**: Mais tolerante com conexões instáveis

---

## 🧹 Limpeza de Produtos Desativados (Futura)

Se quiser remover produtos desativados automaticamente:

```bash
# Ver quantos serão deletados
python manage.py shell
>>> from produtos.models import ProdutoAutomatico
>>> ProdutoAutomatico.objects.filter(
...     ativo=False,
...     motivo_desativacao__contains='Desativado automaticamente'
... ).count()

# Deletar
>>> ProdutoAutomatico.objects.filter(
...     ativo=False,
...     motivo_desativacao__contains='Desativado automaticamente'
... ).delete()
```

---

## 📈 Monitoramento no Admin

Agora você pode:

1. **Ver contador de falhas**: Coluna `falhas_consecutivas` no listview
2. **Filtrar problemáticos**: Use o filtro `Status de Falhas`
3. **Resetar manualmente**: Selecione e use ação `Resetar contador de falhas`
4. **Ver motivo**: Campo `motivo_desativacao` mostra por que foi desativado
5. **Reativar**: Simplesmente marque `ativo=True`

---

## ✅ Checklist

- [ ] Adicionar campos ao modelo ProdutoAutomatico
- [ ] Fazer `makemigrations` e `migrate`
- [ ] Atualizar admin.py com novo fieldset e filter
- [ ] Atualizar management command com nova lógica
- [ ] Testar com `--forcar` manualmente
- [ ] Verificar logs de desativação no admin
- [ ] (Opcional) Criar ação de reset de falhas
- [ ] (Opcional) Criar custom filter

---

**Data**: Março 2026  
**Status**: Pronto para implementação
