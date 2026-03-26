/**
 * Modal de Cadastro para Newsletter
 * Captura nome, email, telefone e preferências do usuário
 */

'use strict';

(function() {
    // Configuração
    const CONFIG = {
        modalId: 'newsletterModal',
        formId: 'newsletterForm',
        apiEndpoint: '/api/newsletter/signup/',
        storageKey: 'newsletter_modal_shown'
    };

    // Função para criar o modal HTML
    function createModal() {
        const modalHTML = `
        <div class="modal fade" id="${CONFIG.modalId}" tabindex="-1" aria-labelledby="newsletterModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title" id="newsletterModalLabel">
                            <i class="bi bi-envelope-heart me-2"></i>Receba as Melhores Ofertas!
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted mb-3">
                            <i class="bi bi-star-fill text-warning me-1"></i>
                            Cadastre-se para receber promocoes exclusivas, analises de produtos e atualizacoes dos melhores precos!
                        </p>
                        <form id="${CONFIG.formId}" class="needs-validation">
                            <div class="row">
                                <div class="col-md-12 mb-3">
                                    <label for="nome" class="form-label">Nome Completo *</label>
                                    <input type="text" class="form-control" id="nome" name="nome" required placeholder="Seu nome">
                                    <div class="invalid-feedback">Por favor, forneça seu nome.</div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-7 mb-3">
                                    <label for="email" class="form-label">Email *</label>
                                    <input type="email" class="form-control" id="email" name="email" required placeholder="seu@email.com">
                                    <div class="invalid-feedback">Por favor, forneça um email valido.</div>
                                </div>
                                <div class="col-md-5 mb-3">
                                    <label for="telefone" class="form-label">Telefone / WhatsApp *</label>
                                    <input type="tel" class="form-control" id="telefone" name="telefone" required placeholder="11999999999">
                                    <small class="text-muted d-block mt-1">Com DDD, sem caracteres especiais</small>
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="canal" class="form-label">Como voce prefere receber atualizacoes? *</label>
                                <select class="form-select" id="canal" name="canal_preferido" required>
                                    <option value="">-- Selecione uma opcao --</option>
                                    <option value="email">Email</option>
                                    <option value="whatsapp">WhatsApp</option>
                                    <option value="ambos">Email e WhatsApp</option>
                                </select>
                                <div class="invalid-feedback">Selecione uma opcao.</div>
                            </div>
                            
                            <div class="card bg-light mb-3">
                                <div class="card-body">
                                    <label class="form-label fw-bold mb-3">Que tipo de conteudo te interessa?</label>
                                    <div class="form-check mb-2">
                                        <input class="form-check-input" type="checkbox" id="promo" name="receber_promocoes" value="true" checked>
                                        <label class="form-check-label" for="promo">
                                            <i class="bi bi-tag-fill text-success me-1"></i>
                                            <strong>Promocoes e Descontos</strong> - Ofertas imperdveis e cupons exclusivos
                                        </label>
                                    </div>
                                    <div class="form-check mb-2">
                                        <input class="form-check-input" type="checkbox" id="analise" name="receber_analises" value="true" checked>
                                        <label class="form-check-label" for="analise">
                                            <i class="bi bi-graph-up text-info me-1"></i>
                                            <strong>Analises de Produtos</strong> - Comparacoes, dicas de compra e tendencias
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="update" name="receber_atualizacoes" value="true" checked>
                                        <label class="form-check-label" for="update">
                                            <i class="bi bi-lightning-charge-fill text-warning me-1"></i>
                                            <strong>Atualizacoes do Site</strong> - Novas categorias, features e melhorias
                                        </label>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="alert alert-info small" role="alert">
                                <i class="bi bi-info-circle me-1"></i>
                                Nao compartilhamos seus dados com terceiros. Saiba mais sobre nossa <a href="/legal/privacidade/" class="text-decoration-none" onclick="abrirPaginaPrivacidade(event)">politica de privacidade</a>.
                            </div>
                            
                            <div class="modal-footer pt-3 border-top">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary btn-lg" id="submitBtn">
                                    <i class="bi bi-check-circle me-1"></i>Cadastrar Agora
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    // Funcao para obter IP e user agent
    function getClientInfo() {
        return {
            ip: 'auto',  // Sera detectado no servidor via request.META
            user_agent: navigator.userAgent
        };
    }

    // Funcao para submeter o formulario
    function setupFormSubmit() {
        const form = document.getElementById(CONFIG.formId);
        if (!form) return;

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Validacao
            if (!form.checkValidity() === false) {
                e.stopPropagation();
            }

            // Coletar dados
            const data = {
                nome: document.getElementById('nome').value.trim(),
                email: document.getElementById('email').value.trim(),
                telefone: document.getElementById('telefone').value.trim(),
                canal_preferido: document.getElementById('canal').value,
                receber_promocoes: document.getElementById('promo').checked,
                receber_analises: document.getElementById('analise').checked,
                receber_atualizacoes: document.getElementById('update').checked,
                user_agent: navigator.userAgent
            };

            // Validar dados
            if (!data.nome || !data.email || !data.telefone) {
                alert('Por favor, preencha todos os campos obrigatorios');
                return;
            }

            // Desabilitar botao
            const submitBtn = document.getElementById('submitBtn');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando...';

            try {
                // Enviar dados para o servidor
                const response = await fetch(CONFIG.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    const result = await response.json();
                    
                    // Mostrar mensagem de sucesso
                    showSuccessMessage();
                    
                    // Marcar como mostrado para nao aparecer novamente hoje
                    markModalShown();
                    
                    // Fechar modal apos 2 segundos
                    setTimeout(() => {
                        const modal = bootstrap.Modal.getInstance(document.getElementById(CONFIG.modalId));
                        if (modal) modal.hide();
                        form.reset();
                    }, 2000);
                } else {
                    const error = await response.json();
                    alert('Erro ao cadastrar: ' + (error.detail || 'Tente novamente'));
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro de conexao. Tente novamente');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }

    // Funcao para obter CSRF token
    function getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Funcao para mostrar mensagem de sucesso
    function showSuccessMessage() {
        const form = document.getElementById(CONFIG.formId);
        const formContent = form.parentElement;
        
        formContent.innerHTML = `
        <div class="text-center py-4">
            <i class="bi bi-check-circle text-success" style="font-size: 3rem;"></i>
            <h4 class="mt-3 text-success">Cadastro Realizado com Sucesso!</h4>
            <p class="text-muted">Voce ja esta recebendo as melhores ofertas do mercado.</p>
            <p class="small text-muted">Verifique seu email para confirmar o cadastro.</p>
        </div>
        `;
    }

    // Funcao para marcar modal como mostrado
    function markModalShown() {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        localStorage.setItem(CONFIG.storageKey, tomorrow.getTime().toString());
    }

    // Funcao para verificar se modal ja foi mostrado hoje
    function wasModalShownToday() {
        const stored = localStorage.getItem(CONFIG.storageKey);
        if (!stored) return false;
        return new Date().getTime() < parseInt(stored);
    }

    // Funcao para inicializar o modal
    function init() {
        // Criar modal
        createModal();
        setupFormSubmit();

        // Mostrar modal apos 5 segundos se nao foi no mostrado no  dia
        if (!wasModalShownToday() && document.querySelectorAll('.produto-card').length > 0) {
            setTimeout(() => {
                const modal = new bootstrap.Modal(document.getElementById(CONFIG.modalId));
                modal.show();
            }, 5000);
        }

        // Botao manual para abrir modal
        const btnOpenModal = document.getElementById('btnOpenNewsletter');
        if (btnOpenModal) {
            btnOpenModal.addEventListener('click', function(e) {
                e.preventDefault();
                const modal = new bootstrap.Modal(document.getElementById(CONFIG.modalId));
                modal.show();
            });
        }
    }

    // Funcao para abrir página de privacidade em modal
    window.abrirPaginaPrivacidade = function(event) {
        event.preventDefault();
        
        // Criar modal dinamicamente - aumentado para modal-xl
        const modalHTML = `
        <div class="modal fade" id="modalPrivacidade" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable" style="max-width: 90%; max-height: 90vh;">
                <div class="modal-content" style="max-height: 85vh;">
                    <div class="modal-header bg-primary text-white sticky-top">
                        <h5 class="modal-title">Política de Privacidade</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="modalPrivacidadeContent" style="overflow-y: auto; padding: 30px;">
                        <p class="text-center"><span class="spinner-border spinner-border-sm"></span> Carregando...</p>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Remover modal anterior se existir
        const oldModal = document.getElementById('modalPrivacidade');
        if (oldModal) {
            oldModal.remove();
        }
        
        // Adicionar novo modal
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Limpar qualquer timeout anterior
        if (window.privacidadeTimeoutId) {
            clearTimeout(window.privacidadeTimeoutId);
        }
        
        // Abrir modal
        const modal = new bootstrap.Modal(document.getElementById('modalPrivacidade'));
        modal.show();
        
        // Fechar modal automaticamente após 3 segundos
        window.privacidadeTimeoutId = setTimeout(function() {
            const privacidadeModal = bootstrap.Modal.getInstance(document.getElementById('modalPrivacidade'));
            if (privacidadeModal) {
                privacidadeModal.hide();
            }
        }, 3000);
        
        // Carregar conteúdo via AJAX
        fetch('/legal/privacidade/')
            .then(response => response.text())
            .then(html => {
                // Extrair apenas o conteúdo com a classe conteudo-legal
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Procurar por seletores em prioridade
                let content = doc.querySelector('.conteudo-legal');
                if (!content) {
                    content = doc.querySelector('[class*="conteudo"]');
                }
                if (!content) {
                    content = doc.querySelector('.container > div');
                }
                if (!content) {
                    // Fallback: pegar tudo após h1
                    const h1 = doc.querySelector('h1');
                    if (h1) {
                        // Criar div com h1 e tudo depois
                        const div = document.createElement('div');
                        div.innerHTML = doc.body.innerHTML;
                        content = div.querySelector('[role="main"]') || div;
                    }
                }
                
                const contentDiv = document.getElementById('modalPrivacidadeContent');
                if (content && content.innerHTML.trim()) {
                    // Adicionar o HTML com estilos
                    contentDiv.innerHTML = `
                        <style>
                            #modalPrivacidadeContent h1,
                            #modalPrivacidadeContent h2,
                            #modalPrivacidadeContent h3,
                            #modalPrivacidadeContent h4 {
                                margin-top: 20px;
                                margin-bottom: 15px;
                                font-weight: 600;
                                color: #222;
                            }
                            #modalPrivacidadeContent p {
                                margin-bottom: 12px;
                                line-height: 1.6;
                            }
                            #modalPrivacidadeContent ul,
                            #modalPrivacidadeContent ol {
                                margin-left: 20px;
                                margin-bottom: 15px;
                            }
                            #modalPrivacidadeContent li {
                                margin-bottom: 8px;
                            }
                            #modalPrivacidadeContent b,
                            #modalPrivacidadeContent strong {
                                font-weight: 600;
                                color: #222;
                            }
                        </style>
                        ${content.innerHTML}
                    `;
                } else {
                    contentDiv.innerHTML = '<p>Conteúdo não encontrado. <a href="/legal/privacidade/" target="_blank">Clique aqui</a> para abrir em nova aba.</p>';
                }
            })
            .catch(error => {
                console.error('Erro ao carregar privacidade:', error);
                document.getElementById('modalPrivacidadeContent').innerHTML = 
                    '<p class="text-danger">Erro ao carregar página. Por favor, <a href="/legal/privacidade/" target="_blank">clique aqui</a> para abrir em nova aba.</p>';
            });
    };

    // Inicializar quando DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
