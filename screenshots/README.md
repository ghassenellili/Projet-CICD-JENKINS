# Captures d'écran du projet (Dossier `screenshots/`)

Conformément à la **Section 6 (What you hand in)** du sujet PDF, placez dans ce dossier `screenshots/` les 6 captures d'écran suivantes avant de générer le PDF final de votre rapport (`report.pdf`) :

1. `01-blue-ocean-parallel.png` : **Blue Ocean** montrant un build vert (`SUCCESS`) avec les deux stages `Unit tests` et `HTTP tests` exécutés en parallèle.
2. `02-test-results-and-yellow-run.png` : **Test Result** d'un run, ainsi qu'un **build jaune (`UNSTABLE`)** montrant que les stages Docker (`Docker image`, `Security scan`, `Push`, `Staging`, `Production`) ont bien été ignorés (*skipped*).
3. `03-dockerhub-tags.png` : L'onglet **Tags** de votre dépôt Docker Hub (`ghassenellili/error-budget-calculator`) montrant les tags `1.0.1`, `1.0.2`, etc. (et aucun tag `latest`).
4. `04-docker-ps-ports.png` : Le terminal affichant la commande `docker ps` avec les deux conteneurs actifs : **staging** (`0.0.0.0:8081->8080/tcp`) et **production** (`0.0.0.0:8082->8080/tcp`).
5. `05-browser-staging-prod.png` : L'application ouverte dans le navigateur sur `http://localhost:8081` (Staging) et `http://localhost:8082` (Production).
6. `06-mailpit-notification.png` : L'interface web de **Mailpit** montrant l'e-mail reçu avec le numéro de version `v1.0.N` dans l'objet (`[SUCCESS] error-budget-calculator v1.0.N`).
