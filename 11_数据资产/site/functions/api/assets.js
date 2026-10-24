export async function onRequest(context) {
  const url = new URL(context.request.url)
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '100'), 500)
  const offset = Math.max(parseInt(url.searchParams.get('offset') || '0'), 0)
  const manifest = {
    total: 1000000,
    format: 'jsonl',
    path: '11_数据资产/registry/assets_registry.jsonl'
  }
  return new Response(JSON.stringify({
    ok: true,
    ...manifest,
    offset,
    limit
  }), {
    headers: { 'content-type': 'application/json; charset=utf-8' }
  })
}
