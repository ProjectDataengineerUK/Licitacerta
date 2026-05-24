from datetime import datetime, timezone

import httpx
import pytest
import respx

from src.tools.blacklist import check_blacklist, CGU_BASE


@respx.mock
def test_blacklist_clean_cnpj_not_blocked():
    for endpoint in ("ceis", "cnep", "cepim"):
        respx.get(f"{CGU_BASE}/{endpoint}").mock(
            return_value=httpx.Response(200, json=[])
        )

    result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is False
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is False
    assert isinstance(result.checked_at, datetime)


@respx.mock
def test_blacklist_ceis_blocked():
    respx.get(f"{CGU_BASE}/ceis").mock(
        return_value=httpx.Response(200, json=[{"cnpj": "12345678000195"}])
    )
    respx.get(f"{CGU_BASE}/cnep").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{CGU_BASE}/cepim").mock(return_value=httpx.Response(200, json=[]))

    result = check_blacklist("12345678000195", api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is False
    assert result.cepim_blocked is False
    assert result.any_blocked is True


@respx.mock
def test_blacklist_all_blocked():
    for endpoint in ("ceis", "cnep", "cepim"):
        respx.get(f"{CGU_BASE}/{endpoint}").mock(
            return_value=httpx.Response(200, json=[{"cnpj": "12345678000195"}])
        )

    result = check_blacklist("12.345.678/0001-95", api_key="test-key")

    assert result.ceis_blocked is True
    assert result.cnep_blocked is True
    assert result.cepim_blocked is True
    assert result.any_blocked is True


@respx.mock
def test_blacklist_strips_cnpj_formatting():
    """CNPJ com pontuação deve produzir a mesma requisição que sem pontuação."""
    for endpoint in ("ceis", "cnep", "cepim"):
        respx.get(f"{CGU_BASE}/{endpoint}").mock(
            return_value=httpx.Response(200, json=[])
        )

    # Não deve lançar exceção independente do formato
    result_formatted = check_blacklist("12.345.678/0001-95", api_key="key")
    result_raw = check_blacklist("12345678000195", api_key="key")

    assert result_formatted.any_blocked == result_raw.any_blocked


@respx.mock
def test_blacklist_raises_on_api_error():
    respx.get(f"{CGU_BASE}/ceis").mock(return_value=httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        check_blacklist("12345678000195", api_key="test-key")


@respx.mock
def test_blacklist_no_llm_called(mocker):
    """Verifica que nenhum cliente Anthropic é instanciado durante a consulta."""
    for endpoint in ("ceis", "cnep", "cepim"):
        respx.get(f"{CGU_BASE}/{endpoint}").mock(
            return_value=httpx.Response(200, json=[])
        )

    mock_anthropic = mocker.patch("anthropic.Anthropic")
    check_blacklist("12345678000195", api_key="key")

    mock_anthropic.assert_not_called()
