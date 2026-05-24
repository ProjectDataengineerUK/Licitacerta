from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from src.tools.blacklist import CGU_BASE, check_blacklist

_CNPJ = "12345678000195"
_ENDPOINTS = ("ceis", "cnep", "cepim")


def _make_response(data=None, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=MagicMock(status_code=status_code),
        )
    else:
        resp.raise_for_status.return_value = None
        resp.json.return_value = data if data is not None else []
    return resp


@contextmanager
def _mock_client(responses: dict):
    """Patch httpx.Client so each endpoint returns the given response."""
    with patch("src.tools.blacklist.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value

        def _get(url, **_kwargs):
            for endpoint, resp in responses.items():
                if f"/{endpoint}" in url:
                    return resp
            raise ValueError(f"Unexpected URL in test: {url}")

        instance.get.side_effect = _get
        yield instance


def test_blacklist_clean_cnpj_not_blocked():
    responses = {ep: _make_response([]) for ep in _ENDPOINTS}

    with _mock_client(responses):
        result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is False
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is False
    assert isinstance(result.checked_at, datetime)


def test_blacklist_ceis_blocked():
    responses = {
        "ceis": _make_response([{"cnpj": _CNPJ}]),
        "cnep": _make_response([]),
        "cepim": _make_response([]),
    }

    with _mock_client(responses):
        result = check_blacklist(_CNPJ, api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is True


def test_blacklist_all_blocked():
    responses = {ep: _make_response([{"cnpj": _CNPJ}]) for ep in _ENDPOINTS}

    with _mock_client(responses):
        result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is True
    assert result.cepim_blocked is True
    assert result.any_blocked is True


def test_blacklist_strips_cnpj_formatting():
    """CNPJ com pontuação deve produzir a mesma requisição que sem pontuação."""
    responses = {ep: _make_response([]) for ep in _ENDPOINTS}

    with _mock_client(responses) as client:
        check_blacklist("12.345.678/0001-95", api_key="key")
        check_blacklist(_CNPJ, api_key="key")

    for call_args in client.get.call_args_list:
        assert _CNPJ in call_args.kwargs.get("params", {}).get("cnpjSancionado", "")


def test_blacklist_raises_on_api_error():
    responses = {"ceis": _make_response(status_code=500), "cnep": _make_response([]), "cepim": _make_response([])}

    with _mock_client(responses):
        with pytest.raises(httpx.HTTPStatusError):
            check_blacklist(_CNPJ, api_key="test-key")


def test_blacklist_no_llm_called(mocker):
    """Verifica que nenhum cliente Anthropic é instanciado durante a consulta."""
    mock_anthropic = mocker.patch("anthropic.Anthropic")
    responses = {ep: _make_response([]) for ep in _ENDPOINTS}

    with _mock_client(responses):
        check_blacklist(_CNPJ, api_key="key")

    mock_anthropic.assert_not_called()
