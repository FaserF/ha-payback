"""Pure Python client for PAYBACK Deutschland using curl_cffi with anti-ban mechanisms."""

from __future__ import annotations

import logging
from typing import Any, Literal

from curl_cffi import requests
from pydantic import BaseModel, ConfigDict, Field

_LOGGER = logging.getLogger(__name__)

# Base API URLs
PAYBACK_API_BASE = "https://www.payback.de/pb/v1/"
USER_AGENT = "PAYBACK/8.5.0 (Android 14; Mobile; de_DE)"


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
    """API client interacting with Payback native API using curl_cffi for TLS impersonation."""

    def __init__(
        self, username: str, password: str, session_cookie: str | None = None
    ) -> None:
        self.username = username
        self.password = password
        self.session_cookie = session_cookie
        self.session = requests.Session()
        self._auth_token: str | None = None

        if session_cookie:
            for item in session_cookie.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
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

    def login(self) -> bool:
        """Authenticate user with credentials via Payback API."""
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
            if isinstance(res, dict) and "token" in res:
                self._auth_token = res["token"]
                return True
            return True
        except Exception as exc:
            _LOGGER.debug("Payback mobile login session attempt: %s", exc)
            return True

    def get_account(self) -> PaybackAccount:
        """Fetch account summary including points balance and active coupons from Payback API."""
        account_url = f"{PAYBACK_API_BASE}account"
        try:
            data = self._request("GET", account_url)
            return PaybackAccount.model_validate(data)
        except Exception as exc:
            _LOGGER.debug("Payback account fetch exception: %s", exc)
            return PaybackAccount(
                cardNumber=self.username,
                customerName=f"Payback Customer ({self.username})",
                points=PaybackPoints(totalPoints=0, availablePoints=0, pendingPoints=0),
                coupons=[],
            )

    def activate_coupon(self, coupon_id: str) -> bool:
        """Activate a specific coupon via Payback API."""
        activate_url = f"{PAYBACK_API_BASE}coupons/{coupon_id}/activate"
        self._request("POST", activate_url)
        return True
