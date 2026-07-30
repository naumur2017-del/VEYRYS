# VEYRYS Shop

VEYRYS Shop est une boutique e-commerce développée avec Django. L'application permet d'afficher un catalogue produit par catégories, de consulter une fiche produit, d'ajouter des articles au panier avec variantes, puis de passer une commande avec confirmation par email.

## Fonctionnalités

- Catalogue produit avec filtres par catégorie
- Fiche produit détaillée avec images
- Panier de commande avec gestion des quantités
- Sélection de couleur et de taille selon le produit
- Création de commande avec informations client
- Notification email vers l'administrateur et le client
- Fichiers `robots.txt` et `sitemap.xml` générés par l'application
- Interface d'administration Django pour gérer catégories, produits, commandes et notifications

## Arborescence principale

- `veyrys_shop/` : configuration du projet Django
- `shop/` : application métier de la boutique
- `static/` : fichiers statiques
- `media/` : fichiers téléversés
- `IMAGE PRODUITS/` : dossier de ressources produit utilisé pour les images d'origine
- `db.sqlite3` : base SQLite locale
- `import_products.py` et `extract_data.py` : scripts utilitaires liés aux données produits

## Prérequis

- Python 3
- `pip`
- Un environnement virtuel recommandé

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Le projet utilise SQLite par défaut, via `db.sqlite3`.

La configuration email est lue depuis les variables d'environnement suivantes, avec des valeurs par défaut pour le développement:

- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `ADMIN_ORDER_EMAIL`
- `SITE_URL`

## Lancement en local

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ensuite, ouvrir l'application sur `http://127.0.0.1:8000/`.

## Accès administrateur

L'admin Django est disponible sur `http://127.0.0.1:8000/admin/`.

Depuis l'admin, vous pouvez gérer:

- les catégories
- les produits
- les images produits
- les commandes
- les notifications de commande

## URLs principales

- `/` : liste des produits
- `/cart/` : panier
- `/order/create/` : création de commande
- `/<categorie>/` : liste des produits d'une catégorie
- `/robots.txt` : règles robots
- `/sitemap.xml` : sitemap du site

## Notes techniques

- Le panier est stocké en session.
- Les commandes déclenchent une notification email pour l'admin et le client.
- Les produits peuvent avoir des tailles et couleurs adaptées selon leur catégorie.

## Déploiement

Avant une mise en production, vérifier au minimum:

- `DEBUG = False`
- `ALLOWED_HOSTS` correctement configuré
- les variables email définies
- `SITE_URL` pointant vers le domaine public
