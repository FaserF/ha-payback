"""Pure Python client for PAYBACK Deutschland using curl_cffi with anti-ban mechanisms."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from curl_cffi import requests
from pydantic import BaseModel, ConfigDict, Field

_LOGGER = logging.getLogger(__name__)

# Base API URLs
PAYBACK_API_BASE = "https://www.payback.de/pb/v1/"
PAYBACK_WEB_BASE = "https://www.payback.de"
USER_AGENT = "PAYBACK/8.5.0 (Android 14; Mobile; de_DE)"
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class PaybackError(RuntimeError):
    """Base error for PAYBACK integration."""


class PaybackCookieError(PaybackError):
    """Raised when the provided browser session cookie is missing or malformed."""


class PaybackWAFError(PaybackError):
    """Raised when Imperva/Incapsula WAF blocks the request."""


class PaybackAuthError(PaybackError):
    """Raised when authentication fails or the web session cookie is expired."""


def normalize_cookie_header(raw: str | None) -> dict[str, str]:
    """Parse a copied Cookie header string into a clean name->value mapping."""
    if not raw:
        return {}
    cleaned = raw.strip().strip('"').strip("'")
    cleaned = re.sub(r"^cookie\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")

    cookies: dict[str, str] = {}
    for item in cleaned.split(";"):
        part = item.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        name = k.strip()
        val = v.strip()
        if name:
            cookies[name] = val
    return cookies


def extract_bbst_token(cookies: dict[str, str]) -> str | None:
    """Extract Payback web session token (bbst/bbpt) if present."""
    for key in ("bbst", "bbpt"):
        if cookies.get(key):
            return cookies[key]
    return None


def _is_waf_challenge(status_code: int, body: str) -> bool:
    """Return True if the response indicates an Imperva/Incapsula WAF block."""
    if status_code in (403, 429):
        return True
    lowered = body.lower()
    return (
        "_incapsula_resource" in lowered
        or "request unsuccessful" in lowered
        or "incapsula incident id" in lowered
    )


def _is_login_page(url: str, body: str) -> bool:
    """Return True if Payback redirected to login or served an unauthenticated page."""
    lower_url = url.lower()
    if "/login" in lower_url or "sso/login" in lower_url:
        return True
    lowered = body.lower()
    return (
        'name="password"' in lowered
        and "punktekonto" not in lowered
        and "points" not in lowered
    )


def _parse_int(value: Any) -> int:
    """Parse localized integer strings such as '1.234' or '1,234' safely."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r"[^\d-]", "", str(value))
    if not digits or digits == "-":
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def _extract_embedded_json_objects(html: str) -> list[dict[str, Any]]:
    """Extract JSON objects from __NEXT_DATA__ or application/json script tags."""
    objects: list[dict[str, Any]] = []
    for match in re.finditer(
        r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        raw_json = match.group(1).strip()
        if not raw_json:
            continue
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                objects.append(parsed)
        except json.JSONDecodeError:
            continue
    return objects


def _walk_find_points(obj: Any) -> dict[str, int] | None:
    """Recursively locate points fields inside hydrated Payback JSON."""
    if isinstance(obj, dict):
        for total_k, avail_k, pend_k in (
            ("totalPoints", "availablePoints", "pendingPoints"),
            ("total", "available", "pending"),
            ("punkte", "verfuegbarePunkte", "gesperrtePunkte"),
        ):
            if total_k in obj or avail_k in obj:
                total = _parse_int(obj.get(total_k, 0))
                avail = _parse_int(obj.get(avail_k, total))
                pend = _parse_int(obj.get(pend_k, 0))
                return {"total": total, "available": avail, "pending": pend}
        for val in obj.values():
            found = _walk_find_points(val)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _walk_find_points(item)
            if found is not None:
                return found
    return None


def _walk_find_coupons(obj: Any) -> list[PaybackCoupon]:
    """Recursively locate coupon lists inside hydrated Payback JSON."""
    coupons: list[PaybackCoupon] = []
    seen: set[str] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, dict):
            cid = node.get("couponId") or node.get("id")
            if cid and (
                "partnerName" in node
                or "activated" in node
                or "title" in node
                or "multiplier" in node
            ):
                cid_str = str(cid)
                if cid_str not in seen:
                    seen.add(cid_str)
                    coupons.append(
                        PaybackCoupon(
                            couponId=cid_str,
                            title=str(node.get("title") or node.get("headline") or ""),
                            description=str(node.get("description") or ""),
                            partnerName=str(
                                node.get("partnerName") or node.get("partner") or ""
                            ),
                            multiplier=str(node.get("multiplier") or ""),
                            validUntil=str(node.get("validUntil") or ""),
                            activated=bool(
                                node.get("activated")
                                or node.get("isActivated")
                                or False
                            ),
                        )
                    )
            for val in node.values():
                _visit(val)
        elif isinstance(node, list):
            for item in node:
                _visit(item)

    _visit(obj)
    return coupons


