# 🏦 NovaBank — Application de Gestion Bancaire

> Application web de gestion bancaire complète développée avec **Django** et **Bootstrap 5**, permettant aux utilisateurs de gérer leurs comptes, effectuer des transactions et suivre leurs finances en temps réel.

---

## 🛠️ Technologies Utilisées

### Backend

| Technologie       | Version   | Rôle                                      |
|-------------------|-----------|--------------------------------------------|
| **Python**        | 3.x       | Langage de programmation principal          |
| **Django**        | 6.0.4     | Framework web (MTV : Model-Template-View)   |
| **MySQL**         | —         | Base de données relationnelle               |
| **ReportLab**     | —         | Génération de fichiers PDF                  |
| **xhtml2pdf**     | —         | Conversion HTML → PDF (rapports)            |
| **Pillow**        | —         | Traitement d'images (cachet officiel, etc.) |
| **python-dateutil** | —       | Manipulation avancée des dates              |

### Frontend

| Technologie           | Version   | Rôle                                        |
|-----------------------|-----------|----------------------------------------------|
| **HTML5**             | —         | Structure des pages (Django Templates)        |
| **CSS3**              | —         | Styles personnalisés (`style.css`)            |
| **JavaScript**        | ES6+      | Logique côté client (Vanilla JS)              |
| **Bootstrap**         | 5.3.3     | Framework CSS responsive (via CDN)            |
| **Bootstrap Icons**   | 1.11.3    | Icônes vectorielles (via CDN)                 |
| **GSAP**              | 3.12.2    | Animations de scroll (ScrollTrigger)          |
| **Chart.js**          | —         | Graphiques interactifs (Dashboard)            |
| **Google Fonts**      | Inter     | Typographie moderne                           |

### Base de Données

- **MySQL** — Base de données principale (port `3306`)

---

## 📁 Architecture du Projet

```
projet-gestion_de_banque-/
│
├── bank_project/                    # Répertoire principal Django
│   │
│   ├── bank_project/                # Configuration du projet
│   │   ├── settings.py              # Paramètres Django (DB, apps, middleware)
│   │   ├── urls.py                  # Routes URL principales
│   │   └── wsgi.py                  # Point d'entrée WSGI
│   │
│   ├── accounts/                    # 👤 App : Authentification & Profils
│   │   ├── models.py                # Modèle Profile (extension de User)
│   │   ├── views.py                 # Inscription, connexion, profil
│   │   ├── forms.py                 # Formulaires personnalisés
│   │   ├── backends.py              # Backend auth (email ou username)
│   │   └── management/              # Commandes manage.py personnalisées
│   │
│   ├── banking/                     # 💰 App : Opérations Bancaires
│   │   ├── models.py                # Modèles Account & Transaction
│   │   └── views.py                 # Dépôt, retrait, virement, export PDF
│   │
│   ├── dashboard/                   # 📊 App : Tableau de Bord
│   │   └── views.py                 # Métriques et graphiques Chart.js
│   │
│   ├── notifications/               # 🔔 App : Notifications
│   │   ├── models.py                # Modèle Notification
│   │   ├── context_processors.py    # Compteur de notifications non lues
│   │   └── views.py                 # Affichage et gestion
│   │
│   ├── cards/                       # 💳 App : Cartes Bancaires
│   │   ├── models.py                # Modèle Card (plafond, statut)
│   │   └── views.py                 # Gestion des cartes
│   │
│   ├── administration/              # 🛡️ App : Panneau d'Administration
│   │   └── views.py                 # Supervision système (staff only)
│   │
│   ├── templates/                   # 📄 Templates HTML (Django Templates)
│   │   ├── base.html                # Layout principal (navbar, footer)
│   │   ├── index.html               # Page d'accueil (landing page)
│   │   ├── accounts/                # Templates auth (login, register)
│   │   ├── banking/                 # Templates bancaires
│   │   ├── dashboard/               # Templates tableau de bord
│   │   ├── cards/                   # Templates cartes
│   │   ├── notifications/           # Templates notifications
│   │   ├── administration/          # Templates admin personnalisé
│   │   └── admin/                   # Surcharge du Django Admin
│   │
│   ├── static/                      # 🎨 Fichiers Statiques
│   │   ├── css/style.css            # Styles CSS personnalisés
│   │   └── js/main.js               # JavaScript (thème, animations, particules)
│   │
│   ├── manage.py                    # Commande Django
│   ├── requirements.txt             # Dépendances Python
│   └── db.sqlite3                   # Base de données SQLite (dev)
│
├── CAHIER DE CHARGE (PYTHON).pdf    # Cahier des charges du projet (PDF)
├── Rapport-Django.docx              # Rapport du projet Django
├── venv/                            # Environnement virtuel Python
└── README.md                        # Ce fichier
```

---

## ✨ Fonctionnalités

