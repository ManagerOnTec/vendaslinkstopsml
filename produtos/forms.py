from django import forms
from django.core.exceptions import ValidationError


class ImportarProdutosForm(forms.Form):
    """Formulário para importar múltiplos produtos via upload de arquivo .txt"""
    
    arquivo = forms.FileField(
        label='Arquivo .txt com Links',
        help_text='Cada linha deve conter um link (Mercado Livre, Amazon, Shopee, etc). Linhas vazias são ignoradas.',
        widget=forms.FileInput(attrs={
            'accept': '.txt',
            'class': 'form-control'
        })
    )
    
    processar_imediatamente = forms.BooleanField(
        label='Processar Imediatamente (Extrair Dados)',
        required=False,
        initial=True,
        help_text='Se marcado, iniciará a extração de dados para cada produto assim que forem criados.'
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        
        # Validar extensão
        if not arquivo.name.endswith('.txt'):
            raise ValidationError('Arquivo deve ser um .txt')
        
        # Validar tamanho máximo (1 MB)
        if arquivo.size > 1024 * 1024:
            raise ValidationError('Arquivo não pode exceder 1 MB')
        
        return arquivo
    
    def processar_arquivo(self):
        """Extrai e valida os links do arquivo"""
        arquivo = self.cleaned_data['arquivo']
        
        # Ler conteúdo do arquivo
        conteudo = arquivo.read().decode('utf-8')
        linhas = conteudo.split('\n')
        
        # Extrair e limpar links
        links = []
        for linha in linhas:
            link = linha.strip()
            # Ignorar linhas vazias e comentários
            if link and not link.startswith('#'):
                links.append(link)
        
        if not links:
            raise ValidationError('Nenhum link válido encontrado no arquivo.')
        
        return links
