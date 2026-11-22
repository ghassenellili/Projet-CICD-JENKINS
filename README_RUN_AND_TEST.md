# Guide Pratique : Lancer et Tester la Partie CI (Features 1 à 8)

Ce fichier explique comment lancer et tester l'application **SRE Error Budget Calculator** ainsi que la partie **Continuous Integration (Features 1 à 8)** du pipeline **Jenkins / Docker / Docker Hub** sur votre machine.

---

## 1. Périmètre couvert par votre partie CI (Features 1 à 8)

1. **Feature 1 — Everything in Git** : Code de l'application (`app/`), tests (`tests/`), `Dockerfile` et `Jenkinsfile` sur GitHub, lus via *Pipeline script from SCM*.
2. **Feature 2 — Build** : Création de l'environnement virtuel Python (`.venv`), installation des dépendances (`pip install -r requirements.txt`) et création du paquet `build/dist/*.tar.gz`.
3. **Feature 3 — Tests in parallel** : Exécution simultanée en parallèle de **7 tests unitaires** (`Unit tests`) et **5 tests HTTP** (`HTTP tests`).
4. **Feature 4 — Test reports** : Publication des rapports XML avec `junit 'build/test-results/*.xml'`. Un test qui échoue passe le build en **JAUNE (`UNSTABLE`)**.
5. **Feature 5 — Parameters** : `DEPLOY_ENV` (`staging` ou `production`) et `SLO_TARGET` (`99.9`).
6. **Feature 6 — Artifacts** : Archivage du paquet de build et des rapports XML avec `fingerprint: true`.
7. **Feature 7 — Docker image** : Construction de l'image uniquement si le build est **VERT (`SUCCESS`)**, avec le tag `ghassenellili/error-budget-calculator:1.0.${BUILD_NUMBER}` (jamais `latest`).
8. **Feature 8 — Push to Docker Hub** : Authentification sécurisée via `withCredentials` (`dockerhub-token`) et push de l'image taguée sur Docker Hub (avec les bonus **Trivy Security Scan**, `timeout` et `retry(3)`).

---

## 2. Tester l'application et les tests en local

Dans votre terminal PowerShell (`d:\Projet-CiCd-Jenkins`) :

```powershell
# 1. Lancer les 7 tests unitaires (génère build/test-results/unit-report.xml)
python -m pytest tests/test_unit.py --junitxml=build/test-results/unit-report.xml

# 2. Lancer les 5 tests HTTP (génère build/test-results/http-report.xml)
python -m pytest tests/test_http.py --junitxml=build/test-results/http-report.xml

# 3. Construire et lancer le conteneur Docker manuellement pour tester l'application
docker build -t ghassenellili/error-budget-calculator:1.0.1 .
docker run -d --name error-budget-test -p 8080:8080 ghassenellili/error-budget-calculator:1.0.1
```

### Tester les routes HTTP de l'application (`http://localhost:8080`) :
- **Interface Web** : `http://localhost:8080`
- **Health Check** : `http://localhost:8080/health` $\rightarrow$ Retourne `OK` (HTTP 200)
- **Calcul Downtime** : `http://localhost:8080/slo/downtime?slo=99.9&days=30` $\rightarrow$ Retourne `"allowed_downtime_minutes": 43.2`

```powershell
# Tester la décision GO (20 erreurs sur 100 000 requêtes, budget = 100)
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 20}'

# Tester la décision NO-GO (150 erreurs sur 100 000 requêtes, budget dépassé)
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/slo/release-check" `
  -ContentType "application/json" `
  -Body '{"slo_target": 99.9, "total_requests": 100000, "failed_requests": 150}'

# Arrêter le conteneur de test local
docker rm -f error-budget-test
```

---

## 3. Tester le Pipeline CI (Features 1 à 8) dans Jenkins

### Scénario A : Build CI Vert (`SUCCESS`) jusqu'au Push Docker Hub

1. Ouvrez Jenkins (`http://localhost:8080`) sur votre job.
2. Cliquez sur **Build with Parameters** $\rightarrow$ **Build**.
3. Vérifiez que chaque stage passe au **VERT** :
   - `Build`
   - `Tests` (`Unit tests` + `HTTP tests` en parallèle)
   - `Package` (vérifiez les fichiers archivés et leurs empreintes MD5 dans *Fingerprints*)
   - `Docker image` (`ghassenellili/error-budget-calculator:1.0.N`)
   - `Security scan (Trivy)`
   - `Push`
4. Ouvrez **Docker Hub** (`https://hub.docker.com/r/ghassenellili/error-budget-calculator/tags`) et vérifiez que le nouveau tag `1.0.N` est bien publié (sans tag `latest`).

### Scénario B : Test cassé $\rightarrow$ Build Jaune (`UNSTABLE`) sans création d'image Docker

1. Dans `tests/test_unit.py` (ligne 18), remplacez `43.2` par `999.9` :
   ```python
   assert result["allowed_downtime_minutes"] == 999.9
   ```
2. Commitez et poussez sur votre branche :
   ```powershell
   git add tests/test_unit.py
   git commit -m "Break unit test to verify yellow UNSTABLE build skips Docker image and push"
   git push
   ```
3. Lancez le build dans Jenkins :
   - Le stage `Tests` détecte l'échec via `junit` et passe le build en **JAUNE (`UNSTABLE`)**.
   - Les stages `Docker image`, `Security scan (Trivy)` et `Push` sont automatiquement **ignorés (*skipped*)**.
4. Remettez `43.2` dans `tests/test_unit.py`, commitez et poussez pour remettre le build au vert.
