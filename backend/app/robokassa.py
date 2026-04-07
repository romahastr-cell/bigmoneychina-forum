"""Robokassa integration with fiscalization (ФЗ-54)"""
import hashlib
import json
import os
import urllib.parse
from typing import Optional

ROBOKASSA_LOGIN = os.getenv("ROBOKASSA_LOGIN", "")
PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "")
PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "")
TEST_MODE = os.getenv("ROBOKASSA_TEST_MODE", "true").lower() == "true"
SNO = os.getenv("ROBOKASSA_SNO", "usn_income")   # система налогообложения
PAYMENT_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def build_receipt(item_name: str, amount: float, email: str) -> dict:
    """Build receipt JSON for fiscalization (ФЗ-54)"""
    return {
        "sno": SNO,
        "items": [
            {
                "name": item_name[:128],
                "quantity": 1,
                "sum": round(amount, 2),
                "payment_method": "full_payment",
                "payment_object": "service",
                "tax": "none"   # без НДС (УСН)
            }
        ]
    }


def build_payment_url(
    inv_id: int,
    amount: float,
    description: str,
    email: str,
    item_name: str = "Билет на форум «Технологии и Бизнес»"
) -> str:
    """Generate Robokassa payment URL with receipt for fiscalization"""
    receipt = build_receipt(item_name, amount, email)
    receipt_json = json.dumps(receipt, ensure_ascii=False)
    receipt_encoded = urllib.parse.quote(receipt_json)

    # Signature: MerchantLogin:OutSum:InvId:Receipt:Password1
    sig_string = f"{ROBOKASSA_LOGIN}:{amount:.2f}:{inv_id}:{receipt_json}:{PASSWORD1}"
    signature = _md5(sig_string)

    params = {
        "MerchantLogin": ROBOKASSA_LOGIN,
        "OutSum": f"{amount:.2f}",
        "InvId": inv_id,
        "Description": description[:100],
        "SignatureValue": signature,
        "Email": email,
        "Receipt": receipt_encoded,
        "Encoding": "utf-8",
        "Culture": "ru",
    }
    if TEST_MODE:
        params["IsTest"] = 1

    return PAYMENT_URL + "?" + urllib.parse.urlencode(params)


def verify_result(out_sum: str, inv_id: str, signature: str) -> bool:
    """Verify Robokassa ResultURL callback signature"""
    sig_string = f"{out_sum}:{inv_id}:{PASSWORD2}"
    expected = _md5(sig_string)
    return expected == signature.upper()


def build_ok_response(inv_id: str) -> str:
    """Required OK response to Robokassa"""
    return f"OK{inv_id}"
