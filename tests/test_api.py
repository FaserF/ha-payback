"""Test API client for PAYBACK Deutschland."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.payback.api import (
    PaybackAPIClient,
    PaybackAuthError,
    PaybackCookieError,
    PaybackCoupon,
    PaybackPoints,
    PaybackWAFError,
    extract_bbst_token,
    normalize_cookie_header,
)


def test_payback_models():
    """Test data model instantiation and field aliases."""
    pts = PaybackPoints(totalPoints=100, availablePoints=80, pendingPoints=20)
    assert pts.total_points == 100
    assert pts.available_points == 80
    assert pts.pending_points == 20

    c = PaybackCoupon(couponId="123", title="Test", partnerName="DM", activated=True)
    assert c.coupon_id == "123"
    assert c.partner_name == "DM"
    assert c.activated is True


def test_api_client_login():
    """Test API client login method."""
    client = PaybackAPIClient("user@test.com", "pass")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"token": "xyz123"}'
    mock_resp.json.return_value = {"token": "xyz123"}

    with patch.object(client.session, "request", return_value=mock_resp):
        assert client.login() is True
        assert client._auth_token == "xyz123"


def test_api_activate_coupon_failure():
    """Test coupon activation error handling."""
    client = PaybackAPIClient("user@test.com", "pass")
    with patch.object(client.session, "request", side_effect=RuntimeError("API Error")):
        with pytest.raises(RuntimeError):
            client.activate_coupon("invalid_id")


def test_normalize_cookie_header_and_bbst_token():
    """Cookie normalization strips Cookie: prefix and extracts bbst token."""
    raw = (
        "Cookie: BIGipServerpool_pde_e3_lmsweb_httpd_a=123; "
        "visid_incap_123=abc; nlbi_123=def; incap_ses_99=ghi; "
        "bbpt=pt123; bbst=st456\n"
    )
    parsed = normalize_cookie_header(raw)
    assert parsed["BIGipServerpool_pde_e3_lmsweb_httpd_a"] == "123"
    assert parsed["visid_incap_123"] == "abc"
    assert parsed["incap_ses_99"] == "ghi"
    assert extract_bbst_token(parsed) == "st456"


def test_cookie_login_and_web_account_parsing():
    """Valid cookie authenticates via /punktekonto and parses points and coupons."""
    client = PaybackAPIClient(
        "1234567890",
        "pass",
        session_cookie="visid_incap_1=a; incap_ses_1=b; bbst=tok1",
    )

    points_html = """
    <html><script type="application/json">
    {"account":{"cardNumber":"1234567890","customerName":"Max","totalPoints":1250,"availablePoints":1000,"pendingPoints":250}}
    </script></html>
    """
    coupons_html = """
    <html><script type="application/json">
    {"coupons":[{"couponId":"cp1","title":"10x Punkte","partnerName":"REWE","activated":false}]}
    </script></html>
    """

    def mock_req(method, url, **kwargs):
        r = MagicMock()
        r.status_code = 200
        r.url = url
        if "/punktekonto" in url:
            r.text = points_html
        elif "/coupons" in url:
            r.text = coupons_html
        else:
            r.text = ""
        return r

    with patch.object(client.session, "request", side_effect=mock_req):
        assert client.login() is True
        acc = client.get_account()
        assert acc.card_number == "1234567890"
        assert acc.points.total_points == 1250
        assert acc.points.available_points == 1000
        assert acc.points.pending_points == 250
        assert len(acc.coupons) == 1
        assert acc.coupons[0].coupon_id == "cp1"
        assert acc.coupons[0].partner_name == "REWE"


def test_cookie_login_waf_and_missing_keys_raise():
    """Malformed cookie raises PaybackCookieError and WAF block raises PaybackWAFError."""
    bad_client = PaybackAPIClient("u", "p", session_cookie="foo=bar")
    with pytest.raises(PaybackCookieError):
        bad_client.login()

    waf_client = PaybackAPIClient("u", "p", session_cookie="incap_ses_1=b; bbst=x")
    waf_resp = MagicMock(status_code=403, url="https://www.payback.de/punktekonto")
    waf_resp.text = "<html>_Incapsula_Resource Request unsuccessful</html>"
    with patch.object(waf_client.session, "request", return_value=waf_resp):
        with pytest.raises(PaybackWAFError):
            waf_client.login()

    no_token_client = PaybackAPIClient("u", "p")
    r_404 = MagicMock(status_code=404, content=b"")
    r_404.raise_for_status.side_effect = RuntimeError("404")
    with patch.object(no_token_client.session, "request", return_value=r_404):
        with pytest.raises(PaybackAuthError):
            no_token_client.login()
