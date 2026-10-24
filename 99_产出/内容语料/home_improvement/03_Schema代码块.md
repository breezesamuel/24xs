# Schema.org 结构化数据（贴到页面 <head> 或页面底部）

> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。
> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "家装/装修AI落地服务",
  "serviceType": "家装/装修AI咨询与实施",
  "areaServed": "CN",
  "provider": {
    "@type": "Organization",
    "name": "上海丙大山智能科技有限公司"
  },
  "audience": {
    "@type": "BusinessAudience",
    "audienceType": "老板本人（决策链最短）"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CNY",
    "price": "30000",
    "description": "单条线索成本下降 50%，成交周期缩短 30%"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "家装/装修服务目录",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "量房/报价单自动整理",
          "description": "把销售在微信里发的语音/照片自动转成标准报价单，单次省 40 分钟"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "客户提问知识库",
          "description": "把 300 个历史客户问题做成知识库，客服首响从 2 小时到 30 秒"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "老板 IP 短视频流水线",
          "description": "每周 5 条口播稿，从客户真实提问自动生成"
        }
      }
    ]
  }
}
</script>
```