def parse_points_html(html: str, default_card: str) -> tuple[str, str, PaybackPoints]:
    """Parse points balance and customer metadata from /punktekonto HTML."""
    for obj in _extract_embedded_json_objects(html):
        pts = _walk_find_points(obj)
        if pts is not None:
            card_match = re.search(r'"cardNumber"\s*:\s*"([^"]+)"', html)
            name_match = re.search(r'"customerName"\s*:\s*"([^"]+)"', html)
            return (
                card_match.group(1) if card_match else default_card,
                name_match.group(1)
                if name_match
                else f"Payback Customer ({default_card})",
                PaybackPoints(
                    totalPoints=pts["total"],
                    availablePoints=pts["available"],
                    pendingPoints=pts["pending"],
                ),
            )

    total_m = re.search(
        r"(?:Gesamtpunkte|Punktestand|Total\s*Points)[^\d]{0,40}([\d.,]+)",
        html,
        re.IGNORECASE,
    )
    avail_m = re.search(
        r"(?:Verf(?:ü|ue|&uuml;)gbare\s*Punkte|Available\s*Points)[^\d]{0,40}([\d.,]+)",
        html,
        re.IGNORECASE,
    )
    pend_m = re.search(
        r"(?:Gesperrte\s*Punkte|Pending\s*Points)[^\d]{0,40}([\d.,]+)",
        html,
        re.IGNORECASE,
    )
    if total_m is not None or avail_m is not None:
        total = (
            _parse_int(total_m.group(1))
            if total_m is not None
            else _parse_int(avail_m.group(1))  # type: ignore[union-attr]
        )
        avail = _parse_int(avail_m.group(1)) if avail_m is not None else total
        pend = _parse_int(pend_m.group(1)) if pend_m else 0
        return (
            default_card,
            f"Payback Customer ({default_card})",
            PaybackPoints(totalPoints=total, availablePoints=avail, pendingPoints=pend),
        )

    raise PaybackAuthError("Could not parse PAYBACK points from /punktekonto response")


def parse_coupons_html(html: str) -> list[PaybackCoupon]:
    """Parse coupons from /coupons hydrated JSON or HTML attributes."""
    for obj in _extract_embedded_json_objects(html):
        found = _walk_find_coupons(obj)
        if found:
            return found

    coupons: list[PaybackCoupon] = []
    for match in re.finditer(
        r'data-coupon-id=["\']([^"\']+)["\']([^>]*)', html, re.IGNORECASE
    ):
        cid = match.group(1).strip()
        attrs = match.group(2)
        title_m = re.search(r'data-title=["\']([^"\']*)["\']', attrs)
        partner_m = re.search(r'data-partner=["\']([^"\']*)["\']', attrs)
        act_m = re.search(r'data-activated=["\']?(true|1)["\']?', attrs, re.IGNORECASE)
        coupons.append(
            PaybackCoupon(
                couponId=cid,
                title=title_m.group(1) if title_m else cid,
                partnerName=partner_m.group(1) if partner_m else "",
                activated=bool(act_m),
            )
        )
    return coupons


class PaybackPoints(BaseModel):
    """Payback points breakdown."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    total_points: int = Field(default=0, alias="totalPoints")
    available_points: int = Field(default=0, alias="availablePoints")
    pending_points: int = Field(default=0, alias="pendingPoints")


class PaybackCoupon(BaseModel):
    """Payback coupon details."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    coupon_id: str = Field(default="", alias="couponId")
    title: str = Field(default="")
    description: str = Field(default="")
    partner_name: str = Field(default="", alias="partnerName")
    multiplier: str = Field(default="")
    valid_until: str = Field(default="", alias="validUntil")
    activated: bool = Field(default=False)


