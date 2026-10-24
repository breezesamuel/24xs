# Schema.org 结构化数据（贴到页面 <head> 或页面底部）

> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。
> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Service",
  "name": "本地生活（教培/健身/汽修）AI落地服务",
  "serviceType": "本地生活（教培/健身/汽修）AI咨询与实施",
  "areaServed": "CN",
  "provider": {
    "@type": "Organization",
    "name": "上海丙大山智能科技有限公司"
  },
  "audience": {
    "@type": "BusinessAudience",
    "audienceType": "门店老板"
  },
  "offers": {
    "@type": "Offer",
    "priceCurrency": "CNY",
    "price": "12000",
    "description": "到店咨询量 +30%，员工内容产出从 0 到每周 7 条"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "本地生活（教培/健身/汽修）服务目录",
    "itemListElement": [
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "门店内容日历",
          "description": "每周 5 条图文+2条短视频，含团购文案"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "私域自动回复",
          "description": "社群/企微问题自动应答 + 到店提醒"
        }
      },
      {
        "@type": "Offer",
        "itemOffered": {
          "@type": "Service",
          "name": "老客召回脚本",
          "description": "按消费周期自动发个性化召回"
        }
      }
    ]
  }
}
</script>
```
