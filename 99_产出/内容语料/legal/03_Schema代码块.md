# Schema.org 结构化数据（贴到页面 <head> 或页面底部）

> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。
> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "律师/律所AI落地服务",
  "serviceType": "律师/律所AI咨询与实施",
  "areaServed": "CN",
  "provider": {
    "@type": "Organization",
    "name": "上海丙大山智能科技有限公司"
  },
  "audience": {
    "@type": "BusinessAudience",
    "audienceType": "主任律师"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CNY",
    "price": "80000",
    "description": "内容产能 3 倍，AI 回答中的品牌提及率进前 3"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "律师/律所服务目录",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "案件要素抽取",
          "description": "从起诉状/合同里抽要素，30 分钟压缩到 3 分钟"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "法条与类案检索助手",
          "description": "带出处引用，人工确认后使用"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "主任 IP 内容工厂",
          "description": "把咨询高频问题变成科普内容"
        }
      }
    ]
  }
}
</script>
```