class PaybackAccount(BaseModel):
    """Payback account summary."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    card_number: str = Field(default="", alias="cardNumber")
    customer_name: str = Field(default="", alias="customerName")
    points: PaybackPoints = Field(default_factory=PaybackPoints)
    coupons: list[PaybackCoupon] = Field(default_factory=list)


class PaybackAPIClient:
    """API client interacting with Payback mobile or cookie-backed web endpoints."""

    def __init__(
        self, username: str, password: str, session_cookie: str | None = None
    ) -> None:
        self.username = username
        self.password = password
        self.session_cookie = session_cookie
        self.session = requests.Session()
        self._auth_token: str | None = None
        self._web_authenticated = False
        self._cookies: dict[str, str] = normalize_cookie_header(session_cookie)

        for k, v in self._cookies.items():
            self.session.cookies.set(k, v, domain=".payback.de")

    def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        url: str,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        req_headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Accept-Language": "de-DE,de;q=0.9",
            "X-PAYBACK-CLIENT-ID": "androidapp_de",
        }
        if self._auth_token:
            req_headers["Authorization"] = f"Bearer {self._auth_token}"
        if headers:
            req_headers.update(headers)

        try:
            response = self.session.request(
                method,
                url,
                json=json_data,
                headers=req_headers,
                impersonate="chrome",
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as exc:
            _LOGGER.debug("Payback API request for %s returned: %s", url, exc)
            raise RuntimeError(f"Payback API request failed: {exc}") from exc

    def _web_get(self, path: str) -> str:
        """Perform a browser-like GET request against www.payback.de."""
        url = f"{PAYBACK_WEB_BASE}{path}"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": WEB_USER_AGENT,
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        response = self.session.request(
            "GET",
            url,
            headers=headers,
            impersonate="chrome",
            timeout=15.0,
        )
        body = getattr(response, "text", "") or ""
        resp_url = str(getattr(response, "url", url))
        if _is_waf_challenge(response.status_code, body):
            raise PaybackWAFError(
                "PAYBACK request blocked by Imperva/Incapsula WAF challenge"
            )
        if response.status_code in (401, 404):
            raise PaybackAuthError(
                f"PAYBACK web endpoint {path} returned HTTP {response.status_code}"
            )
        response.raise_for_status()
        if _is_login_page(resp_url, body):
            raise PaybackAuthError("PAYBACK session cookie expired or not logged in")
        return body

    def login(self) -> bool:
        """Authenticate via browser session cookie or mobile session API."""
        self._web_authenticated = False
        if self.session_cookie and self.session_cookie.strip():
            if not self._cookies:
                raise PaybackCookieError(
                    "Provided session cookie string could not be parsed"
                )
            has_incap = any(
                k.startswith(("visid_incap_", "incap_ses_")) for k in self._cookies
            )
            if not extract_bbst_token(self._cookies) and not has_incap:
                raise PaybackCookieError(
                    "Session cookie is missing required Payback/Imperva keys (bbst or visid_incap_/incap_ses_)"
                )
            self._web_get("/punktekonto")
            self._web_authenticated = True
            return True

        login_url = f"{PAYBACK_API_BASE}sessions"
        try:
            res = self._request(
                "POST",
                login_url,
                json_data={
                    "principal": self.username,
                    "password": self.password,
                },
            )
        except Exception as exc:
            raise PaybackAuthError(f"Payback login failed: {exc}") from exc

        if isinstance(res, dict) and res.get("token"):
            self._auth_token = str(res["token"])
            return True

        raise PaybackAuthError(
            "Payback login did not return a session token; please provide a browser session cookie"
        )

    def get_account(self) -> PaybackAccount:
        """Fetch account points and coupons from mobile API or authenticated web pages."""
        if self._auth_token:
            data = self._request("GET", f"{PAYBACK_API_BASE}account")
            return PaybackAccount.model_validate(data)

        if self._cookies or self._web_authenticated:
            points_html = self._web_get("/punktekonto")
            card_no, customer_name, points = parse_points_html(
                points_html, self.username
            )
            coupons: list[PaybackCoupon] = []
            try:
                coupons_html = self._web_get("/coupons")
                coupons = parse_coupons_html(coupons_html)
            except PaybackError:
                raise
            except Exception as exc:
                _LOGGER.debug("Failed parsing /coupons page: %s", exc)
            return PaybackAccount(
                cardNumber=card_no,
                customerName=customer_name,
                points=points,
                coupons=coupons,
            )

        raise PaybackAuthError("Not authenticated with PAYBACK")

    def activate_coupon(self, coupon_id: str) -> bool:
        """Activate a specific coupon via Payback API."""
        activate_url = f"{PAYBACK_API_BASE}coupons/{coupon_id}/activate"
        self._request("POST", activate_url)
        return True
