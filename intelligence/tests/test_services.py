from types import SimpleNamespace

import pytest

from intelligence.services.claude_analyst import generate_analysis

pytestmark = pytest.mark.django_db


def _fake_text_message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def test_generate_analysis_returns_final_text_block(mocker, make_event, make_bout):
    event = make_event()
    bout = make_bout(event, weight_class="Lightweight")

    fake_runner = [
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="get_fighter_profile")]),
        _fake_text_message("Both fighters bring solid records into this matchup."),
    ]
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            messages=SimpleNamespace(tool_runner=mocker.Mock(return_value=fake_runner))
        )
    )
    mocker.patch(
        "intelligence.services.claude_analyst.anthropic.Anthropic", return_value=fake_client
    )

    result = generate_analysis(bout)

    assert result == "Both fighters bring solid records into this matchup."


def test_generate_analysis_falls_back_when_effort_kwarg_unsupported(mocker, make_event, make_bout):
    event = make_event()
    bout = make_bout(event)

    def tool_runner(*args, **kwargs):
        if "output_config" in kwargs:
            raise TypeError("unexpected keyword argument 'output_config'")
        return [_fake_text_message("Analysis without effort tuning.")]

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(messages=SimpleNamespace(tool_runner=tool_runner))
    )
    mocker.patch(
        "intelligence.services.claude_analyst.anthropic.Anthropic", return_value=fake_client
    )

    result = generate_analysis(bout)

    assert result == "Analysis without effort tuning."


def test_generate_analysis_raises_when_no_text_block_present(mocker, make_event, make_bout):
    event = make_event()
    bout = make_bout(event)

    fake_runner = [
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="get_fighter_profile")])
    ]
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            messages=SimpleNamespace(tool_runner=mocker.Mock(return_value=fake_runner))
        )
    )
    mocker.patch(
        "intelligence.services.claude_analyst.anthropic.Anthropic", return_value=fake_client
    )

    with pytest.raises(RuntimeError, match="no text block"):
        generate_analysis(bout)
