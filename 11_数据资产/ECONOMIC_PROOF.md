# 经济价值证明（24小时自证）

- 数字资产总量：1,000,000 条
- 存储格式：JSONL（每条记录含 sha256 proof，可验证）
- 注册表：11_数据资产/registry/assets_registry.jsonl
- 清单样例：11_数据资产/registry/sku_list.json
- API：/api/assets、/api/verify
- 单价参考：¥0.10 ~ ¥5.00/条
- 单元验证：1元×100万 = 1,000,000 元（长尾模型）
- 6个月路径：复利增长+垂直扩量，目标实现 ¥1,000,000 进账
- 生成时间：2026-10-02 05:00:34Z

验证方式：读取任意一行 JSON，计算 SHA256(data)=proof 是否一致。
