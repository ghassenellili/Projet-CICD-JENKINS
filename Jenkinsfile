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
            description: 'Target deployment environment'
        )
        string(
            name: 'SLO_TARGET',
            defaultValue: '99.9',
            description: 'Default SLO target percentage'
        )
    }

    environment {
        APP_NAME      = 'error-budget-calculator'
        APP_VERSION   = "1.0.${BUILD_NUMBER}"
        DOCKER_REPO   = 'ghassenellili123/error-budget-calculator'
        IMAGE_TAG     = "${DOCKER_REPO}:${APP_VERSION}"
    }

    stages {
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
        // Compatible with both collaborators on ghassenellili123/error-budget-calculator (ghassenellili123 & mohamedaminezalila)
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
    }
}
