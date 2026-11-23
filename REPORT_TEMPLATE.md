# Rapport de Projet Final — CI/CD with Jenkins & Docker
## Application : SRE Error Budget Calculator

- **Établissement** : Horizon School of Digital Technologies
- **Binôme** : Ghassen Ellili (CI — Features 1 à 8) & Mohamed Amine Zalila (CD — Features 9 à 12)
- **Dépôt GitHub** : `https://github.com/ghassenellili/Projet-CICD-JENKINS`
- **Dépôt Docker Hub** : `https://hub.docker.com/r/ghassenellili123/error-budget-calculator` (Collaborateurs : `ghassenellili123` & `aminezalila`)

---

## 1. Présentation de l'application et du scénario métier

L'application **SRE Error Budget Calculator** est un microservice web et API REST développé en **Python (Flask)**. Dans une organisation DevOps/SRE, la décision d'autoriser ou de bloquer une mise en production repose sur le **Budget d'Erreur (Error Budget)** défini par le *Service Level Objective (SLO)* (par exemple `99.9%` de disponibilité sur 30 jours, soit `43.2 minutes` d'indisponibilité tolérée).

Notre application expose :
- `GET /health` : retourne `OK` (HTTP 200), utilisé par le `HEALTHCHECK` Docker et le smoke test Jenkins.
- `GET /slo/downtime?slo=99.9&days=30` : calcule le temps d'indisponibilité maximal autorisé en minutes et secondes (`43.2 min` / `2592.0 s`).
- `POST /slo/budget` : calcule le nombre d'erreurs HTTP tolérées, le budget restant et le pourcentage consommé.
- `POST /slo/burn-rate` : calcule la vitesse de consommation du budget (*Burn Rate*) et détermine le niveau d'alerte (`NORMAL`, `WARNING`, `HIGH`, `CRITICAL`).
- `POST /slo/release-check` : agit comme une barrière de déploiement automatique (*Release Gate*) en retournant `GO`, `CAUTION` ou `NO-GO`.

---

## 2. Vue d'ensemble du Pipeline Jenkins (Blue Ocean)

![Pipeline Blue Ocean — Exécution complète en vert avec Tests en parallèle](screenshots/01-blue-ocean-parallel.png)

### Explication détaillée de chaque Stage (et pourquoi il est nécessaire)

| Stage | Rôle technique | Pourquoi ce stage est indispensable |
| :--- | :--- | :--- |
| **1. Build** | Crée un environnement virtuel isolé (`.venv`), installe les dépendances depuis `requirements.txt` et prépare l'archive de distribution `build/dist/*.tar.gz`. | Garantit que l'application et ses dépendances s'installent proprement avant de lancer les tests. |
| **2. Tests (Parallel : `Unit tests` & `HTTP tests`)** | Exécute simultanément **7 tests unitaires** (`tests/test_unit.py`) et **5 tests HTTP** (`tests/test_http.py`) avec `python -m pytest --junitxml=...`, puis publie les rapports via `junit`. | Le parallélisme réduit le temps de feedback CI. La publication JUnit passe le build en **jaune (`UNSTABLE`)** si un test échoue, empêchant la création d'une image défectueuse. |
| **3. Package (Artifacts)** | Archive le paquet de build et les rapports XML JUnit avec `archiveArtifacts(..., fingerprint: true)`. | Assure la traçabilité complète (empreinte MD5/fingerprint) entre un numéro de build Jenkins et les fichiers produits. |
| **4. Docker image** | Construit l'image Docker taguée `ghassenellili123/error-budget-calculator:1.0.${BUILD_NUMBER}` uniquement si `currentBuild.currentResult == 'SUCCESS'`. | Garantit qu'aucune image n'est construite si un test est en échec (build jaune) et interdit l'usage du tag ambigu `latest`. |
| **5. Security scan (Trivy)** *(Bonus)* | Analyse l'image Docker locale avec **Aqua Trivy** (`--exit-code 1 --severity CRITICAL`) en utilisant le volume de cache `trivy-cache`. | Bloque immédiatement le pipeline avant le push sur Docker Hub si une vulnérabilité critique (CVE) est présente dans l'image. |
| **6. Push** | Authentifie Jenkins auprès de Docker Hub via `withCredentials` (`dockerhub-token` Read & Write) et pousse l'image dans un bloc `retry(3)`. | Publie l'artefact immuable dans un registre distant tout en tolérant les micro-coupures réseau grâce aux 3 tentatives automatiques. |
| **7. Staging :8081** | Déploie le conteneur sur le port `8081`, vérifie que `GET /health` répond `OK`, puis exécute un smoke test sur `/slo/downtime?slo=99.9&days=30` en vérifiant la réponse exacte (`43.2`). | Valide que le conteneur réel démarre et répond correctement aux requêtes HTTP avant de solliciter une validation humaine. |
| **8. Production :8082** | Si `DEPLOY_ENV == 'production'`, met le pipeline en pause avec une étape `input` d'approbation manuelle, puis déploie **exactement la même image** sur le port `8082`. | Implémente le contrôle humain final (*Continuous Delivery*) et garantit que l'image testée en staging est identique à celle mise en production. |
| **Post Actions (`mail` & `cleanWs()`)** | Envoie un e-mail via **Mailpit** contenant la version `v1.0.${BUILD_NUMBER}` dans l'objet (succès, instable ou échec), puis nettoie l'espace de travail avec `cleanWs()`. | Informe immédiatement l'équipe SRE de l'état de la livraison et évite la saturation du disque du serveur Jenkins. |

---

## 3. Fonctionnalités Bonus Implémentées

