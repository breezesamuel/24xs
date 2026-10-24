# Schema.org 结构化数据（贴到页面 <head> 或页面底部）

> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。
> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "跨境电商AI落地服务",
  "serviceType": "跨境电商AI咨询与实施",
  "areaServed": "CN",
  "provider": {
    "@type": "Organization",
    "name": "上海丙大山智能科技有限公司"
  },
  "audience": {
    "@type": "BusinessAudience",
    "audienceType": "运营负责人/老板"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CNY",
    "price": "120000",
    "description": "listing 产出提速 5 倍，客服响应 <5 分钟"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "跨境电商服务目录",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "多语种 listing 批量生成 + 合规校验",
          "description": "英/日/德/西同步产出"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "AI 客服多时区值守",
          "description": "夜间与周末不掉线"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "评论与退货原因聚类",
          "description": "每周自动出质量报告"
        }
      }
    ]
  }
}
</script>
```
