# Guide Complet pour Mohamed Amine Zalila (`mohamedaminezalila`) — Lancer la CI & Ajouter la Partie CD (Features 9 à 12)

Bienvenue **Mohamed Amine** ! Ce guide explique étape par étape comment :
1. Faire tourner toute la partie **CI (Features 1 à 8)** déjà prête sur ton PC avec ton compte collaborateur Docker Hub **`mohamedaminezalila`**.
2. Créer ta branche **`amine/cd-pipeline`** pour ajouter ta partie **Continuous Delivery (Features 9 à 12 : Staging `:8081`, Production `:8082` avec approbation, Email Mailpit et `cleanWs()`)** et finaliser le projet CI/CD !

---

## Étape 1 : Configurer Git et Cloner le dépôt (avec ton propre compte GitHub)

Conformément à la Section 2 du PDF (*"Each student commits from their own GitHub account"*), ouvre PowerShell ou Git Bash sur ton PC :

```bash
git clone https://github.com/ghassenellili/Projet-CICD-JENKINS.git
cd Projet-CICD-JENKINS

# Configurer ton nom et ton email GitHub personnel
git config user.name "mohamedaminezalila"
git config user.email "TON_EMAIL_GITHUB@horizon-university.tn"

# Créer ta branche nominative (Section 2 : jamais de commit direct sur main)
git checkout -b amine/cd-pipeline
```

---

## Étape 2 : Configurer ton Token Docker Hub (`mohamedaminezalila`) dans ton Jenkins

Comme **Ghassen (`ghassenellili123`)** t'a ajouté comme **Collaborator** sur le dépôt Docker Hub `ghassenellili123/error-budget-calculator`, tu peux pousser directement sur ce dépôt avec ton propre compte Docker Hub **`mohamedaminezalila`** !

