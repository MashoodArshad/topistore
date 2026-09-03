import json
import hmac
import hashlib
import urllib.request
import urllib.parse
import urllib.error
from django.conf import settings


class SafepayGatewayClient:
    """
    Official Safepay REST API Integration Client (v1 / v2).
    Handles Tracker Initialization, Hosted Checkout Redirection,
    HMAC Signature Validation, and Server-to-Server Status Inquiries.
    """

    def __init__(self):
        self.api_key = settings.SAFEPAY_API_KEY
        self.api_secret = settings.SAFEPAY_API_SECRET
        self.webhook_secret = settings.SAFEPAY_WEBHOOK_SECRET
        self.base_url = settings.SAFEPAY_BASE_URL
        self.checkout_base_url = settings.SAFEPAY_CHECKOUT_URL
        self.environment = settings.SAFEPAY_ENV

    def create_order_tracker(self, order):
        """
        Registers order with Safepay API: POST /order/v1/init
        Returns: (tracker_token: str, error_message: str)
        """
        if not self.api_key:
            return None, "SAFEPAY_API_KEY is not set in environment variables."

        # Convert PKR Decimal to integer Paisa (e.g. 1500.00 -> 150000)
        amount_paisa = int(round(float(order.total_cost) * 100))

        endpoint = f"{self.base_url}/order/v1/init"
        payload = {
            "client": self.api_key,
            "amount": amount_paisa,
            "currency": "PKR",
            "environment": self.environment
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status in (200, 201):
                    raw_data = json.loads(response.read().decode('utf-8'))
                    token = raw_data.get('data', {}).get('token')
                    if token:
                        return token, None
                    return None, f"Malformed response from Safepay: {raw_data}"
                return None, f"Safepay returned HTTP status {response.status}"

        except urllib.error.HTTPError as http_err:
            try:
                error_body = json.loads(http_err.read().decode('utf-8'))
                error_msg = error_body.get('status', {}).get('message', str(http_err))
            except Exception:
                error_msg = f"HTTP Error {http_err.code}: {http_err.reason}"
            return None, error_msg

        except urllib.error.URLError as url_err:
            return None, f"Network connection error to Safepay: {url_err.reason}"

        except Exception as ex:
            return None, f"Unexpected gateway exception: {str(ex)}"

    def construct_checkout_url(self, tracker_token, order, redirect_url, cancel_url):
        """
        Constructs the official Safepay Hosted Checkout URL.
        """
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
        """
        Direct API Inquiry: Queries Safepay to check if a tracker token is paid.
        Returns: (is_paid: bool, transaction_reference: str)
        """
        if not tracker_token:
            return False, ""

        endpoint = f"{self.base_url}/order/v1/tracker/{tracker_token}"
        headers = {
            "Accept": "application/json",
            "X-SFPY-MERCHANT-SECRET": self.api_secret
        }

        try:
            req = urllib.request.Request(endpoint, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    tracker_data = data.get('data', {})
                    state = tracker_data.get('state', '').upper()
                    token = tracker_data.get('token', tracker_token)

                    # State 'TRACKER_ENDED' or 'PAID' or 'COMPLETED' indicates success
                    if state in ('PAID', 'COMPLETED', 'TRACKER_ENDED'):
                        return True, token
        except Exception as e:
            print(f"⚠️ Direct Tracker Inquiry Notice: {e}")

        return False, ""

    def verify_webhook_signature(self, raw_body_bytes, received_signature):
        """
        Validates HMAC SHA-256 digital signature sent in webhook headers.
        """
        if not self.webhook_secret or not received_signature:
            return False

        computed_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            raw_body_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, received_signature)