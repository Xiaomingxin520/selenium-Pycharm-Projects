// 后续接入Jenkins时使用，不影响现有的代码

pipeline {
    agent any
    environment {

        // true=无头跑（CI用），false=弹浏览器（本地调试用）
        HEADLESS = "true"

        // 改成服务器上chromedriver的真实路径
        CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
    }

    stages {
        stage('拉取代码') {
            steps {
                echo '代码由 Jenkins 自动拉取'
            }
        }

        stage('安装依赖') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('执行自动化测试') {
            steps {
                sh 'pytest'
            }
        }
    }

    post {
        always {
            cleanWs()
            allure includeProperties: false, results: [[path: 'reports/allure-results']]
        }
    }
}