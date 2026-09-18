from project_1.client import call_model


def test_model_connection() -> None:
    """The configured model endpoint accepts a basic request."""
    result = call_model(
        instructions="Respond with one short word.",
        user_input="Confirm that the connection works.",
    )
    assert result != ""


# If there is a connection problem (exception is raised)
# If an empty string the assertion fails