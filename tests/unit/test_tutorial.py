from drummer.api.routes.tutorial import STEPS, TutorialStep

EXPECTED_STEP_COUNT = 10


def test_step_count_matches_expected() -> None:
    assert len(STEPS) == EXPECTED_STEP_COUNT


def test_all_steps_are_tutorial_step_instances() -> None:
    for step in STEPS:
        assert isinstance(step, TutorialStep)


def test_first_step_has_no_method() -> None:
    assert STEPS[0].method is None


def test_steps_with_requests_have_method_and_url() -> None:
    for step in STEPS[1:]:
        assert step.method is not None
        assert step.url != ""


def test_step_4_has_base_url_variable_override() -> None:
    # Index 4 = "Environment variables"
    assert "base_url" in STEPS[4].variable_overrides


def test_step_4_url_uses_base_url_variable() -> None:
    assert "{{base_url}}" in STEPS[4].url


def test_step_5_pre_script_is_not_empty() -> None:
    # Index 5 = "Pre-request scripts"
    assert STEPS[5].pre_script != ""


def test_step_5_pre_script_sets_header() -> None:
    assert "dm.request.headers" in STEPS[5].pre_script


def test_step_6_post_script_is_not_empty() -> None:
    # Index 6 = "Post-request scripts"
    assert STEPS[6].post_script != ""


def test_step_6_post_script_reads_response_json() -> None:
    assert "dm.response.json()" in STEPS[6].post_script


def test_all_steps_have_non_empty_title() -> None:
    for step in STEPS:
        assert step.title != ""


def test_all_steps_have_non_empty_instructions() -> None:
    for step in STEPS:
        assert step.instructions != ""