1. Connecte-toi sur [Docker Hub](https://app.docker.com/settings/personal-access-tokens) avec ton compte **`mohamedaminezalila`** (et accepte l'invitation de collaborateur sur `ghassenellili123/error-budget-calculator` si demandé).
2. Clique sur **Generate new token** :
   - **Description** : `jenkins-amine`
   - **Access permissions** : **`Read, Write, Delete`** (ou **`Read & Write`**)
   - Copie le token généré (`dckr_pat_...`).
3. Dans ton **Jenkins** (`Manage Jenkins` $\rightarrow$ `Credentials` $\rightarrow$ `System` $\rightarrow$ `Global credentials` $\rightarrow$ `Add Credentials`) :
   - **Kind** : `Username with password`
   - **Username** : `mohamedaminezalila`
   - **Password** : colle ton token `dckr_pat_...`
   - **ID** : `dockerhub-token` *(exactement cet ID)*
   - Clique sur **Create**.

*(Grâce à `withCredentials` dans le `Jenkinsfile`, Jenkins se connectera en tant que `mohamedaminezalila` et poussera l'image `ghassenellili123/error-budget-calculator:1.0.${BUILD_NUMBER}` !)*

---

## Étape 3 : Démarrer Mailpit et Configurer le SMTP dans Jenkins (Feature 11)

1. Lance le conteneur **Mailpit** dans Docker :
   ```powershell
   docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit
   ```
   *(Interface web de réception des e-mails : `http://localhost:8025`)*

2. Dans **Jenkins** (`Manage Jenkins` $\rightarrow$ `System` $\rightarrow$ tout en bas dans **E-mail Notification**) :
   - **SMTP server** : `localhost` (si Jenkins est sur Windows) ou `host.docker.internal` (si Jenkins est dans un conteneur Docker)
   - Clique sur **Advanced...** $\rightarrow$ **SMTP Port** : `1025`
   - Clique sur **Save**.

---

## Étape 4 : Compléter le `Jenkinsfile` avec ta Partie CD (Features 9 à 12)

Pour que l'enseignant voie clairement tes commits dans le `Jenkinsfile` sur GitHub (`Insights > Contributors` et dans ta Pull Request), remplace le contenu de `Jenkinsfile` par la version complète **CI (1–8) + CD (9–12)** ci-dessous :

```groovy
pipeline {
    agent any

    // Bonus: Timeouts and retries (pipeline timeout)
    options {
        timeout(time: 15, unit: 'MINUTES')
    }

    // Feature 5: Parameters (DEPLOY_ENV + one more parameter of your choice)
    parameters {
        choice(
            name: 'DEPLOY_ENV',
            choices: ['staging', 'production'],
            description: 'Target deployment environment (staging on 8081, or staging + production on 8082)'
        )
        string(
            name: 'SLO_TARGET',
            defaultValue: '99.9',
            description: 'Default SLO target percentage tested during the staging smoke test'
        )
    }

    environment {
        APP_NAME      = 'error-budget-calculator'
        APP_VERSION   = "1.0.${BUILD_NUMBER}"
        DOCKER_REPO   = 'ghassenellili123/error-budget-calculator'
        IMAGE_TAG     = "${DOCKER_REPO}:${APP_VERSION}"
        STAGING_PORT  = '8081'
        PROD_PORT     = '8082'
        NOTIFY_EMAIL  = 'team-sre@horizon.local'
    }

    stages {
        // ==================== PARTIE CI (FEATURES 1 TO 8 - GHASSEN) ====================

        // Feature 2: Build (create build folders and install dependencies)
        stage('Build') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv
                            . .venv/bin/activate
                            pip install --upgrade pip
                            pip install -r requirements.txt
                            mkdir -p build/test-results build/dist
                            echo "${APP_NAME}-${APP_VERSION}" > build/dist/version.txt
                            tar -czf build/dist/${APP_NAME}-${APP_VERSION}.tar.gz app/ requirements.txt Dockerfile
                        '''
                    } else {
                        bat '''
                            python -m venv .venv
                            call .venv\\Scripts\\activate.bat
                            python -m pip install --upgrade pip
                            pip install -r requirements.txt
                            if not exist build\\test-results mkdir build\\test-results
                            if not exist build\\dist mkdir build\\dist
                            echo %APP_NAME%-%APP_VERSION% > build\\dist\\version.txt
                            tar -czf build\\dist\\%APP_NAME%-%APP_VERSION%.tar.gz app requirements.txt Dockerfile
                        '''
                    }
                }
            }
        }

        // Feature 3: Tests in parallel (>= 5 unit tests and >= 2 HTTP tests)
        stage('Tests') {
            parallel {
                stage('Unit tests') {
                    steps {
                        script {
                            if (isUnix()) {
                                sh '''
                                    . .venv/bin/activate
                                    python -m pytest tests/test_unit.py --junitxml=build/test-results/unit-report.xml || true
                                '''
                            } else {
                                bat '''
                                    call .venv\\Scripts\\activate.bat
                                    python -m pytest tests/test_unit.py --junitxml=build/test-results/unit-report.xml || exit /b 0
                                '''
                            }
                        }
                    }
                }
                stage('HTTP tests') {
                    steps {
                        script {
                            if (isUnix()) {
                                sh '''
                                    . .venv/bin/activate
                                    python -m pytest tests/test_http.py --junitxml=build/test-results/http-report.xml || true
                                '''
                            } else {
                                bat '''
                                    call .venv\\Scripts\\activate.bat
                                    python -m pytest tests/test_http.py --junitxml=build/test-results/http-report.xml || exit /b 0
                                '''
                            }
                        }
                    }
                }
            }
            post {
                always {
                    // Feature 4: Test reports (junit publishes XML reports; failing test marks build UNSTABLE/yellow)
                    junit 'build/test-results/*.xml'
                }
            }
        }

        // Feature 6: Artifacts (archive build output and test reports with fingerprint)
        stage('Package') {
            steps {
                archiveArtifacts artifacts: 'build/dist/*.tar.gz, build/dist/version.txt, build/test-results/*.xml',
                                 fingerprint: true
            }
        }

        // Feature 7: Docker image (built ONLY if the build is green; tag = 1.0.${BUILD_NUMBER}, never latest)
        stage('Docker image') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                script {
                    if (isUnix()) {
                        sh "DOCKER_BUILDKIT=0 docker build --pull=false -t ${IMAGE_TAG} ."
                    } else {
                        bat """
                            set DOCKER_BUILDKIT=0
                            docker build --pull=false -t ${IMAGE_TAG} .
                        """
                    }
                }
            }
        }

        // Bonus 1: Security scan with Trivy before push (CRITICAL flaw stops the pipeline, uses cache volume)
        stage('Security scan (Trivy)') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                script {
                    if (isUnix()) {
                        sh """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                -v trivy-cache:/root/.cache/ \
                                aquasec/trivy:latest image \
                                --exit-code 1 \
                                --severity CRITICAL \
                                ${IMAGE_TAG}
                        """
                    } else {
                        bat """
                            docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ aquasec/trivy:latest image --exit-code 1 --severity CRITICAL ${IMAGE_TAG}
                        """
                    }
                }
            }
        }

        // Feature 8 + Bonus 2: Push to Docker Hub (withCredentials + Read & Write token + retry(3))
        stage('Push') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-token',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_TOKEN'
                )]) {
                    retry(3) {
                        script {
                            if (isUnix()) {
                                sh '''
                                    set -e
                                    export DOCKER_CONFIG="${WORKSPACE}/.docker-cfg"
                                    mkdir -p "$DOCKER_CONFIG"
                                    echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
                                    docker push "${IMAGE_TAG}"
                                    docker logout
                                    rm -rf "$DOCKER_CONFIG"
                                '''
                            } else {
                                powershell '''
                                    $ErrorActionPreference = 'Continue'
                                    $cfgDir = Join-Path $env:WORKSPACE ".docker-cfg"
                                    New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
                                    Set-Content -Path (Join-Path $cfgDir "config.json") -Value "{}" -Encoding Ascii

                                    $user = $env:DOCKER_USER.Trim()
                                    $token = $env:DOCKER_TOKEN.Trim()
                                    Write-Host "Logging into Docker Hub as collaborator '$user' to push $env:IMAGE_TAG..."

                                    docker --config "$cfgDir" login -u "$user" -p "$token" 2>&1 | ForEach-Object { Write-Host $_ }
                                    if ($LASTEXITCODE -ne 0) { throw "Docker login failed for user '$user' (exit code $LASTEXITCODE)" }

                                    docker --config "$cfgDir" push $env:IMAGE_TAG 2>&1 | ForEach-Object { Write-Host $_ }
                                    if ($LASTEXITCODE -ne 0) { throw "Docker push failed (exit code $LASTEXITCODE)" }

                                    docker --config "$cfgDir" logout 2>&1 | Out-Null
                                    Remove-Item -Recurse -Force $cfgDir -ErrorAction SilentlyContinue
                                '''
                            }
                        }
                    }
                }
            }
        }

        // ==================== PARTIE CD (FEATURES 9 TO 12 - MOHAMED AMINE ZALILA) ====================

        // Feature 9 + Bonus 3: Staging (:8081) + smoke test (/health and /slo/downtime exact response check)
        stage('Staging :8081') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                script {
                    if (isUnix()) {
                        sh """
                            OLD_IDS=\$(docker ps -q --filter "publish=${STAGING_PORT}")
                            if [ -n "\$OLD_IDS" ]; then docker rm -f \$OLD_IDS || true; fi
                            docker rm -f ${APP_NAME}-staging || true
                            docker run -d --name ${APP_NAME}-staging -p ${STAGING_PORT}:8080 ${IMAGE_TAG}
                            sleep 3

                            HEALTH_OUT=\$(curl -fsS http://localhost:${STAGING_PORT}/health)
                            test "\$HEALTH_OUT" = "OK"

                            SMOKE_OUT=\$(curl -fsS "http://localhost:${STAGING_PORT}/slo/downtime?slo=${params.SLO_TARGET}&days=30")
                            echo "Smoke test output: \$SMOKE_OUT"
                            echo "\$SMOKE_OUT" | grep -q '"allowed_downtime_minutes":43.2'
                        """
                    } else {
                        powershell """
                            \$ErrorActionPreference = 'Continue'
                            \$oldIds = docker ps -q --filter "publish=${STAGING_PORT}"
                            if (\$oldIds) { docker rm -f \$oldIds 2>&1 | Out-Null }
                            docker rm -f ${APP_NAME}-staging 2>&1 | Out-Null
                            \$ErrorActionPreference = 'Stop'

                            docker run -d --name ${APP_NAME}-staging -p ${STAGING_PORT}:8080 ${IMAGE_TAG}
                            if (\$LASTEXITCODE -ne 0) { throw "Failed to start staging container on port ${STAGING_PORT}" }
                            Start-Sleep -Seconds 3

                            \$health = (Invoke-WebRequest -Uri "http://localhost:${STAGING_PORT}/health" -UseBasicParsing).Content.Trim()
                            if (\$health -ne "OK") { throw "Health check failed: \$health" }

                            \$smoke = Invoke-RestMethod -Uri "http://localhost:${STAGING_PORT}/slo/downtime?slo=${params.SLO_TARGET}&days=30"
                            Write-Host "Smoke test output: \$(\$smoke | ConvertTo-Json -Compress)"
                            if (\$smoke.allowed_downtime_minutes -ne 43.2) { throw "Smoke test calculation mismatch!" }
                        """
                    }
                }
            }
        }

        // Feature 10: Production with approval (input step, then same image on port 8082, only if DEPLOY_ENV = production)
        stage('Production :8082') {
            when {
                allOf {
                    expression { currentBuild.currentResult == 'SUCCESS' }
                    expression { params.DEPLOY_ENV == 'production' }
                }
            }
            steps {
                input message: "Approve deployment of ${IMAGE_TAG} to Production (:8082)?", ok: 'Deploy to Production'
                script {
                    if (isUnix()) {
                        sh """
                            OLD_IDS=\$(docker ps -q --filter "publish=${PROD_PORT}")
                            if [ -n "\$OLD_IDS" ]; then docker rm -f \$OLD_IDS || true; fi
                            docker rm -f ${APP_NAME}-production || true
                            docker run -d --name ${APP_NAME}-production -p ${PROD_PORT}:8080 ${IMAGE_TAG}
                            sleep 3
                            PROD_HEALTH=\$(curl -fsS http://localhost:${PROD_PORT}/health)
                            test "\$PROD_HEALTH" = "OK"
                        """
                    } else {
                        powershell """
                            \$ErrorActionPreference = 'Continue'
                            \$oldIds = docker ps -q --filter "publish=${PROD_PORT}"
                            if (\$oldIds) { docker rm -f \$oldIds 2>&1 | Out-Null }
                            docker rm -f ${APP_NAME}-production 2>&1 | Out-Null
                            \$ErrorActionPreference = 'Stop'

                            docker run -d --name ${APP_NAME}-production -p ${PROD_PORT}:8080 ${IMAGE_TAG}
                            if (\$LASTEXITCODE -ne 0) { throw "Failed to start production container on port ${PROD_PORT}" }
                            Start-Sleep -Seconds 3
                            \$prodHealth = (Invoke-WebRequest -Uri "http://localhost:${PROD_PORT}/health" -UseBasicParsing).Content.Trim()
                            if (\$prodHealth -ne "OK") { throw "Production health check failed: \$prodHealth" }
                        """
                    }
                }
            }
        }
    }

    // Feature 11 & 12: Email notification (Mailpit) with version in subject + cleanWs() in post { always }
    post {
        success {
            mail to: "${NOTIFY_EMAIL}",
                 subject: "[SUCCESS] ${APP_NAME} v${APP_VERSION} - Pipeline #${BUILD_NUMBER}",
                 body: "Build #${BUILD_NUMBER} (version ${APP_VERSION}) succeeded.\nEnvironment: ${params.DEPLOY_ENV}\nImage: ${IMAGE_TAG}\nDetails: ${BUILD_URL}"
        }
        unstable {
            mail to: "${NOTIFY_EMAIL}",
                 subject: "[UNSTABLE] ${APP_NAME} v${APP_VERSION} - Tests Failed (#${BUILD_NUMBER})",
                 body: "Build #${BUILD_NUMBER} (version ${APP_VERSION}) is UNSTABLE (yellow) due to test failures. Docker build and deployment were skipped.\nDetails: ${BUILD_URL}"
        }
        failure {
            mail to: "${NOTIFY_EMAIL}",
                 subject: "[FAILURE] ${APP_NAME} v${APP_VERSION} - Pipeline #${BUILD_NUMBER}",
                 body: "Build #${BUILD_NUMBER} (version ${APP_VERSION}) failed.\nEnvironment: ${params.DEPLOY_ENV}\nDetails: ${BUILD_URL}"
        }
        always {
            cleanWs()
        }
    }
}
```

---

## Étape 5 : Pousser ta branche `amine/cd-pipeline` et ouvrir une Pull Request

```bash
git add Jenkinsfile
git commit -m "Add CD stages (Staging 8081, Production 8082 with approval, Mailpit notification and cleanWs)"
git push -u origin amine/cd-pipeline
```

1. Sur GitHub (`https://github.com/ghassenellili/Projet-CICD-JENKINS/pulls`), ouvre une **Pull Request** de `amine/cd-pipeline` vers `main`.
2. **Ghassen** la relit, laisse un commentaire d'approbation (*Approve*) et la fusionne sur `main` !
3. Lance le build en choisissant `DEPLOY_ENV = production` dans Jenkins et prends les 3 dernières captures d'écran dans `screenshots/` :
   - `04-docker-ps-ports.png` : `docker ps` montrant Staging (`8081`) et Production (`8082`).
   - `05-browser-staging-prod.png` : `http://localhost:8081` et `http://localhost:8082` dans le navigateur.
   - `06-mailpit-notification.png` : l'e-mail reçu dans Mailpit (`http://localhost:8025`).
