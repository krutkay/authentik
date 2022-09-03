"""Device flow views"""
from typing import Optional
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils.timezone import now
from django.views import View

from authentik.lib.utils.time import timedelta_from_string
from authentik.providers.oauth2.models import DeviceToken, OAuth2Provider


class DeviceView(View):
    """Device flow, devices can request tokens which users can verify"""

    client_id: str
    provider: OAuth2Provider
    scopes: list[str] = []

    def parse_request(self) -> Optional[HttpResponse]:
        """Parse incoming request"""
        client_id = self.request.POST.get("client_id", None)
        if not client_id:
            return HttpResponseBadRequest()
        provider = OAuth2Provider.objects.filter(
            client_id=client_id,
        ).first()
        if not provider:
            return HttpResponseBadRequest()
        self.provider = provider
        self.client_id = client_id
        self.scopes = self.request.POST.get("scope", "").split(" ")
        return None

    def post(self, request: HttpRequest) -> HttpResponse:
        """Generate device token"""
        resp = self.parse_request()
        if resp:
            return resp
        until = timedelta_from_string(self.provider.access_code_validity)
        token: DeviceToken = DeviceToken.objects.create(
            expires=now() + until, provider=self.provider, _scope=" ".join(self.scopes)
        )
        device_url = self.request.build_absolute_uri(
            reverse("authentik_providers_oauth2_root:device-login")
        )
        return JsonResponse(
            {
                "device_code": token.device_code,
                "verification_uri": device_url,
                "verification_uri_complete": device_url
                + "?"
                + urlencode(
                    {
                        "code": token.user_code,
                    }
                ),
                "user_code": token.user_code,
                "expires_in": until.total_seconds(),
                "interval": 5,
            }
        )


class DeviceEntryView(View):
    """View used to initiate the device-code flow, url entered by endusers"""

    def dispatch(self, request: HttpRequest) -> HttpResponse:
        pass
