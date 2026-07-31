# veyrys_shop/local_settings.py
# -------------------------------------------------------------
# FICHIER DE CONFIGURATION LOCAL - NE PAS PARTAGER
# -------------------------------------------------------------
# Ce fichier contient les identifiants SMTP sensibles.
# Django va automatiquement lire ces valeurs et écraser celles par défaut.

# 1. Configuration du serveur SMTP (ex: Gmail, Outlook, Hostinger, etc.)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# 2. Identifiants de connexion au compte email d'envoi
EMAIL_HOST_USER = 'veyrys28@gmail.com'
# Pour Gmail (ou 2FA), utiliser impérativement un "Mot de passe d'application" (16 caractères)
EMAIL_HOST_PASSWORD = 'vffl obqk cxnr rqog'

# 3. Paramètres de réception et d'expédition
# Adresse qui RECOIT les notifications lorsqu'une nouvelle commande client est validée
ADMIN_ORDER_EMAIL = 'veyrys28@gmail.com'
# Adresse apparaissant comme l'EXPEDITEUR dans la boite mail du client
DEFAULT_FROM_EMAIL = 'veyrys28@gmail.com'
