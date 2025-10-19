import os
import io
import zipfile
from typing import Tuple, Optional

from fastapi import HTTPException, status

MOCK = os.getenv('PAY_MOCK', 'true').lower() == 'true'


def _read_private_key_from_path(path: str) -> str:
    if not path:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='WECHAT_PRIVATE_KEY_PATH 未配置')
    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail='微信私钥pem文件不存在')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _build_wx_client():
    from wechatpayv3 import WeChatPay, WeChatPayType
    mchid = os.getenv('WECHAT_MCH_ID')
    appid = os.getenv('WECHAT_APP_ID')
    serial_no = os.getenv('WECHAT_MCH_CERT_SERIAL_NO')
    api_v3_key = os.getenv('WECHAT_API_V3_KEY')
    pk_path = os.getenv('WECHAT_PRIVATE_KEY_PATH')
    base_url = os.getenv('BASE_URL', '')
    required = {
        'WECHAT_MCH_ID': mchid,
        'WECHAT_APP_ID': appid,
        'WECHAT_MCH_CERT_SERIAL_NO': serial_no,
        'WECHAT_API_V3_KEY': api_v3_key,
        'WECHAT_PRIVATE_KEY_PATH': pk_path,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise HTTPException(status_code=500, detail=f"微信支付参数未完整配置: 缺少 {', '.join(missing)}")
    private_key = _read_private_key_from_path(pk_path)
    notify_url = base_url.rstrip('/') + '/api/pay/notify/wechat' if base_url else None
    return WeChatPay(wechatpay_type=WeChatPayType.NATIVE, appid=appid, mchid=mchid, private_key=private_key, cert_serial_no=serial_no, apiv3_key=api_v3_key, notify_url=notify_url)


def create_native_order(amount_yuan: float, description: str, out_trade_no: str) -> Tuple[str, dict]:
    """Return (code_url, raw_resp). In MOCK mode, return a placeholder URL or in real mode call WeChat Native API."""
    if MOCK:
        return f"/api/pay/mock/wechat_qr/{out_trade_no}", {"mock": True}
    wx = _build_wx_client()
    total_cents = int(round(amount_yuan * 100))
    # 规范 out_trade_no 为不带连字符的32位（微信最大32字节限制）
    wx_out_trade_no = out_trade_no.replace('-', '')[:32]
    # 使用通用 pay 接口并指定 NATIVE 类型，保持与官方示例一致
    from wechatpayv3 import WeChatPayType
    code, data = wx.pay(
        description=description,
        out_trade_no=wx_out_trade_no,
        amount={'total': total_cents, 'currency': 'CNY'},
        pay_type=WeChatPayType.NATIVE
    )
    print(code)
    print(data)
    # 兼容字符串/字节响应体，尽量解析为JSON对象
    parsed = data
    if isinstance(parsed, (bytes, bytearray)):
        try:
            parsed = parsed.decode('utf-8')
        except Exception:
            pass
    if isinstance(parsed, str):
        try:
            import json
            parsed = json.loads(parsed)
        except Exception:
            pass
    print(code, parsed)
    if code == 200 and isinstance(parsed, dict) and 'code_url' in parsed:
        return parsed['code_url'], parsed
    raise HTTPException(status_code=500, detail=f'微信下单失败: {parsed}')


def verify_and_parse_notify(headers, body_bytes: bytes) -> dict:
    if MOCK:
        return {"mock": True}
    wx = _build_wx_client()
    try:
        import json
        body = json.loads(body_bytes.decode('utf-8'))
        print("decrypt_callback input headers:", dict(headers))
        print("decrypt_callback input body:", body)
        # decrypt_callback 方法需要传入 headers 和 body 来验证签名并解密
        # 注意：某些SDK版本可能需要传入 body_bytes 而不是解析后的 dict
        result = wx.decrypt_callback(headers, body_bytes.decode('utf-8'))
        print("decrypt_callback result:", result)
        print("decrypt_callback result type:", type(result))
        # result 是解密后的数据，通常包含 out_trade_no, trade_state 等字段
        return {"resource": result}
    except Exception as e:
        print(f"decrypt_callback error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f'微信回调解析失败: {str(e)}')