Nous avons implémenté **4 fonctionnalités bonus** de la Section 5 :

1. **Security scan avec Trivy (Bonus 1)** :
   - *Problème résolu* : Une image Docker dont le code applicatif passe les tests unitaires peut tout de même contenir des librairies système ou Python présentant des failles de sécurité critiques. En exécutant `aquasec/trivy:latest image --exit-code 1 --severity CRITICAL` avec un volume de cache `trivy-cache` juste avant le stage `Push`, toute faille critique casse le build en rouge et empêche la publication sur Docker Hub.
2. **Timeouts et Retries (Bonus 2)** :
   - *Problème résolu* : Un processus bloqué ou une étape `input` oubliée peut monopoliser un exécuteur Jenkins indéfiniment ; à l'inverse, un timeout réseau passager vers Docker Hub peut faire échouer tout un build valide. L'option globale `options { timeout(time: 15, unit: 'MINUTES') }` protège les ressources Jenkins, et `retry(3)` autour de `docker push` fiabilise la publication réseau.
3. **Health Check complet (Bonus 3)** :
   - *Problème résolu* : Un conteneur Docker peut être à l'état `Up` (`running`) alors que le serveur web interne est planté ou bloqué. L'instruction `HEALTHCHECK` dans le `Dockerfile` interroge périodiquement `http://localhost:8080/health`, et le smoke test de staging vérifie à la fois `/health` (`OK`) et un calcul métier réel sur `/slo/downtime`.
4. **GitHub Actions CI Workflow (Bonus 4 — `.github/workflows/ci.yml`)** :
   - *Comparaison Jenkinsfile vs GitHub Actions* :
     - **Hébergement & Exécution** : GitHub Actions est *SaaS / cloud-managed* (`runs-on: ubuntu-latest`) et se déclenche nativement sur chaque `push` et `pull_request` sans serveur à maintenir, tandis que **Jenkins** est *self-hosted* (ayant accès au démon Docker local pour construire, scanner et déployer les conteneurs sur les ports `8081` et `8082`).
     - **Syntaxe & Écosystème** : GitHub Actions utilise du **YAML** déclaratif avec des actions réutilisables (`actions/checkout@v4`, `actions/setup-python@v5`), alors que le `Jenkinsfile` utilise un DSL **Groovy** déclaratif permettant une orchestration fine des étapes `parallel`, `when`, `input` (approbation humaine) et `junit` (état jaune `UNSTABLE`).

---

## 4. Trois problèmes rencontrés et comment nous les avons résolus

### Problème 1 : Le build passait au rouge (`FAILURE`) au lieu de jaune (`UNSTABLE`) lorsqu'un test échouait
- **Cause** : Par défaut dans Jenkins, lorsque `pytest` retourne un code de sortie différent de `0` (test en échec), l'étape `sh` / `bat` échoue immédiatement et marque le stage en `FAILURE` (rouge) avant même que le plugin `junit` ne puisse analyser le rapport XML.
- **Solution** : Nous avons ajouté `|| exit /b 0` (sous Windows) et `|| true` (sous Linux) à la commande `python -m pytest ... --junitxml=...`, et placé `junit 'build/test-results/*.xml'` dans le bloc `post { always { ... } }` du stage `Tests`. Ainsi, c'est le plugin `junit` qui évalue les fichiers XML et passe proprement le build à l'état **jaune (`UNSTABLE`)** en cas de test cassé, tandis que la condition `when { expression { currentBuild.currentResult == 'SUCCESS' } }` bloque la construction de l'image Docker, le scan Trivy et le Push.

### Problème 2 : Échec de `docker push` sur Windows à cause de `credsStore: desktop` et des permissions du token Docker Hub
- **Cause** : Sur Windows, le fichier global `.docker/config.json` utilise `"credsStore": "desktop"`. Or, le service Jenkins s'exécute sous un compte système sans accès au trousseau graphique de la session utilisateur, ce qui empêchait `docker login` d'enregistrer le token. De plus, un token Docker Hub créé par défaut en *Read-only* refusait le push avec l'erreur `access token has insufficient scopes`.
- **Solution** : Nous avons isolé la configuration Docker du build dans un répertoire temporaire propre au workspace (`$WORKSPACE/.docker-cfg/config.json`) et généré un Personal Access Token Docker Hub avec les droits **`Read & Write`** stocké dans Jenkins Credentials (`dockerhub-token`).

### Problème 3 : Conflit de port (`port is already allocated`) et erreur `ModuleNotFoundError: No module named 'app'`
- **Cause** : Lors de l'exécution de `pytest` en CI, le dossier racine n'était pas dans le `PYTHONPATH`, provoquant `ModuleNotFoundError: No module named 'app'`. Par ailleurs, d'anciens conteneurs occupaient déjà le port `8081` lors du déploiement.
- **Solution** : Nous avons ajouté un fichier `pytest.ini` avec `pythonpath = .` (et utilisé `python -m pytest`), et ajouté un nettoyage automatique des conteneurs occupant le port cible (`docker ps -q --filter "publish=8081"`) avant chaque déploiement.

---

## 5. Preuves d'exécution (Captures d'écran)

### A. Build Jaune (`UNSTABLE`) lorsqu'un test échoue : les stages Docker, Trivy et Push sont ignorés (*skipped*)
![Test Results & Yellow Run — Stages Docker ignorés](screenshots/02-test-results-and-yellow-run.png)

### B. Dépôt Docker Hub `ghassenellili123/error-budget-calculator` mis à jour après le stage `Push`
![Docker Hub Repository](screenshots/03-dockerhub-tags.png)
