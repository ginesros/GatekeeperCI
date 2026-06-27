@Library('jenkins-gatekeeper@main') _

pipeline {
    agent any
    
    environment {
        SCANNER_HOME = tool 'sonar-scanner'
        
        // AI Provider configuration
        LLM_MODEL = 'qwen2.5-coder:7b'
        OLLAMA_URL = 'http://172.17.0.13:11434/api/generate'
        
        // Directory to store reports
        REPORTS_DIR = 'reports'
    }
    
    stages {

        stage('Checkout') {
            steps {
                echo 'Get source code...'
                git branch: 'example', url: 'https://github.com/ginesros/GatekeeperCI.git'
            }
        }

        stage('Initialize') {
            steps {
                sh "mkdir -p ${REPORTS_DIR}"
                echo "Starting Jenkins AI-Powered DevSecOps & FinOps Gatekeeper pipeline"
            }
        }

        stage('Security Scanners') {
            steps {
                echo 'Starting Security Scanners...'
                withSonarQubeEnv('sonar-local') {
                    sh """
                    ${SCANNER_HOME}/bin/sonar-scanner \
                      -Dsonar.projectKey=my-infra \
                      -Dsonar.projectName="My Infra" \
                      -Dsonar.sources=.
                    """
                    
                    // Fetch SonarQube issues via API and save to REPORTS_DIR
                    // Assuming SONAR_HOST_URL and SONAR_TOKEN are provided by withSonarQubeEnv
                    sh """
                    echo "Extracting SonarQube report..."
                    curl -s -u "\${SONAR_TOKEN}:" "\${SONAR_HOST_URL}/api/issues/search?componentKeys=my-infra&ps=500" > ${REPORTS_DIR}/sonarqube.json || echo "Failed to fetch SonarQube report"
                    """
                }
            }
        }
        
        /*stage('Static Analysis (Ephemeral Containers)') {
            when {
                changeRequest() // Only run on Pull Requests
            } 
            agent {
                docker { image 'aquasec/tfsec:latest' }
            }
            steps {
                // Run tfsec in a Docker container
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    script {
                        sh "tfsec . -f json > ${REPORTS_DIR}/tfsec.json || true"
                    }
                }
                
                // Run checkov in a Docker container
                 catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    sh """
                        docker run --rm -t -v \$(pwd):/tf bridgecrew/checkov -d /tf -o json > ${REPORTS_DIR}/checkov.json || true
                    """
                } 
                
                // Note: Trivy and Infracost can be added here following the same pattern
            }
        }*/
        
        stage('AI Security Review') {
            steps {
                script {
                    // Extract scripts from Jenkins Shared Library to the workspace
                    def pyScript = libraryResource 'ai_bridge/gatekeeper_ai.py'
                    def reqFile = libraryResource 'ai_bridge/requirements.txt'
                    
                    writeFile file: 'gatekeeper_ai.py', text: pyScript
                    writeFile file: 'requirements.txt', text: reqFile
                    
                    sh """
                        echo "Setting up Python virtual environment..."
                        # Create venv assuming python3 and python3-venv are installed on the Jenkins host
                        python3 -m venv venv
                        
                        echo "Activating venv and installing dependencies..."
                        . venv/bin/activate
                        pip install -r requirements.txt
                        
                        echo "Running AI Bridge script..."
                        python gatekeeper_ai.py
                    """
                }
            }
        }
    }
    
    /* post {
        always {
            // Notify via Telegram using the custom shared library
            script {
                // Obtener el estado del Quality Gate si está disponible
                def sonarStatus = env.SONAR_QUALITY_GATE_STATUS ?: 'N/A'
                
                def statusMessage = "<b>Jenkins-Gatekeeper Pipeline</b>\n" +
                                    "Job: ${env.JOB_NAME} #${env.BUILD_NUMBER}\n" +
                                    "Status: <b>${currentBuild.currentResult}</b>\n" +
                                    "SonarQube Quality Gate: <b>${sonarStatus}</b>\n" +
                                    "URL: ${env.BUILD_URL}"
                                    
                notifyTelegram(
                    botTokenCredentialsId: 'telegram-bot-token',
                    chatId: '-1001234567890', // Replace with your actual Chat ID or use env var
                    message: statusMessage
                )
            }
        }
        cleanup {
            // Clean up workspace
            cleanWs()
        }
    } */
}
