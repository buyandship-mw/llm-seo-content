from typing import Any, Optional

from modules.llm_client import LLMClient
from modules.openai_client import OpenAIClient, AzureOpenAIClient
from modules.post_generator import _invoke_comprehensive_llm

class DummySearchClient(LLMClient):
    def __init__(self):
        self.called_search = False
    @property
    def supports_web_search(self) -> bool:
        return True
    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 1.0,
        *,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        use_search: bool = False,
    ) -> tuple[Any, Optional[str]]:
        if use_search:
            self.called_search = True
            return {}, '{"a": 1}'
        raise AssertionError("should call with use_search=True")

class DummyNoSearchClient(LLMClient):
    def __init__(self):
        self.called = False
    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 1.0,
        *,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        use_search: bool = False,
    ) -> tuple[Any, Optional[str]]:
        if use_search:
            raise AssertionError("should not call with search")
        self.called = True
        return {}, '{"a": 1}'


def test_supports_web_search_flags():
    o = OpenAIClient.__new__(OpenAIClient)
    a = AzureOpenAIClient.__new__(AzureOpenAIClient)
    assert o.supports_web_search is True
    assert a.supports_web_search is False


def test_invoke_comprehensive_llm_respects_flag():
    search_client = DummySearchClient()
    no_search_client = DummyNoSearchClient()

    res1, raw1 = _invoke_comprehensive_llm("hi", search_client, "model", ["a"])
    assert search_client.called_search is True
    assert res1 == {"a": 1}

    res2, raw2 = _invoke_comprehensive_llm("hi", no_search_client, "model", ["a"])
    assert no_search_client.called is True
    assert res2 == {"a": 1}


class DummyFailSearchClient(LLMClient):
    def __init__(self):
        self.called = False
    @property
    def supports_web_search(self) -> bool:
        return True
    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 1.0,
        *,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        use_search: bool = False,
    ) -> tuple[Any, Optional[str]]:
        if use_search:
            self.called = True
            return {}, None
        raise AssertionError("should call with use_search=True")


def test_invoke_comprehensive_llm_aborts_on_search_failure():
    client = DummyFailSearchClient()
    res, raw = _invoke_comprehensive_llm("hi", client, "model", ["a"])
    assert client.called is True
    assert res is None
