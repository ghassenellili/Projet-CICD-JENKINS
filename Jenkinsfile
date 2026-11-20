pipeline {
    agent any

    // Bonus: Timeouts and retries (pipeline timeout)
    options {
        timeout(time: 15, unit: 'MINUTES')
    }

    // Feature 5: Parameters (DEPLOY_ENV + a second parameter of choice)
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
        DOCKER_REPO   = 'ghassenellili/error-budget-calculator'
        IMAGE_TAG     = "${DOCKER_REPO}:${APP_VERSION}"
        STAGING_PORT  = '8081'
        PROD_PORT     = '8082'
        NOTIFY_EMAIL  = 'team-sre@horizon.local'
    }

    stages {
        // Feature 2: Build (create build folders and install dependencies)
        stage('Build') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    mkdir -p build/test-results build/dist
                    echo "${APP_NAME}-${APP_VERSION}" > build/dist/version.txt
                    tar -czf build/dist/${APP_NAME}-${APP_VERSION}.tar.gz app/ requirements.txt Dockerfile
                '''
            }
        }

        // Feature 3: Tests in parallel (>= 5 unit tests and >= 2 HTTP tests)
        stage('Tests') {
            parallel {
                stage('Unit tests') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            pytest tests/test_unit.py --junitxml=build/test-results/unit-report.xml || true
                        '''
                    }
                }
                stage('HTTP tests') {
                    steps {
                        sh '''
                            . .venv/bin/activate
                            pytest tests/test_http.py --junitxml=build/test-results/http-report.xml || true
                        '''
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
                sh "docker build -t ${IMAGE_TAG} ."
            }
        }

        // Bonus 1: Security scan with Trivy before push (CRITICAL flaw stops the pipeline, uses cache volume)
        stage('Security scan (Trivy)') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                sh """
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v trivy-cache:/root/.cache/ \
                        aquasec/trivy:latest image \
                        --exit-code 1 \
                        --severity CRITICAL \
                        ${IMAGE_TAG}
                """
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
                        sh '''
                            echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
                            docker push "${IMAGE_TAG}"
                            docker logout
                        '''
                    }
                }
            }
        }

        // Feature 9 + Bonus 3: Staging (:8081) + smoke test (/health and /slo/downtime exact response check)
        stage('Staging :8081') {
            when {
                expression { currentBuild.currentResult == 'SUCCESS' }
            }
            steps {
                sh """
                    docker rm -f ${APP_NAME}-staging || true
                    docker run -d --name ${APP_NAME}-staging -p ${STAGING_PORT}:8080 ${IMAGE_TAG}
                    sleep 3

                    # Verify /health returns exact 'OK'
                    HEALTH_OUT=\$(curl -fsS http://localhost:${STAGING_PORT}/health)
                    test "\$HEALTH_OUT" = "OK"

                    # Smoke test: call /slo/downtime and verify exact calculation result
                    SMOKE_OUT=\$(curl -fsS "http://localhost:${STAGING_PORT}/slo/downtime?slo=${params.SLO_TARGET}&days=30")
                    echo "Smoke test output: \$SMOKE_OUT"
                    echo "\$SMOKE_OUT" | grep -q '"allowed_downtime_minutes":43.2'
                """
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
                sh """
                    docker rm -f ${APP_NAME}-production || true
                    docker run -d --name ${APP_NAME}-production -p ${PROD_PORT}:8080 ${IMAGE_TAG}
                    sleep 3
                    PROD_HEALTH=\$(curl -fsS http://localhost:${PROD_PORT}/health)
                    test "\$PROD_HEALTH" = "OK"
                """
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
