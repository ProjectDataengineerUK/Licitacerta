from datetime import datetime

import httpx
import pytest
import respx

from src.tools.blacklist import CGU_BASE, check_blacklist

_CNPJ = "12345678000195"


def _mock_endpoint(endpoint: str, **kwargs):
    return respx.get(
        f"{CGU_BASE}/{endpoint}",
        params={"cnpjSancionado": _CNPJ, "pagina": "1"},
    ).mock(**kwargs)


@respx.mock
def test_blacklist_clean_cnpj_not_blocked():
    for endpoint in ("ceis", "cnep", "cepim"):
        _mock_endpoint(endpoint, return_value=httpx.Response(200, json=[]))

    result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is False
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is False
    assert isinstance(result.checked_at, datetime)


@respx.mock
def test_blacklist_ceis_blocked():
    _mock_endpoint("ceis", return_value=httpx.Response(200, json=[{"cnpj": "12345678000195"}]))
    _mock_endpoint("cnep", return_value=httpx.Response(200, json=[]))
    _mock_endpoint("cepim", return_value=httpx.Response(200, json=[]))

    result = check_blacklist("12345678000195", api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is True


@respx.mock
def test_blacklist_all_blocked():
    for endpoint in ("ceis", "cnep", "cepim"):
        _mock_endpoint(endpoint, return_value=httpx.Response(200, json=[{"cnpj": "12345678000195"}]))

    result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is True
    assert result.cepim_blocked is True
    assert result.any_blocked is True


@respx.mock
def test_blacklist_strips_cnpj_formatting():
    """CNPJ com pontuação deve produzir a mesma requisição que sem pontuação."""
    for endpoint in ("ceis", "cnep", "cepim"):
        _mock_endpoint(endpoint, return_value=httpx.Response(200, json=[]))

    result_formatted = check_blacklist("12.345.678/0001-95", api_key="key")
    result_raw = check_blacklist("12345678000195", api_key="key")

    assert result_formatted.any_blocked == result_raw.any_blocked


@respx.mock
def test_blacklist_raises_on_api_error():
    _mock_endpoint("ceis", return_value=httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        check_blacklist("12345678000195", api_key="test-key")


@respx.mock
def test_blacklist_no_llm_called(mocker):
    """Verifica que nenhum cliente Anthropic é instanciado durante a consulta."""
    for endpoint in ("ceis", "cnep", "cepim"):
        _mock_endpoint(endpoint, return_value=httpx.Response(200, json=[]))

    mock_anthropic = mocker.patch("anthropic.Anthropic")
    check_blacklist("12345678000195", api_key="key")

    mock_anthropic.assert_not_called()
