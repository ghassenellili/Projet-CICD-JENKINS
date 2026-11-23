# Captures d'écran du projet (`screenshots/`)

Ce dossier rassemble toutes les captures d'écran de notre pipeline CI/CD (**Ghassen Ellili — Partie CI** & **Mohamed Amine Zalila — Partie CD**) conformément à la **Section 6 (What you hand in)** du sujet PDF :

1. **`01-blue-ocean-parallel.png`** : **Blue Ocean** montrant un build vert (`SUCCESS`) avec les deux stages `Unit tests` et `HTTP tests` exécutés en parallèle, jusqu'au déploiement en production.
2. **`02-test-results-and-yellow-run.png`** : **Test Result** d'un run et un **build jaune (`UNSTABLE`)** montrant que les stages Docker (`Docker image`, `Security scan (Trivy)`, `Push`, `Deploy to staging`, `Deploy to production`) sont automatiquement ignorés (*skipped*).
3. **`03-dockerhub-tags.png`** : Dépôt **Docker Hub** (`ghassenellili123/error-budget-calculator`) mis à jour automatiquement par Jenkins (tags `1.0.N`, jamais `latest`).
4. **`04-docker-ps-staging-production.png`** : Terminal affichant `docker ps` avec les conteneurs actifs : **`ebc-staging`** (`0.0.0.0:8081->8080/tcp`, `healthy`), **`ebc-prod`** (`0.0.0.0:8082->8080/tcp`, `healthy`), `jenkins-local` (`8080`) et `mailpit` (`8025`).
5. **`05-app-staging-and-production.png`** : L'application répondant côte à côte dans le navigateur sur **Staging** (`http://localhost:8081/slo/downtime?slo=99.9&days=30`) et **Production** (`http://localhost:8082/slo/downtime?slo=99.9&days=30`).
6. **`06-mailpit-email.png`** : L'interface web de **Mailpit** (`http://localhost:8025`) montrant l'e-mail de succès reçu (`error-budget-calculator 1.0.9 deployed (staging)`).
7. **`06-mailpit-failure-email.png`** : L'interface web de **Mailpit** montrant un e-mail d'échec (`FAILURE: error-budget-calculator 1.0.12`) avec le journal `build.log` en pièce jointe.
8. **`07-rollback-stageview.png`** : Vue **Stage View** du second job Jenkins bonus **`error-budget-calculator-rollback`** (`Jenkinsfile.rollback`).
9. **`07-rollback-console.png`** : **Console Output** du job de rollback montrant l'approbation manuelle par **Mohamed Amine Zalila** et le retour en production de l'image `1.0.8` sur le port `8082`.
10. **`08-pull-requests.png`** : Historique GitHub des **Pull Requests** fermées/fusionnées montrant le travail en binôme entre **Ghassen Ellili** (`ghassen/...`) et **Mohamed Amine Zalila** (`amine/...`).
