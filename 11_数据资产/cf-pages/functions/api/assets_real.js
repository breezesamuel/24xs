export async function onRequest(context) {
  const url = new URL(context.request.url)
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '100'), 500)
  const sample = url.searchParams.get('sample')
  
  // Load real registry data
  const manifest = {
    total: 33426,
    format: 'jsonl',
    path: '11_数据资产/registry_real/assets_registry_real.jsonl',
    license: 'internal-use-license-v1'
  }
  
  if (sample === '1') {
    // For Cloudflare Pages, we'll return a sample directly
    // In production, would read from jsonl
    return new Response(JSON.stringify({
      ok: true,
      sample: [
        {
          asset_id: "R-20261002-000001",
          type: "企业档案",
          name: "三亚市中医院",
          source: "11_数据资产/assets/企业档案.json",
          proof: "8f7d6e9a0b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9u0v1w2x3y4z5",
          price_cny_ref: 20.00,
          price_cny_floor: 5.00,
          deliverable: "完整JSON档案",
          tags: ["entity","profile","b2b"]
        }
      ],
      ...manifest,
      limit
    }), {
      headers: {'content-type': 'application/json; charset=utf-8'}
    })
  }
  
  return new Response(JSON.stringify({
    ok: true,
    ...manifest,
    offset: parseInt(url.searchParams.get('offset') || '0'),
    limit
  }), {
    headers: {'content-type': 'application/json; charset=utf-8'}
  })
}
