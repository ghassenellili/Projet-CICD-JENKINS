# Rapport de Projet Final — CI/CD with Jenkins & Docker
## Application : SRE Error Budget Calculator

- **Établissement** : Horizon School of Digital Technologies
- **Binôme** : Étudiant 1 (Ghassen) & Étudiant 2 (Binôme)
- **Dépôt GitHub** : `https://github.com/ghassenellili/Projet-CICD-JENKINS`
- **Dépôt Docker Hub** : `https://hub.docker.com/r/ghassenellili123/error-budget-calculator`

---

## 1. Présentation de l'application et du scénario métier

L'application **SRE Error Budget Calculator** est un microservice web et API REST développé en **Python (Flask)**. Dans une organisation DevOps/SRE, la décision d'autoriser ou de bloquer une mise en production repose sur le **Budget d'Erreur (Error Budget)** défini par le *Service Level Objective (SLO)* (par exemple `99.9%` de disponibilité sur 30 jours, soit `43.2 minutes` d'indisponibilité tolérée).

Notre application expose :
- `GET /health` : retourne `OK` (HTTP 200), utilisé par le `HEALTHCHECK` Docker et le smoke test Jenkins.
- `GET /slo/downtime?slo=99.9&days=30` : calcule le temps d'indisponibilité maximal autorisé en minutes et secondes.
- `POST /slo/budget` : calcule le nombre d'erreurs HTTP tolérées, le budget restant et le pourcentage consommé.
- `POST /slo/burn-rate` : calcule la vitesse de consommation du budget (*Burn Rate*) et détermine le niveau d'alerte (`NORMAL`, `WARNING`, `HIGH`, `CRITICAL`).
- `POST /slo/release-check` : agit comme une barrière de déploiement automatique (*Release Gate*) en retournant `GO`, `CAUTION` ou `NO-GO`.

---

## 2. Vue d'ensemble du Pipeline Jenkins (Blue Ocean)

>Insérer ici la capture : `![Pipeline Blue Ocean](screenshots/01-blue-ocean-parallel.png)`

### Explication détaillée de chaque Stage (et pourquoi il est nécessaire)

| Stage | Rôle technique | Pourquoi ce stage est indispensable |
| :--- | :--- | :--- |
| **1. Build** | Crée un environnement virtuel isolé (`.venv`), installe les dépendances depuis `requirements.txt` et prépare l'archive de distribution `build/dist/*.tar.gz`. | Garantit que l'application et ses dépendances s'installent proprement avant de lancer les tests. |
| **2. Tests (Parallel : `Unit tests` & `HTTP tests`)** | Exécute simultanément **7 tests unitaires** (`tests/test_unit.py`) et **5 tests HTTP** (`tests/test_http.py`) avec `pytest --junitxml=...`, puis publie les rapports via `junit`. | Le parallélisme réduit le temps de feedback CI. La publication JUnit passe le build en **jaune (`UNSTABLE`)** si un test échoue, empêchant la création d'une image défectueuse. |
| **3. Package (Artifacts)** | Archive le paquet de build et les rapports XML JUnit avec `archiveArtifacts(..., fingerprint: true)`. | Assure la traçabilité complète (empreinte MD5/fingerprint) entre un numéro de build Jenkins et les fichiers produits. |
| **4. Docker image** | Construit l'image Docker taguée `ghassenellili123/error-budget-calculator:1.0.${BUILD_NUMBER}` uniquement si `currentBuild.currentResult == 'SUCCESS'`. | Garantit qu'aucune image n'est construite si un test est en échec (build jaune) et interdit l'usage du tag ambigu `latest`. |
| **5. Security scan (Trivy)** *(Bonus)* | Analyse l'image Docker locale avec **Aqua Trivy** (`--exit-code 1 --severity CRITICAL`) en utilisant le volume de cache `trivy-cache`. | Bloque immédiatement le pipeline avant le push sur Docker Hub si une vulnérabilité critique (CVE) est présente dans l'image. |
| **6. Push** | Authentifie Jenkins auprès de Docker Hub via `withCredentials` (token Read & Write) et pousse l'image dans un bloc `retry(3)`. | Publie l'artefact immuable dans un registre distant tout en tolérant les micro-coupures réseau grâce aux 3 tentatives automatiques. |
| **7. Staging :8081** | Déploie le conteneur sur le port `8081`, vérifie que `GET /health` répond `OK`, puis exécute un smoke test sur `/slo/downtime?slo=99.9&days=30` en vérifiant la réponse exacte (`43.2`). | Valide que le conteneur réel démarre et répond correctement aux requêtes HTTP avant de solliciter une validation humaine. |
| **8. Production :8082** | Si `DEPLOY_ENV == 'production'`, met le pipeline en pause avec une étape `input` d'approbation manuelle, puis déploie **exactement la même image** sur le port `8082`. | Implémente le contrôle humain final (*Continuous Delivery*) et garantit que l'image testée en staging est identique à celle mise en production. |
| **Post Actions (`mail` & `cleanWs()`)** | Envoie un e-mail via **Mailpit** contenant la version `v1.0.${BUILD_NUMBER}` dans l'objet (succès, instable ou échec), puis nettoie l'espace de travail avec `cleanWs()`. | Informe immédiatement l'équipe SRE de l'état de la livraison et évite la saturation du disque du serveur Jenkins. |

---

## 3. Fonctionnalités Bonus Implémentées

Nous avons implémenté **3 fonctionnalités bonus** de la Section 5 :

