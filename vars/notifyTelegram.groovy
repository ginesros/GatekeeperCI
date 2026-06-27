def call(Map config = [:]) {
    // Default parameters or those passed in config
    def botTokenCredentialsId = config.botTokenCredentialsId ?: 'telegram-bot-token'
    def chatId = config.chatId
    def message = config.message

    if (!chatId || !message) {
        error "notifyTelegram: The parameters 'chatId' and 'message' are mandatory."
    }

    // Get the Telegram token from Jenkins credentials
    withCredentials([string(credentialsId: botTokenCredentialsId, variable: 'TELEGRAM_BOT_TOKEN')]) {
        def telegramUrl = "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
        
        // Execute curl to send the message via Telegram API
        sh """
        curl -s -X POST ${telegramUrl} \\
            -d chat_id=${chatId} \\
            -d parse_mode=HTML \\
            -d text="${message}"
        """
    }
}
