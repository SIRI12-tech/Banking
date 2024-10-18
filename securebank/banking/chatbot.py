def get_bot_response(message):
    message = message.lower()
    if "hello" in message or "hi" in message:
        return "Hello! How can I assist you today?"
    elif "balance" in message:
        return "To check your balance, please go to the Account Summary page."
    elif "transfer" in message:
        return "You can make a transfer by clicking on the 'Transfer' option in the Quick Actions menu."
    elif "loan" in message:
        return "For information about loans, please visit our Loans page or speak with a customer service representative."
    elif "thank" in message:
        return "You're welcome! Is there anything else I can help you with?"
    else:
        return "I'm sorry, I didn't understand that. Can you please rephrase your question or ask about a specific banking service?"