# Guide Pratique : Lancer et Tester le Projet Complet (CI 1–8 + CD 9–12 + Bonus)

Ce fichier explique comment démarrer et tester l'application **SRE Error Budget Calculator** ainsi que l'ensemble du pipeline **Jenkins / Docker / Trivy / Docker Hub / Mailpit / Rollback** développé en binôme par **Ghassen Ellili (CI 1–8)** et **Mohamed Amine Zalila (CD 9–12)**.

---

## 1. Démarrer l'environnement (Docker, Jenkins & Mailpit)

Ouvrez un terminal PowerShell ou Git Bash dans `d:\Projet-CiCd-Jenkins` :

```powershell
# Démarrer Mailpit (serveur SMTP sur 1025 et interface web sur 8025)
docker start mailpit
# (Ou si le conteneur n'existe pas encore : docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit)

# Vérifier les conteneurs actifs (ebc-staging sur 8081, ebc-prod sur 8082, mailpit sur 8025)
docker ps
```

### Liens utiles :
- **Dépôt GitHub** : `https://github.com/ghassenellili/Projet-CICD-JENKINS`
- **Dépôt Docker Hub** : `https://hub.docker.com/r/ghassenellili123/error-budget-calculator/tags`
- **Jenkins** : `http://localhost:8080` (ou `http://localhost:9090` selon l'installation locale)
- **Staging (`ebc-staging`)** : `http://localhost:8081` (`http://localhost:8081/health`)
- **Production (`ebc-prod`)** : `http://localhost:8082` (`http://localhost:8082/health`)
- **Mailpit** : `http://localhost:8025`

---

## 2. Tester l'application et ses routes HTTP

### A. Tests dans le navigateur (`GET`)
1. **Dashboard Web** : `http://localhost:8081` et `http://localhost:8082`
2. **Health Check** : `http://localhost:8081/health` $\rightarrow$ Retourne `OK` (HTTP 200).
3. **Calcul Downtime** : `http://localhost:8081/slo/downtime?slo=99.9&days=30` $\rightarrow$ Retourne `"allowed_downtime_minutes": 43.2` (`"allowed_downtime_seconds": 2592.0`).

### B. Tests de l'API dans PowerShell (`POST`)

```powershell
# 1. Décision "GO" (20 erreurs sur 100 000 requêtes, budget autorisé = 100)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 20}'

# 2. Décision "NO-GO" (150 erreurs sur 100 000 requêtes, budget dépassé)
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 150}'
```

---

## 3. Tester le Pipeline Complet (Features 1 à 12) dans Jenkins

### Scénario A : Build Vert + Déploiement Staging (`ebc-staging` :8081) & Production (`ebc-prod` :8082)

1. Dans Jenkins, ouvrez le job `error-budget-calculator` et cliquez sur **Build with Parameters**.
2. Choisissez **`DEPLOY_ENV` = `production`** et **`SLO_TARGET` = `99.9`**, puis cliquez sur **Build**.
3. Le pipeline exécute successivement :
   - **`Build`** : `.venv`, `pip install -r requirements.txt` et création de `build/dist/*.tar.gz`.
   - **`Tests` (en parallèle)** : **7 tests unitaires** (`Unit tests`) et **6 tests HTTP** (`HTTP tests`) + publication JUnit XML (`junit`).
   - **`Package`** : archivage des artefacts avec `fingerprint: true`.
   - **`Docker image`** : construction de `ghassenellili123/error-budget-calculator:1.0.${BUILD_NUMBER}` (jamais `latest`).
   - **`Security scan (Trivy)`** : scan de sécurité contre les failles `CRITICAL` avec le volume de cache `trivy-cache`.
   - **`Push`** : envoi sur Docker Hub via `withCredentials` (`dockerhub-token`) et `retry(3)`.
   - **`Deploy to staging`** : lancement du conteneur **`ebc-staging`** sur le port `8081` et exécution du **Smoke Test** (`/health` = `OK` et `/slo/downtime?slo=99.9&days=30` = `43.2`).
   - **`Deploy to production`** : pause avec approbation manuelle (`input`, bouton **Deploy**), puis déploiement de **la même image** dans le conteneur **`ebc-prod`** sur le port `8082` et vérification de `/health`.
   - **`Post Actions`** : envoi de l'e-mail via **Mailpit** (`emailext` à `team@lab.local`) avec la version dans l'objet + nettoyage `cleanWs()`.

### Scénario B : Tester un échec de test $\rightarrow$ Build Jaune (`UNSTABLE`) sans déploiement

1. Dans `tests/test_unit.py` (ligne 18), remplacez `43.2` par `999.9`, commitez et poussez.
2. Lancez le build dans Jenkins :
   - Le stage `Tests` marque le build en **JAUNE (`UNSTABLE`)** via `junit`.
   - Tous les stages suivants (`Docker image`, `Security scan (Trivy)`, `Push`, `Deploy to staging`, `Deploy to production`) sont **ignorés (*skipped*)**.
3. Remettez `43.2` dans `tests/test_unit.py`, commitez et poussez.

### Scénario C : Tester le Job Bonus de Rollback (`Jenkinsfile.rollback`)

1. Dans Jenkins, ouvrez le second job **`error-budget-calculator-rollback`**.
2. Cliquez sur **Build with Parameters** et saisissez `ROLLBACK_TO` = `1.0.8` (numéro de version déjà présent sur Docker Hub).
3. Le stage `Check the image` vérifie l'image avec `docker pull`, puis le stage `Rollback production` demande une confirmation (**Rollback**), redéploie `ebc-prod` sur le port `8082` avec cette version et vérifie `/health`.
