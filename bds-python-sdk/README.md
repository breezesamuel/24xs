# bds-client

丙大山数字资产平台官方 Python SDK。

## 安装
```bash
pip install -e .
```

## 快速开始
```python
from bds_client import BDSClient

client = BDSClient(api_key="sk_live_xxxxxxxx", base_url="https://geo-audit-24xs.vercel.app")

# 搜索资产
assets = client.search_assets(q="采购方画像", type="采购方画像", limit=10)
print(assets)

# 购买
purchase = client.purchase(asset_id="V-20261003-001234", qty=1)
print(purchase.checkout_url)

# 验证
verify = client.verify_proof(proof="...", data={"name": "xxx"})
print(verify.match)
```

## CLI
```bash
bds-client --api-key sk_live_xxx search -q "采购方画像" -l 5
bds-client --api-key sk_live_xxx verify --proof "xxx" --data "{}"
bds-client --api-key sk_live_xxx purchase --asset-id "V-xxx" --qty 1
```

## 方法参考
见 `bds_client.py` 类 `BDSClient`。
