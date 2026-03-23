from django.core.management.base import BaseCommand
from produtos.models import DocumentoLegal


class Command(BaseCommand):
    help = 'Popula os documentos legais (Privacidade, Termos, Afiliados) com conteúdo padrão'

    def handle(self, *args, **options):
        documentos = {
            'privacidade': '''
<h2>Política de Privacidade e Termos</h2>
<p>Esta política descreve como coletamos e usamos dados ao visitar nosso site.</p>

<h3>1. Anúncios e Cookies</h3>
<p>Utilizamos o <b>Google AdSense</b> para exibir anúncios. O Google utiliza cookies para veicular anúncios com base em suas visitas anteriores. Você pode desativar a publicidade personalizada visitando as <a href="https://adssettings.google.com" target="_blank">Configurações de anúncios do Google</a>.</p>

<h3>2. Coleta de Dados</h3>
<p>Não armazenamos dados sensíveis de usuários. Nosso ambiente hospedado no <b>Google Cloud Platform (GCP)</b> segue padrões rigorosos de segurança de infraestrutura.</p>

<h3>3. Cookies e Rastreamento</h3>
<p>Usamos cookies para:</p>
<ul>
    <li>Melhorar sua experiência de navegação</li>
    <li>Análise de tráfego via Google Analytics</li>
    <li>Entrega de anúncios direcionados via Google AdSense</li>
</ul>

<p><i>Última atualização: {% now "F" %} de {% now "Y" %}.</i></p>
            ''',
            'termos': '''
<h2>Termos de Uso</h2>
<p>Bem-vindo ao nosso site. Ao usar este site, você concorda com os seguintes termos e condições.</p>

<h3>1. Propriedade Intelectual</h3>
<p>Todo o conteúdo neste site, incluindo textos, imagens e links, é protegido por direitos autorais e outras leis de propriedade intelectual.</p>

<h3>2. Links de Afiliados</h3>
<p>Este é um <b>agregador de ofertas</b>. Quando você clica em um link de produto e faz uma compra, podemos receber uma comissão.
Você <b>não paga nada a mais</b> por isso.</p>

<h3>3. Limitação de Responsabilidade</h3>
<p>Este site fornece informações sobre produtos e ofertas. Não somos responsáveis por:</p>
<ul>
    <li>Qualidade ou disponibilidade dos produtos</li>
    <li>Preços ou promoções (sujeitos a mudanças)</li>
    <li>Danos diretos ou indiretos pelo uso do site</li>
</ul>

<h3>4. Modificações dos Termos</h3>
<p>Reservamos o direito de modificar estes termos a qualquer momento. Mudanças significativas serão anunciadas nesta página.</p>

<p><i>Última atualização: {% now "F" %} de {% now "Y" %}.</i></p>
            ''',
            'afiliados': '''
<h2>Divulgação de Afiliados</h2>
<p>Somos afiliados dos principais e-commerces do Brasil e do mundo. Aqui você encontra uma lista completa de nossas parcerias.</p>

<h3>1. O que significa ser um site de afiliados?</h3>
<p>Isso significa que podemos receber uma pequena comissão quando você:</p>
<ul>
    <li>Clica em um de nossos links</li>
    <li>Realiza uma compra dentro de um prazo específico</li>
</ul>

<h3>2. Você paga mais?</h3>
<p><b>NÃO!</b> O preço final é <b>exatamente o mesmo</b>. A comissão sai da margem do lojista, não do seu bolso.</p>

<h3>3. Nossas Parcerias</h3>
<p>Participamos de programas de afiliados de:</p>
<ul>
    <li><b>Mercado Livre</b> - Maior marketplace da América Latina</li>
    <li><b>Amazon</b> - Eletrônicos, livros, eletrodomésticos</li>
    <li><b>Shopee</b> - Moda, tecnologia, casa e jardim</li>
    <li><b>Hotmart</b> - Cursos e produtos digitais</li>
    <li>Outras plataformas de e-commerce parceiras</li>
</ul>

<h3>4. Transparência</h3>
<p>Acreditamos em <b>transparência total</b>. Todos os links neste site são links de afiliados claramente identificados.</p>

<p><i>Última atualização: {% now "F" %} de {% now "Y" %}.</i></p>
            ''',
        }

        for tipo, texto_html in documentos.items():
            obj, criado = DocumentoLegal.objects.update_or_create(
                tipo=tipo,
                defaults={'texto_html': texto_html}
            )
            status = '✓ Criado' if criado else '✓ Atualizado'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{status}: {obj.get_tipo_display()}'
                )
            )

        self.stdout.write(
            self.style.SUCCESS('\n✅ Documentos legais populados com sucesso!')
        )
