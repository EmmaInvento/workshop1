from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from phoenix.otel import register
    
from .config import (
    PHOENIX_COLLECTOR_ENDPOINT, 
    PHOENIX_PROJECT_NAME,
    )

def setup_tracing() -> None:
    """Configure OpenTelemetry to export traces
    to Phoenix and instrument the OpenAI client."""
    #Configure OpenTelemary to send traces to phoenix
    tracer_provider = register(
        project_name=PHOENIX_PROJECT_NAME,
        endpoint=PHOENIX_COLLECTOR_ENDPOINT,
    )
    # Instrument OpenAI client:  every call
    # to .create() or .parse() emits a span.
    OpenAIInstrumentor().instrument(
        tracer_provider=tracer_provider
    )


def get_tracer(name: str):
    """Return a tracer for creating manual spans."""
    return trace.get_tracer(name) 