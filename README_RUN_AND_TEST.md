# Guide Pratique : Lancer et Tester le Projet Step-by-Step

Ce fichier explique comment démarrer et tester l'application **SRE Error Budget Calculator** ainsi que le pipeline **Jenkins / Docker / Mailpit** étape par étape sur votre machine.

---

## 1. Démarrer l'environnement (Docker & Mailpit)

Ouvrez un terminal PowerShell dans `d:\Projet-CiCd-Jenkins` :

```powershell
# Démarrer Mailpit (serveur SMTP local pour recevoir les e-mails de Jenkins)
docker start mailpit

# Si le conteneur mailpit n'existe pas encore, créez-le avec :
# docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit

# Vérifier les conteneurs en cours d'exécution
docker ps
```

### Liens utiles à ouvrir dans le navigateur :
- **Dépôt GitHub** : `https://github.com/ghassenellili/Projet-CICD-JENKINS`
- **Jenkins** : `http://localhost:8080`
- **Docker Hub (Tags)** : `https://hub.docker.com/r/ghassenellili/error-budget-calculator/tags`
- **Application Staging (`:8081`)** : `http://localhost:8081`
- **Application Production (`:8082`)** : `http://localhost:8082`
- **Interface Mailpit (`:8025`)** : `http://localhost:8025`

---

## 2. Tester l'application et ses routes HTTP

Une fois le conteneur Staging (`:8081`) ou Production (`:8082`) démarré (ou en local sur `:8080`) :

### A. Tests dans le navigateur (`GET`)
1. **Interface Web** : `http://localhost:8081`
2. **Health Check** : `http://localhost:8081/health` $\rightarrow$ Retourne `OK` (HTTP 200).
3. **Calcul du temps d'indisponibilité autorisé (Downtime)** :
   `http://localhost:8081/slo/downtime?slo=99.9&days=30`
   $\rightarrow$ Retourne `"allowed_downtime_minutes": 43.2` et `"allowed_downtime_seconds": 2592.0`.

### B. Tests de l'API dans PowerShell (`POST`)

```powershell
# 1. Tester le calcul de budget d'erreur en requêtes (/slo/budget)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/budget" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 25}'

# 2. Tester le calcul de Burn Rate (/slo/burn-rate)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/burn-rate" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "observed_error_rate_percent": 0.05}'

# 3. Tester la décision de mise en production : Cas "GO" (20 erreurs sur 100 000 requêtes, budget = 100)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 20}'

# 4. Tester la décision de mise en production : Cas "NO-GO" (150 erreurs sur 100 000 requêtes, budget dépassé)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 150}'
```

---

## 3. Tester le Pipeline CI/CD complet dans Jenkins

### Scénario A : Build vert + Déploiement en Staging (`:8081`) et Production (`:8082`)

1. **Modifier une ligne de code et pousser sur Git** :
   - Dans `app/__init__.py`, changez par exemple la version :
     ```python
     __version__ = "1.1.0"
     ```
   - Poussez la modification :
     ```powershell
     git add app/__init__.py
     git commit -m "Bump application display version to 1.1.0"
     git push
     ```
2. **Lancer le build dans Jenkins** :
   - Sur Jenkins (`http://localhost:8080`), ouvrez le job du projet et cliquez sur **Build with Parameters**.
   - Choisissez :
     - `DEPLOY_ENV` = `production`
     - `SLO_TARGET` = `99.9`
   - Cliquez sur **Build**.
3. **Suivre l'exécution des stages** :
   - `Build` : création du `.venv`, installation des dépendances et création de l'archive `.tar.gz`.
   - `Tests` : exécution en parallèle de `Unit tests` (7 tests) et `HTTP tests` (5 tests) + publication JUnit XML.
   - `Package` : archivage des artefacts avec `fingerprint`.
   - `Docker image` : construction de l'image `ghassenellili/error-budget-calculator:1.0.N`.
   - `Security scan (Trivy)` : scan de sécurité de l'image contre les failles `CRITICAL`.
   - `Push` : envoi de l'image sur Docker Hub avec `withCredentials` et `retry(3)`.
   - `Staging :8081` : déploiement du conteneur sur le port `8081` et exécution du **Smoke Test** (`/health` = `OK` et `/slo/downtime` = `43.2`).
4. **Approuver le déploiement en Production (`:8082`)** :
   - Lorsque le stage `Production :8082` affiche la demande d'approbation (`input`), cliquez sur **Deploy to Production**.
5. **Vérifier le résultat final** :
   - Dans PowerShell, vérifiez que les deux conteneurs (`8081` et `8082`) tournent avec la même image :
     ```powershell
     docker ps
     ```
   - Vérifiez l'application sur `http://localhost:8081` et `http://localhost:8082`.
   - Vérifiez le nouveau tag `1.0.N` dans l'onglet **Tags** sur Docker Hub.
   - Vérifiez l'e-mail `[SUCCESS] error-budget-calculator v1.0.N` dans **Mailpit** (`http://localhost:8025`).

---

### Scénario B : Tester un échec de test (Build Jaune `UNSTABLE` sans déploiement)

1. **Casser volontairement un test unitaire** :
   - Ouvrez `tests/test_unit.py` à la ligne 18 et remplacez `43.2` par `999.9` :
     ```python
     assert result["allowed_downtime_minutes"] == 999.9
     ```
   - Commitez et poussez :
     ```powershell
     git add tests/test_unit.py
     git commit -m "Break unit test intentionally to test UNSTABLE build"
     git push
     ```
2. **Relancer le build dans Jenkins** :
   - Cliquez sur **Build with Parameters** $\rightarrow$ **Build**.
   - Le stage `Tests` détecte l'échec via `junit` et marque le build en **JAUNE (`UNSTABLE`)**.
   - Les stages `Docker image`, `Security scan (Trivy)`, `Push`, `Staging :8081` et `Production :8082` sont automatiquement **ignorés (skipped)**.
   - Un e-mail `[UNSTABLE]` est envoyé dans **Mailpit** (`http://localhost:8025`).
3. **Remettre le test au vert** :
   - Remettez `43.2` à la ligne 18 de `tests/test_unit.py` :
     ```python
     assert result["allowed_downtime_minutes"] == 43.2
     ```
   - Commitez et poussez :
     ```powershell
     git add tests/test_unit.py
     git commit -m "Restore unit test expected value"
     git push
     ```
