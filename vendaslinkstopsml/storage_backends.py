"""
Storage backends customizados para GCP Cloud Storage.
Usado para servir arquivos de mídia através do Google Cloud Storage em produção.
"""

from storages.backends.gcloud import GoogleCloudStorage


class PrivateMediaStorage(GoogleCloudStorage):
    """
    Storage customizado para arquivos de mídia (uploads) no GCP.
    
    Características:
    - Usa configurações de GS_PROJECT_ID, GS_BUCKET_NAME do settings.py
    - Aplica controle de acesso privado (GS_DEFAULT_ACL = None)
    - Gera URLs assinadas temporárias para segurança
    """
    default_acl = 'private'
    file_overwrite = False