### 👤 Gestion des Utilisateurs
- Inscription et connexion (par **email** ou **nom d'utilisateur**)
- Profil utilisateur avec informations personnelles (téléphone, adresse, date de naissance)
- Backend d'authentification personnalisé (`EmailOrUsernameBackend`)
- Commande `init_nova_admin` pour créer l'administrateur par défaut

### 💰 Opérations Bancaires
- **Création de comptes** bancaires (Courant, Épargne, etc.) — requis avant toute opération
- **Dépôt** : min **100 MAD**, max **50 000 MAD** par opération
- **Retrait** : min **50 MAD**, max **3 000 MAD** par opération, plafond **10 000 MAD/jour**
- **Virement** : min **10 MAD**, max **10 000 MAD** par opération, plafond **20 000 MAD/jour**
- Virement vers soi-même **bloqué**
- Vérification du solde avant toute opération débitrice
- **Historique des transactions** avec filtrage par type
- **Export PDF** des transactions (rapport avec cachet officiel)

### 💳 Cartes Bancaires
- Demande de carte liée à un **compte actif** uniquement
- Carte valide **3 ans** à partir de la date de création
- Paiement par carte avec vérification d'**expiration** et de **solde**
- Plafond de dépenses journalier (défaut : **10 000 MAD/jour**)
- Activation / désactivation à la volée
- Les cartes expirées sont automatiquement exclues des paiements

### 🔔 Notifications
- Notifications automatiques pour chaque opération
- Compteur de notifications non lues (badge temps réel)
- Types : `confirm_transaction`, `login_alert`, `account_created`

### 📊 Tableau de Bord
- Solde total et répartition par compte
- Graphiques interactifs avec **Chart.js**
- Métriques et statistiques utilisateur

### 🛡️ Administration (Staff)
- **Dashboard superviseur** : vue d'ensemble (utilisateurs, comptes, volumes, graphiques)
- **Gestion des utilisateurs** : recherche, activation/désactivation, **suppression définitive**
  - Protection : impossible de supprimer son propre compte ou le dernier super-utilisateur
  - Confirmation via **modal moderne** (pas d'alert navigateur)
- **Gestion des comptes bancaires** : filtrage par statut, activation/désactivation
- **Suivi des transactions** : filtrage par type, recherche par numéro de compte
- Pagination sur toutes les listes
- Accès au **Django Admin** natif pour les opérations CRUD

### 🎨 Interface Utilisateur
- Design responsive avec **Bootstrap 5**
- **Mode sombre / clair** avec persistance (`localStorage`)
- Animations de scroll avec **GSAP ScrollTrigger**
- Particules animées sur la page d'accueil (Canvas)
- Compteur animé pour les statistiques
- Typographie moderne (**Inter** via Google Fonts)

---

## 🚀 Installation & Lancement

### Prérequis
- **Python 3.10+**
- **MySQL** (ou utiliser SQLite3 en décommentant dans `settings.py`)
- **pip** (gestionnaire de paquets Python)

### Étapes

1. **Cloner le projet**
   ```bash
   git clone https://github.com/yassine-ait-ali-oumghar/projet-gestion_de_banque-.git
   cd projet-gestion_de_banque-
   ```

2. **Créer et activer l'environnement virtuel**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # Linux / Mac
   ```

3. **Installer les dépendances**
   ```bash
   cd bank_project
   pip install -r requirements.txt
   ```

4. **Configurer la base de données**

   - **Option MySQL** : Créer une base de données `bank_project` dans MySQL
   - **Option SQLite3** : Décommenter la configuration SQLite3 dans `settings.py` et commenter celle de MySQL

5. **Appliquer les migrations**
   ```bash
   python manage.py migrate
   ```

6. **Créer le compte administrateur**
   ```bash
   python manage.py init_nova_admin
   ```
   Ou il sera créé automatiquement si `DEBUG = True`.

7. **Vérifier l'intégrité du système**
   ```bash
   python manage.py check
   ```

8. **Lancer le serveur**
   ```bash
   python manage.py runserver
   ```

9. **Ouvrir dans le navigateur** → [http://localhost:8000/](http://localhost:8000/)

---

## 🔑 Compte Administrateur par Défaut

| Champ          | Valeur                     |
|----------------|----------------------------|
| **Username**   | `admin`                    |
| **Email**      | `admin@novabank.local`     |
| **Mot de passe** | `NovaBank-Admin-2026!`  |

> ⚠️ **Ne jamais utiliser ces identifiants en production.** Changez le mot de passe immédiatement.

---

## 📦 Dépendances Python (`requirements.txt`)

```
django>=4.2
python-dateutil
reportlab
xhtml2pdf
pillow
```

---

## 🔒 Règles Métier (Contrôle de Saisie)

| Opération | Minimum | Maximum / op. | Plafond journalier |
|-----------|---------|---------------|--------------------|
| **Dépôt** | 100 MAD | 50 000 MAD | — |
| **Retrait** | 50 MAD | 3 000 MAD | 10 000 MAD/jour |
| **Virement** | 10 MAD | 10 000 MAD | 20 000 MAD/jour |
| **Paiement carte** | — | Plafond carte | 10 000 MAD/jour |

**Autres protections :**
- Impossible de faire un virement vers son propre compte
- Impossible de débiter un compte inactif ou insuffisamment approvisionné
- Impossible d'utiliser une carte expirée ou inactive
- Compte bancaire requis avant toute transaction
- Carte active requise avant tout paiement par carte

---

## 📄 Licence

Projet académique — Développé dans le cadre du cahier des charges **"Gestion de Banque"** en Python/Django.

---

## 📚 Documents du Projet

| Document | Description |
|----------|-------------|
| **CAHIER DE CHARGE (PYTHON).pdf** | Cahier des charges complet du projet |
| **Rapport-Django.docx** | Rapport détaillé du projet Django |

---

<p align="center">
  <strong>NovaBank</strong> — La banque intelligente conçue pour le monde moderne 🚀
</p>