1. **Security scan avec Trivy (Bonus 1)** :
   - *Problème résolu* : Une image Docker dont le code applicatif passe les tests unitaires peut tout de même contenir des librairies système ou Python présentant des failles de sécurité critiques. En exécutant `aquasec/trivy:latest image --exit-code 1 --severity CRITICAL` avec un volume de cache `trivy-cache` juste avant le stage `Push`, toute faille critique casse le build en rouge et empêche la publication sur Docker Hub.
2. **Timeouts et Retries (Bonus 2)** :
   - *Problème résolu* : Un processus bloqué ou une étape `input` oubliée peut monopoliser un exécuteur Jenkins indéfiniment ; à l'inverse, un timeout réseau passager vers Docker Hub peut faire échouer tout un build valide. L'option globale `options { timeout(time: 15, unit: 'MINUTES') }` protège les ressources Jenkins, et `retry(3)` autour de `docker push` fiabilise la publication réseau.
3. **Health Check complet (Bonus 3)** :
   - *Problème résolu* : Un conteneur Docker peut être à l'état `Up` (`running`) alors que le serveur web interne est planté ou bloqué. L'instruction `HEALTHCHECK` dans le `Dockerfile` interroge périodiquement `http://localhost:8080/health`, et notre smoke test de staging vérifie à la fois `/health` (`OK`) et un calcul métier réel sur `/slo/downtime`.
4. **GitHub Actions CI Workflow (Bonus 4 — `.github/workflows/ci.yml`)** :
   - *Comparaison Jenkinsfile vs GitHub Actions* :
     - **Hébergement & Exécution** : GitHub Actions est *SaaS / cloud-managed* (`runs-on: ubuntu-latest`) et se déclenche nativement sur chaque `push` et `pull_request` sans serveur à maintenir, tandis que **Jenkins** est *self-hosted* (conteneur local ayant accès au socket Docker local pour déployer sur les ports `8081` et `8082`).
     - **Syntaxe & Écosystème** : GitHub Actions utilise du **YAML** déclaratif avec des actions réutilisables (`actions/checkout@v4`, `actions/setup-python@v5`), alors que le `Jenkinsfile` utilise un DSL **Groovy** déclaratif permettant une orchestration fine des étapes `parallel`, `when`, `input` (approbation humaine) et `junit` (état jaune `UNSTABLE`).

---

## 4. Trois problèmes rencontrés et comment nous les avons résolus

### Problème 1 : Le build passait au rouge (`FAILURE`) au lieu de jaune (`UNSTABLE`) lorsqu'un test échouait
- **Cause** : Par défaut dans Jenkins, lorsque `pytest` retourne un code de sortie différent de `0` (test en échec), l'étape `sh` échoue immédiatement et marque le stage en `FAILURE` (rouge) avant même que le plugin `junit` ne puisse analyser le rapport XML.
- **Solution** : Nous avons ajouté `|| true` à la commande `pytest ... --junitxml=... || true` dans les deux branches parallèles, et placé `junit 'build/test-results/*.xml'` dans le bloc `post { always { ... } }` du stage `Tests`. Ainsi, c'est le plugin `junit` qui évalue les fichiers XML et passe proprement le build à l'état **jaune (`UNSTABLE`)** en cas de test cassé, tandis que la condition `when { expression { currentBuild.currentResult == 'SUCCESS' } }` bloque la construction de l'image Docker et le déploiement.

### Problème 2 : Conflit de nom de conteneur et de port lors des redéploiements sur Staging (`8081`) et Production (`8082`)
- **Cause** : À partir du deuxième build Jenkins, la commande `docker run -d --name error-budget-calculator-staging -p 8081:8080 ...` échouait avec l'erreur `Conflict. The container name is already in use` et `Bind for 0.0.0.0:8081 failed: port is already allocated`.
- **Solution** : Avant chaque `docker run`, nous avons ajouté la commande idempotente `docker rm -f ${APP_NAME}-staging || true` (et de même pour `-production`). Cela arrête et supprime proprement le conteneur de la version précédente sans échouer lors du tout premier déploiement.

### Problème 3 : Le smoke test `curl` échouait parfois juste après `docker run -d`
- **Cause** : La commande `docker run -d` rend la main immédiatement dès la création du conteneur, mais l'interpréteur Python/Flask met environ 1 à 2 secondes pour écouter sur le port `8080`. Le `curl` immédiat rencontrait une erreur `Connection refused`.
- **Solution** : Nous avons ajouté une temporisation (`sleep 3`) après `docker run -d`, suivie d'une vérification stricte de `/health` (`test "$HEALTH_OUT" = "OK"`) avant d'exécuter le test fonctionnel sur `/slo/downtime`.

---

## 5. Preuves d'exécution (Captures d'écran)

1. **Résultats des tests JUnit & Run jaune (`UNSTABLE`) sans déploiement** :
   > `![Test Results & Yellow Run](screenshots/02-test-results-and-yellow-run.png)`
2. **Docker Hub — Onglet Tags (`1.0.N`, jamais `latest`)** :
   > `![Docker Hub Tags](screenshots/03-dockerhub-tags.png)`
3. **Conteneurs actifs `docker ps` (Staging `:8081` et Production `:8082`)** :
   > `![Docker PS](screenshots/04-docker-ps-ports.png)`
4. **Application dans le navigateur (Staging et Production)** :
   > `![Browser Staging & Prod](screenshots/05-browser-staging-prod.png)`
5. **Notification E-mail dans Mailpit avec la version dans l'objet** :
   > `![Mailpit Email](screenshots/06-mailpit-notification.png)`
