export async function onRequest(context) {
  try {
    if (context.request.method !== 'POST') {
      return new Response(JSON.stringify({ok: false, error: 'method_not_allowed'}), {status: 405, headers: {'content-type': 'application/json'}})
    }
    
    const body = await context.request.json()
    const asset_id = body.asset_id || ''
    const amount_cny = body.amount_cny || 0
    
    if (!asset_id) {
      return new Response(JSON.stringify({ok: false, error: 'missing_asset_id'}), {status: 400, headers: {'content-type': 'application/json'}})
    }
    
    // MoltsPay / x402 integration placeholder
    // In production, this would create an x402 charge via MoltsPay API
    const checkout_url = `https://app.moltspay.com/checkout?amount=${amount_cny}&currency=CNY&desc=数字资产:${asset_id}&custom=${encodeURIComponent(asset_id)}`
    const payment_url = checkout_url
    
    return new Response(JSON.stringify({
      ok: true,
      asset_id,
      amount_cny,
      checkout_url,
      payment_url,
      note: '支付网关待完整配置（现为预发地址）。收到款项后自动交付资产文件。'
    }), {
      headers: {'content-type': 'application/json; charset=utf-8'}
    })
  } catch (e) {
    return new Response(JSON.stringify({ok: false, error: 'exception'}), {status: 500, headers: {'content-type': 'application/json'}})
  }
}
