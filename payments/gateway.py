import os
import json
import urllib.request
import urllib.error
from django.conf import settings


class SafepayGateway:
    """
    Safepay Payment Gateway Integration.
    Supports: JazzCash, Easypaisa, Visa, Mastercard — all through ONE API.
    
    Sandbox Docs: https://docs.safepay.pk
    """

    def __init__(self):
        # Sandbox keys (testing ke liye)
        # Production mein .env se real keys aayengi
        self.api_key = os.getenv('SAFEPAY_API_KEY', 'your-sandbox-api-key')
        self.environment = os.getenv('SAFEPAY_ENV', 'sandbox')

        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox.api.safepay.pk'
        else:
            self.base_url = 'https://api.safepay.pk'

    def create_checkout_url(self, order, request):
        """
        Creates a Safepay checkout session and returns the payment URL.
        Customer ko is URL par redirect karna hai payment ke liye.
        """
        callback_url = request.build_absolute_uri(f'/payments/callback/{order.order_number}/')

        payload = {
            "environment": self.environment,
            "api_key": self.api_key,
            "amount": int(float(order.total_cost) * 100),  # Safepay paisa mein leta hai (Rs. 1000 = 100000)
            "currency": "PKR",
            "order_id": order.order_number,
            "customer": {
                "first_name": order.first_name.split()[0],
                "last_name": " ".join(order.first_name.split()[1:]) or "Customer",
                "email": order.user.email if order.user else "guest@shahgcaphouse.com",
                "phone": order.phone
            },
            "source": "custom_checkout",
            "webhook": callback_url,
            "cancel_url": request.build_absolute_uri(f'/payments/cancel/{order.order_number}/'),
            "redirect_url": callback_url
        }

        url = f"{self.base_url}/checkout/v1/payment/init"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                # Safepay returns a checkout URL where customer will pay
                return data.get('checkout_url', None)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"Safepay API Error ({e.code}): {error_body}")
            return None
        except Exception as e:
            print(f"Safepay Connection Error: {e}")
            return None

    def verify_payment(self, order_number):
        """
        Verifies if a payment was actually successful.
        Ye callback ke baad call hota hai taake confirm ho ke paisa aa gaya.
        """
        url = f"{self.base_url}/checkout/v1/payment/status/{order_number}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('status') == 'Completed', data.get('transaction_id', '')
        except Exception as e:
            print(f"Payment Verification Error: {e}")
            return False, ''