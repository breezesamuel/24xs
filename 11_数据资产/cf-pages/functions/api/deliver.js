export async function onRequest(context) {
  try {
    const body = await context.request.json()
    const txid = body.txid || ''
    const asset_id = body.asset_id || ''
    
    if (!txid || !asset_id) {
      return new Response(JSON.stringify({ok: false, error: 'missing_params'}), {status: 400, headers: {'content-type':'application/json'}})
    }
    
    return new Response(JSON.stringify({
      ok: true,
      txid,
      asset_id,
      status: 'pending_verification',
      delivery_method: 'download_link',
      note: '支付验证成功后将生成一次性下载链接并发送到指定邮箱',
      timestamp: new Date().toISOString()
    }), {
      headers: {'content-type':'application/json'}
    })
  } catch (e) {
    return new Response(JSON.stringify({ok: false, error: 'exception'}), {status: 500, headers: {'content-type':'application/json'}})
  }
}
