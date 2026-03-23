"""
Management command para atualizar automaticamente os produtos do Mercado Livre.

Uso:
    # Executar verificando agendamentos ativos para o horário atual
    python manage.py atualizar_produtos_ml

    # Forçar execução independente de agendamento
    python manage.py atualizar_produtos_ml --forcar

    # Atualizar apenas produtos específicos (por ID)
    python manage.py atualizar_produtos_ml --ids 1 2 3

Este command é chamado pelo Cloud Scheduler (GCP) ou cron a cada hora.
Ele verifica se há agendamentos ativos para o horário atual e, se houver,
executa a atualização de todos os produtos automáticos.
"""
import time
import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from produtos.models import (
    ProdutoAutomatico, AgendamentoAtualizacao, LogAtualizacao, DiaSemana
)
from produtos.scraper import processar_produto_automatico

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Atualiza dados dos produtos automáticos do Mercado Livre'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forcar',
            action='store_true',
            help='Forçar execução independente de agendamento ativo',
        )
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            help='IDs específicos de produtos para atualizar',
        )

    def handle(self, *args, **options):
        forcar = options.get('forcar', False)
        ids = options.get('ids', None)

        if forcar or ids:
            self.stdout.write(
                self.style.WARNING('Execução forçada (ignorando agendamentos)')
            )
            self._executar_atualizacao(agendamento=None, ids=ids)
            return

        # Verificar agendamentos ativos para o horário atual
        agora = timezone.localtime()
        hora_atual = agora.time()
        dia_semana_atual = agora.weekday()  # 0=Segunda, 6=Domingo

        # Mapear dia da semana para choices
        dia_map = {
            0: DiaSemana.SEG,
            1: DiaSemana.TER,
            2: DiaSemana.QUA,
            3: DiaSemana.QUI,
            4: DiaSemana.SEX,
            5: DiaSemana.SAB,
            6: DiaSemana.DOM,
        }
        dia_atual_choice = dia_map.get(dia_semana_atual)
        eh_dia_util = dia_semana_atual < 5

        agendamentos = AgendamentoAtualizacao.objects.filter(ativo=True)

        if not agendamentos.exists():
            self.stdout.write(
                self.style.WARNING('Nenhum agendamento ativo encontrado.')
            )
            return

        executou = False
        for ag in agendamentos:
            # Verificar se o horário corresponde (margem de 30 minutos)
            ag_hora = ag.horario
            hora_min = (
                datetime.combine(agora.date(), ag_hora) - timedelta(minutes=30)
            ).time()
            hora_max = (
                datetime.combine(agora.date(), ag_hora) + timedelta(minutes=30)
            ).time()

            dentro_horario = hora_min <= hora_atual <= hora_max

            # Verificar dia da semana
            dia_ok = False
            if ag.dias_semana == DiaSemana.TODOS:
                dia_ok = True
            elif ag.dias_semana == DiaSemana.SEG_SEX:
                dia_ok = eh_dia_util
            elif ag.dias_semana == dia_atual_choice:
                dia_ok = True

            if dentro_horario and dia_ok:
                # Verificar se já executou recentemente (última 1 hora)
                ultimo_log = LogAtualizacao.objects.filter(
                    agendamento=ag,
                    executado_em__gte=agora - timedelta(hours=1)
                ).first()

                if ultimo_log:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Agendamento "{ag.nome}" já executou '
                            f'recentemente ({ultimo_log.executado_em}). '
                            f'Pulando.'
                        )
                    )
                    continue

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Executando agendamento: {ag.nome} '
                        f'({ag.horario.strftime("%H:%M")})'
                    )
                )
                self._executar_atualizacao(
                    agendamento=ag,
                    apenas_ativos=ag.atualizar_apenas_ativos
                )
                executou = True

        if not executou:
            self.stdout.write(
                self.style.WARNING(
                    f'Nenhum agendamento para executar agora '
                    f'({hora_atual.strftime("%H:%M")}).'
                )
            )

    def _executar_atualizacao(
        self, agendamento=None, ids=None, apenas_ativos=True
    ):
        """Executa a atualização dos produtos com desativação por falhas."""
        inicio = time.time()
        
        # Constantes
        LIMITE_FALHAS = 5  # Desativa após N falhas consecutivas
        
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
                        produto.save(update_fields=['falhas_consecutivas'])
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

        # Criar log
        LogAtualizacao.objects.create(
            agendamento=agendamento,
            total_produtos=total,
            sucesso=sucesso,
            erros=erros,
            detalhes='\n'.join(detalhes_list),
            duracao_segundos=round(duracao, 2)
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
