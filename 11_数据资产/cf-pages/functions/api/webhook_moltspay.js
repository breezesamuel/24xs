export async function onRequest(context) {
  // MoltsPay x402 webhook verification
  // Expected headers: X-X402-Signature, X-X402-Timestamp
  // Body: raw JSON of payment event
  
  try {
    const sig = context.request.headers.get("X-X402-Signature")
    const ts = context.request.headers.get("X-X402-Timestamp")
    const rawBody = await context.request.text()
    
    if (!sig || !ts) {
      return new Response("Missing signature headers", {status: 400})
    }
    
    // Verify timestamp (300s tolerance)
    const now = Math.floor(Date.now() / 1000)
    if (Math.abs(now - parseInt(ts)) > 300) {
      return new Response("Timestamp expired", {status: 400})
    }
    
    // Verify HMAC-SHA256
    const secret = context.env.MOLTSPAY_WEBHOOK_SECRET
    if (!secret) {
      console.error("MOLTSPAY_WEBHOOK_SECRET not configured")
      return new Response("Server config error", {status: 503})
    }
    
    const encoder = new TextEncoder()
    const key = await crypto.subtle.importKey(
      "raw", encoder.encode(secret), {name: "HMAC", hash: "SHA-256"}, false, ["sign", "verify"]
    )
    const msg = encoder.encode(ts + "." + rawBody)
    const expectedSig = await crypto.subtle.sign("HMAC", key, msg)
    const expectedHex = Array.from(new Uint8Array(expectedSig)).map(b => b.toString(16).padStart(2, "0")).join("")
    
    if (expectedHex !== sig) {
      console.error("Signature mismatch")
      return new Response("Invalid signature", {status: 401})
    }
    
    // Parse event
    const event = JSON.parse(rawBody)
    const eventId = event.id
    
    // Idempotency check (use KV or D1 in production)
    // For now, process
    
    if (event.type === "payment.succeeded" || event.type === "charge.succeeded") {
      const assetId = event.metadata?.asset_id || event.custom || ""
      const amount = event.amount_cny || event.amount || 0
      
      if (assetId) {
        // Trigger delivery
        // In production: write to queue, send email, generate download link
        console.log("Payment confirmed:", {assetId, amount, eventId})
        
        // Here you would:
        // 1. Look up asset in registry
        // 2. Generate signed download URL (time-limited)
        // 3. Email buyer with link
        // 4. Record sale in ledger
      }
    }
    
    return new Response("OK", {status: 200})
  } catch (e) {
    console.error("Webhook error:", e)
    return new Response("Internal error", {status: 500})
  }
}
