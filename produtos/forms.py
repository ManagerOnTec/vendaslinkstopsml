from django import forms
from django.core.exceptions import ValidationError
import re
from html.parser import HTMLParser


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


class AmazonHTMLParser(HTMLParser):
    """Parser para extrair dados de HTML Amazon"""
    def __init__(self):
        super().__init__()
        self.titulo = None
        self.link = None
        self.imagem = None
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'b':
            self.current_tag = 'b'
        elif tag == 'a':
            for attr, value in attrs:
                if attr == 'href' and value:
                    self.link = value
        elif tag == 'img':
            for attr, value in attrs:
                if attr == 'src' and value:
                    self.imagem = value
    
    def handle_data(self, data):
        if self.current_tag == 'b':
            data = data.strip()
            if data:
                self.titulo = data
    
    def handle_endtag(self, tag):
        if tag == 'b':
            self.current_tag = None


class ImportarAmazonHTMLForm(forms.Form):
    """Formulário para importar múltiplos produtos Amazon via HTML (.txt ou .html com tags HTML)"""
    
    arquivo = forms.FileField(
        label='Arquivo .txt ou .html (com conteúdo HTML)',
        help_text='Arquivo contendo tags HTML: <b>Título</b>, <a href="link">...</a>, <img src="imagem" />',
        widget=forms.FileInput(attrs={
            'accept': '.txt,.html',
            'class': 'form-control'
        })
    )
    
    plataforma = forms.ModelChoiceField(
        queryset=None,  # Será definido em __init__
        label='Plataforma',
        required=False,
        empty_label='-- Detectar automaticamente --',
        help_text='Define a plataforma dos produtos importados'
    )
    
    processar_imediatamente = forms.BooleanField(
        label='Processar Imediatamente (Extrair Dados)',
        required=False,
        initial=True,
        help_text='Se marcado, iniciará a extração de dados para cada produto assim que forem criados.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importar aqui para evitar circular imports
        from .models import PlataformaEcommerce
        self.fields['plataforma'].queryset = PlataformaEcommerce.objects.filter(ativo=True).order_by('nome')

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        
        # Validar extensão (case-insensitive)
        nome_arquivo_lower = arquivo.name.lower()
        if not (nome_arquivo_lower.endswith('.txt') or nome_arquivo_lower.endswith('.html')):
            raise ValidationError('Arquivo deve ser .txt ou .html')
        
        # Validar tamanho máximo (5 MB para HTML)
        if arquivo.size > 5 * 1024 * 1024:
            raise ValidationError('Arquivo não pode exceder 5 MB')
        
        return arquivo
    
    def processar_arquivo(self):
        """Extrai título, link e imagem do HTML"""
        arquivo = self.cleaned_data['arquivo']
        
        # Ler conteúdo
        conteudo = arquivo.read().decode('utf-8')
        
        # Dividir em blocos (separados por <br><br> ou múltiplos <br>)
        blocos = re.split(r'<br\s*/?>\s*<br\s*/?>', conteudo)
        
        produtos = []
        for bloco in blocos:
            bloco = bloco.strip()
            if not bloco:
                continue
            
            parser = AmazonHTMLParser()
            try:
                parser.feed(bloco)
            except:
                continue
            
            # Validar se tem pelo menos link
            if parser.link:
                # Se não tem titulo, tentar extrair do bloco
                titulo = parser.titulo
                if not titulo:
                    # Fallback: procurar qualquer texto entre tags
                    match = re.search(r'<b>(.*?)</b>', bloco, re.DOTALL)
                    if match:
                        titulo = match.group(1).strip()
                
                produto = {
                    'titulo': titulo or 'Sem Título',
                    'link': parser.link,
                    'imagem': parser.imagem
                }
                produtos.append(produto)
        
        if not produtos:
            raise ValidationError('Nenhum produto válido encontrado. Certifique-se que o arquivo contém tags <a href="link"> e <b>título</b>')
        
        return produtos
