"""ai_provider reads the text blocks of a reply, wherever they are."""

from types import SimpleNamespace as NS

import pytest

from justdata.shared.analysis.ai_provider import response_text


def test_thinking_block_first():
    reply = NS(content=[NS(type="thinking", thinking="..."), NS(type="text", text="Narrative.")])
    assert response_text(reply) == "Narrative."


def test_several_text_blocks_join():
    assert response_text(NS(content=[NS(type="text", text="A "), NS(type="text", text="B")])) == "A B"


def test_no_text_is_an_error():
    with pytest.raises(Exception, match="no text"):
        response_text(NS(content=[NS(type="thinking", thinking="...")], stop_reason="max_tokens"))
