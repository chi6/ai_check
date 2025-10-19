import os
from typing import Tuple

MOCK = os.getenv('PAY_MOCK', 'true').lower() == 'true'

def create_page_pay(amount_yuan: float, subject: str, out_trade_no: str) -> Tuple[str, dict]:
    """Return (pay_url, raw_resp). In MOCK mode, return a placeholder URL."""
    if MOCK:
        return f"/api/pay/mock/alipay_url/{out_trade_no}", {"mock": True}
    # TODO: integrate python-alipay-sdk page pay
    raise NotImplementedError('Alipay page.pay integration required')

def verify_notify(params: dict) -> bool:
    if MOCK:
        return True
    # TODO: verify sign with alipay public key
    raise NotImplementedError('Alipay notify verification required')


