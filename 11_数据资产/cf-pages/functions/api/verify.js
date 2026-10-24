export async function onRequest(context) {
  try {
    const body = await context.request.json()
    const proof = body.proof || ""
    const parent_proof = body.parent_proof || ""
    const variant_index = body.variant_index || 0
    
    if (proof && parent_proof && variant_index) {
      const enc = new TextEncoder()
      const chain = parent_proof + ":variant:" + variant_index
      const h = await crypto.subtle.digest("SHA-256", enc.encode(chain))
      const hex = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("")
      return new Response(JSON.stringify({ok: true, match: hex === proof, computed: hex, type: "chain"}), {headers: {"content-type": "application/json"}})
    }
    
    // simple data verification
    const data = body.data || ""
    if (proof && data) {
      const enc = new TextEncoder()
      const h = await crypto.subtle.digest("SHA-256", enc.encode(typeof data === "string" ? data : JSON.stringify(data)))
      const hex = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("")
      return new Response(JSON.stringify({ok: true, match: hex === proof, computed: hex, type: "direct"}), {headers: {"content-type": "application/json"}})
    }
    
    return new Response(JSON.stringify({ok: false, error: "bad_request"}), {status: 400, headers: {"content-type": "application/json"}})
  } catch (e) {
    return new Response(JSON.stringify({ok: false, error: "exception"}), {status: 500, headers: {"content-type": "application/json"}})
  }
}
