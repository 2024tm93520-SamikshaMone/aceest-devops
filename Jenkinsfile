pipeline {
    agent any

    environment {
        IMAGE_NAME = 'aceest-fitness'
        IMAGE_TAG  = 'latest'
    }

    stages {

        stage('Checkout') {
            steps {
                echo '--- Pulling latest code from GitHub ---'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '--- Installing Python dependencies ---'
                sh '''
                    python3 -m pip install --upgrade pip
                    pip3 install -r requirements.txt
                    pip3 install flake8
                '''
            }
        }

        stage('Lint') {
            steps {
                echo '--- Running flake8 to check for syntax errors ---'
                sh '''
                    flake8 app.py --count --select=E9,F63,F7,F82 --show-source --statistics
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo '--- Running pytest unit tests ---'
                sh 'python3 -m pytest tests/ -v --tb=short'
            }
        }

        stage('Docker Build') {
            steps {
                echo '--- Building Docker image ---'
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Docker Test') {
            steps {
                echo '--- Running tests inside Docker container ---'
                sh """
                    docker run --rm \
                        --workdir /app \
                        -e DB_PATH=/tmp/aceest_test.db \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        python -m pytest tests/ -v --tb=short
                """
            }
        }

    }

    post {
        success {
            echo 'Pipeline passed - build is healthy.'
        }
        failure {
            echo 'Pipeline failed - check the stage logs above.'
        }
        always {
            echo 'Pipeline finished.'
        }
    }
}
