from .client import call_model
from .prompts.loader import load_prompt
from .tracing import get_tracer

OFFICES = [] #In the future we might have to classify the office the custumer has to contact

tracer = get_tracer(__name__)

def chat_response(message:str) -> str:
    instructions = load_prompt("instruction")
    
    
    with tracer.start_as_current_span(
        "chat_response"
    ) as span:
        response = call_model(
            instructions = instructions, 
            user_input = message,
            )
        span.set_attribute("response", response)
        return response
    

'''
VALID_OFFICES = {
    
}


def validate_office(office: str) -> str:
    """Check that the model returned a known office."""
    with tracer.start_as_current_span(
        "validate_office"
    ) as span:
        span.set_attribute("raw_office", office)
        if office in VALID_CATEGORIES:
            span.set_attribute("valid", True)
            return office
        span.set_attribute("valid", False)
        return "other" 
'''        


