import json
import hmac
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from django.conf import settings


class SafepayGatewayClient:
    """
    Official Safepay REST API Client.
    Strictly points to Sandbox or Production cluster.
    """

    def __init__(self):
        self.api_key = str(getattr(settings, 'SAFEPAY_API_KEY', '')).strip().strip('"').strip("'")
        self.api_secret = str(getattr(settings, 'SAFEPAY_API_SECRET', '')).strip().strip('"').strip("'")
        self.webhook_secret = str(getattr(settings, 'SAFEPAY_WEBHOOK_SECRET', '')).strip().strip('"').strip("'")
        self.environment = str(getattr(settings, 'SAFEPAY_ENV', 'sandbox')).strip().lower()

        # Dynamic Endpoint Routing
        if self.environment == 'production':
            self.base_url = 'https://api.getsafepay.com'
            self.checkout_base_url = 'https://getsafepay.com/checkout/pay'
        else:
            self.base_url = 'https://sandbox.api.getsafepay.com'
            self.checkout_base_url = 'https://sandbox.api.getsafepay.com/checkout/pay'

    def _get_headers(self, extra_headers=None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def create_order_tracker(self, order):
        """
        Initializes an official Safepay order tracker.
        Converts PKR to Paisa (1 PKR = 100 Paisa).
        """
        if not self.api_key:
            return None, "SAFEPAY_API_KEY is missing from .env"

        amount_paisa = int(round(float(order.total_cost) * 100))

        endpoint = f"{self.base_url}/order/v1/init"
        payload = {
            "client": self.api_key,
            "amount": amount_paisa,
            "currency": "PKR",
            "environment": self.environment
        }

        print(f"\n🚀 [SAFEPAY DISPATCH] Endpoint: {endpoint}")
        print(f"📦 [PAYLOAD] Client: {self.api_key[:6]}... | Amount: {amount_paisa} Paisa | Env: {self.environment}")

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=self._get_headers(),
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                raw_data = json.loads(response.read().decode('utf-8'))
                print(f"✅ [SAFEPAY RESPONSE]: {raw_data}\n")
                
                token = raw_data.get('data', {}).get('token')
                if token:
                    return token, None
                return None, f"Malformed response: {raw_data}"

        except urllib.error.HTTPError as http_err:
            try:
                error_body = json.loads(http_err.read().decode('utf-8'))
                status_obj = error_body.get('status', {})
                message = status_obj.get('message', 'fail')
                errors = status_obj.get('errors', [])
                if errors:
                    error_msg = f"{message}: {', '.join(str(e) for e in errors) if isinstance(errors, list) else str(errors)}"
                else:
                    error_msg = f"HTTP {http_err.code}: {message}"
            except Exception:
                error_msg = f"HTTP Error {http_err.code}: {http_err.reason}"
            print(f"❌ [SAFEPAY ERROR]: {error_msg}\n")
            return None, error_msg

        except urllib.error.URLError as url_err:
            return None, f"Network Error: {url_err.reason}"

        except Exception as ex:
            return None, f"Gateway Error: {str(ex)}"

    def construct_checkout_url(self, tracker_token, order, redirect_url, cancel_url):
        params = {
            'beacon': tracker_token,
            'env': self.environment,
            'source': 'custom',
            'order_id': order.order_number,
            'redirect_url': redirect_url,
            'cancel_url': cancel_url,
        }
        query_string = urllib.parse.urlencode(params)
        return f"{self.checkout_base_url}?{query_string}"

    def verify_tracker_status(self, tracker_token):
        if not tracker_token:
            return False, ""

        endpoint = f"{self.base_url}/order/v1/tracker/{tracker_token}"
        headers = self._get_headers({"X-SFPY-MERCHANT-SECRET": self.api_secret})

        try:
            req = urllib.request.Request(endpoint, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    state = data.get('data', {}).get('state', '').upper()
                    token = data.get('data', {}).get('token', tracker_token)
                    if state in ('PAID', 'COMPLETED', 'TRACKER_ENDED'):
                        return True, token
        except Exception as e:
            print(f"⚠️ Tracker inquiry notice: {e}")

        return False, ""

    def verify_webhook_signature(self, raw_body_bytes, received_signature):
        if not self.webhook_secret or not received_signature:
            return False

        computed_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            raw_body_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, received_signature)