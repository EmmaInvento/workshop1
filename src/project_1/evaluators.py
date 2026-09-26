from opentelemetry import trace
from phoenix.client.experiments import create_evaluator

EVALUATOR_VERSION = "contract"

tracer = trace.get_tracer(__name__)


@create_evaluator(name="contract_valid", kind="CODE")
def contract_valid(output: dict) -> bool:
    """Check the complete machine-readable output contract."""
    return output.get("contract_valid") is True


@create_evaluator(name="urgency_level_correct", kind="CODE")
def urgency_level_correct(output: dict, expected: dict) -> bool:
    """Check that the urgency level matches the expected value."""
    urgency_level = output.get("urgency_level")
    expected_urgency_level = expected.get("expected_urgency_level")
    return (
        isinstance(urgency_level, str)
        and isinstance(expected_urgency_level, str)
        and urgency_level == expected_urgency_level
    )
    
    
@create_evaluator(name="name_correct", kind="CODE")
def name_correct(output: dict, expected: dict) -> bool:
    """Check that the name matches the expected value."""
    person_name = output.get("fields", {}).get("person_name")
    expected_person_name = expected.get("expected_name")
    return (
        person_name is None
        and expected_person_name is None
    ) or (
        isinstance(person_name, str)
        and isinstance(expected_person_name, str)
        and person_name == expected_person_name
    )    

@create_evaluator(name="reference_number_correct", kind="CODE")
def reference_number_correct(output: dict, expected: dict) -> bool:
    """Check that the reference_number matches the expected value."""
    reference_number = output.get("fields", {}).get("reference_number")
    expected_reference_number = expected.get("expected_reference_number")
    return (
        reference_number is None
        and expected_reference_number is None
    ) or (
        isinstance(reference_number, str)
        and isinstance(expected_reference_number, str)
        and reference_number == expected_reference_number
    )     
    
@create_evaluator(name="amount_correct", kind="CODE")
def amount_correct(output: dict, expected: dict) -> bool:
    """Check that the amount matches the expected value."""
    amount = output.get("fields", {}).get("amount")
    expected_amount = expected.get("expected_amount")
    return (
        amount is None
        and expected_amount is None
    ) or (
        isinstance(amount, str)
        and isinstance(expected_amount, str)
        and amount == expected_amount
    )  
    
@create_evaluator(name="date_correct", kind="CODE")
def date_correct(output: dict, expected: dict) -> bool:
    """Check that the date matches the expected value."""
    date = output.get("fields", {}).get("date")
    expected_date = expected.get("expected_date")
    return (
        date is None
        and expected_date is None
    ) or (
        isinstance(date, str)
        and isinstance(expected_date, str)
        and date == expected_date
    )            
    



@create_evaluator(name="answer_within_limit", kind="CODE")
def answer_within_limit(output: dict) -> bool:
    """Check that the answer stays within the
    lesson contract limit."""
    with tracer.start_as_current_span("eval_answer_within_limit") as span:
        answer = output.get("answer")
        word_count = len(answer.split()) if isinstance(answer, str) else 0
        result = 0 < word_count <= 100
        span.set_attribute("eval.scorer", "answer_within_limit") #salva nome del valutatore
        span.set_attribute("eval.result", result) #salva true/false
        span.set_attribute("eval.answer_word_count", word_count)# salva numero parole
        return result
    
    
@create_evaluator(name="rationale_within_limit", kind="CODE")
def rationale_within_limit(output: dict) -> bool:
    """Check that the rationale stays within the
    lesson contract limit."""
    with tracer.start_as_current_span("eval_rationale_within_limit") as span:
        rationale = output.get("urgency_rationale")
        word_count = len(rationale.split()) if isinstance(rationale, str) else 0
        result = 0 < word_count <= 100
        span.set_attribute("eval.scorer", "rationale_within_limit") #salva nome del valutatore
        span.set_attribute("eval.result", result) #salva true/false
        span.set_attribute("eval.rationale_word_count", word_count)# salva numero parole
        return result    
        
        
   