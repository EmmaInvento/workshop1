from project_1.chat import chat_response
from project_1.tracing import setup_tracing

def main() -> None:
    setup_tracing()
    user_input = input("What's your question? ")
    response = chat_response(user_input)
    print(response)
    
if __name__ == "__main__":
    main()     