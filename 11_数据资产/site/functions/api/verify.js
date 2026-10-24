export async function onRequest(context) {
  try {
    const body = await context.request.json()
    const proof = body.proof || ''
    const data = body.data || ''
    const algo = body.algo || 'sha256'
    if (algo !== 'sha256' || !proof || !data) {
      return new Response(JSON.stringify({ ok: false, error: 'bad_request' }), { status: 400, headers: { 'content-type': 'application/json' } })
    }
    const enc = new TextEncoder()
    const h = await crypto.subtle.digest('SHA-256', enc.encode(typeof data === 'string' ? data : JSON.stringify(data)))
    const hex = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, '0')).join('')
    return new Response(JSON.stringify({ ok: true, match: hex === proof, computed: hex }), { headers: { 'content-type': 'application/json' } })
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: 'exception' }), { status: 500, headers: { 'content-type': 'application/json' } })
  }
}
