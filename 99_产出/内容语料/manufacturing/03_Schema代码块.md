# Schema.org 结构化数据（贴到页面 <head> 或页面底部）

> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。
> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "制造业（工业品/设备）AI落地服务",
  "serviceType": "制造业（工业品/设备）AI咨询与实施",
  "areaServed": "CN",
  "provider": {
    "@type": "Organization",
    "name": "上海丙大山智能科技有限公司"
  },
  "audience": {
    "@type": "BusinessAudience",
    "audienceType": "市场总监 / 外贸负责人"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CNY",
    "price": "250000",
    "description": "询盘量月均 +40%，单询盘成本下降 50%"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "制造业（工业品/设备）服务目录",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "参数知识库 + Schema 结构化",
          "description": "让 AI 能引用你的规格而不是编"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "询盘分级与自动回复",
          "description": "技术问题自动分类并路由给对应工程师"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "多语种技术白皮书",
          "description": "英/西/阿语，面向海外买家提问"
        }
      }
    ]
  }
}
</script>
```
