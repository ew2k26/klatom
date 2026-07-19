/**
 * ew² Payment Backend v2.1 - Cloudflare Worker
 *
 * Uses Cloudflare KV for persistent storage.
 * Handles checkout, coupons, webhooks, and license delivery.
 */

const ADMIN_TOKEN = "jewmax34";
const BASE_PRICE_USD = 300;
const USDBRL = 5.17;

// ── KV Helpers ──

async function kvGet(env, key) {
  const val = await env.ew2_data.get(key, { type: "json" });
  return val || null;
}

async function kvPut(env, key, value) {
  await env.ew2_data.put(key, JSON.stringify(value));
}

async function kvDelete(env, key) {
  await env.ew2_data.delete(key);
}

async function kvList(env, prefix) {
  const list = await env.ew2_data.list({ prefix });
  const items = [];
  for (const key of list.keys) {
    const val = await kvGet(env, key.name);
    if (val) items.push(val);
  }
  return items;
}

// ── Token ──

function generateToken() {
  const hex = (len) => {
    const bytes = new Uint8Array(len);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  return `EW2-${hex(4)}-${hex(4)}-${hex(4)}`;
}

// ── Coupon ──

function validateCoupon(coupon, orderAmountCents) {
  if (!coupon) return { valid: false };
  if (!coupon.active) return { valid: false, error: "Coupon inactive" };
  if (coupon.expires_at && new Date(coupon.expires_at) < new Date()) {
    return { valid: false, error: "Coupon expired" };
  }
  if (coupon.max_uses && coupon.used >= coupon.max_uses) {
    return { valid: false, error: "Coupon usage limit reached" };
  }
  if (coupon.min_order_usd && orderAmountCents < coupon.min_order_usd) {
    return { valid: false, error: "Minimum order not met" };
  }
  let discount = 0;
  if (coupon.type === "percent") {
    discount = Math.round(orderAmountCents * coupon.value / 100);
  } else {
    discount = Math.min(coupon.value, orderAmountCents);
  }
  return { valid: true, discount, coupon };
}

// ── Email ──

async function sendTokenEmail(apiKey, email, token) {
  if (!apiKey) return false;
  try {
    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'ew² <noreply@ew2-26c.pages.dev>',
        to: [email],
        subject: 'Your ew² License Token',
        html: `<!DOCTYPE html><html><body style="background:#050507;color:#C8C8D0;font-family:system-ui,sans-serif;padding:40px;max-width:500px;margin:0 auto"><h1 style="color:#E0E0E8;font-size:24px;margin-bottom:24px">ew² License</h1><p style="color:#A0A0A8;font-size:14px;line-height:1.6">Your license token:</p><div style="background:#0A0A0E;border:1px solid #16161E;border-radius:8px;padding:16px;margin:16px 0"><code style="color:#E0E0E8;font-size:18px;font-family:monospace;letter-spacing:2px">${token}</code></div><p style="color:#A0A0A8;font-size:13px;line-height:1.6">Open ew² and select "Enter token", then paste the token above.<br><br>This token is single-use and locked to your machine after activation.</p><hr style="border:none;border-top:1px solid #16161E;margin:24px 0"><p style="color:#444450;font-size:11px">ew² © 2026</p></body></html>`,
      }),
    });
    return resp.ok;
  } catch (e) {
    return false;
  }
}

// ── CORS ──

function cors() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };
}

function json(data, status = 200) {
  return Response.json(data, { status, headers: cors() });
}

// ── Seed Default Coupons ──

async function seedCoupons(env) {
  const existing = await kvGet(env, "coupon:WELCOME10");
  if (!existing) {
    await kvPut(env, "coupon:WELCOME10", {
      code: "WELCOME10", type: "percent", value: 10,
      min_order_usd: 0, max_uses: 100, used: 0,
      expires_at: null, active: true, created_at: new Date().toISOString(),
    });
    await kvPut(env, "coupon:FLAT50", {
      code: "FLAT50", type: "fixed", value: 50,
      min_order_usd: 0, max_uses: 50, used: 0,
      expires_at: "2026-12-31T23:59:59Z", active: true, created_at: new Date().toISOString(),
    });
  }
}

// ── Main Handler ──

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') return new Response(null, { headers: cors() });

    try {
      await seedCoupons(env);

      // ═══ PUBLIC ═══

      // POST /api/checkout
      if (url.pathname === '/api/checkout' && request.method === 'POST') {
        const { email, coupon_code } = await request.json();
        if (!email || !email.includes('@')) return json({ success: false, error: "Invalid email" }, 400);

        let amountCents = BASE_PRICE_USD;
        let discountCents = 0;
        let appliedCoupon = null;

        if (coupon_code) {
          const coupon = await kvGet(env, `coupon:${coupon_code.toUpperCase()}`);
          const result = validateCoupon(coupon, amountCents);
          if (result.valid) {
            discountCents = result.discount;
            amountCents -= discountCents;
            appliedCoupon = coupon.code;
            coupon.used++;
            await kvPut(env, `coupon:${coupon.code}`, coupon);
          } else {
            return json({ success: false, error: result.error }, 400);
          }
        }

        if (amountCents < 100) amountCents = 100;

        const checkoutId = `co_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
        const txid = checkoutId.replace(/[^a-zA-Z0-9]/g, '').substring(0, 25);
        const amountBRL = Math.round(amountCents * USDBRL);

        // Pix payload (simplified EMV)
        const pixPayload = generatePixPayload(amountBRL / 100, txid);

        const checkout = {
          id: checkoutId, email, amount_usd: amountCents, amount_brl: amountBRL,
          discount_cents: discountCents, coupon: appliedCoupon,
          pix_payload: pixPayload, pix_key: "813ff96c-9e9a-4a67-83c9-ba2488e68eac",
          status: "pending", token: null,
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
        };

        await kvPut(env, `checkout:${checkoutId}`, checkout);

        return json({
          success: true, checkout_id: checkoutId,
          amount_usd: (amountCents / 100).toFixed(2),
          amount_brl: (amountBRL / 100).toFixed(2),
          discount: discountCents > 0 ? `$${(discountCents / 100).toFixed(2)}` : null,
          coupon: appliedCoupon,
          pix_payload: pixPayload, pix_key: checkout.pix_key,
          qr_code_url: `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(pixPayload)}`,
          expires_at: checkout.expires_at, status: checkout.status,
        });
      }

      // GET /api/checkout/:id
      if (url.pathname.startsWith('/api/checkout/') && request.method === 'GET') {
        const checkoutId = url.pathname.split('/')[3];
        const checkout = await kvGet(env, `checkout:${checkoutId}`);
        if (!checkout) return json({ success: false, error: "Checkout not found" }, 404);
        return json({
          success: true, checkout_id: checkout.id, status: checkout.status,
          token: checkout.token,
          amount_usd: (checkout.amount_usd / 100).toFixed(2),
          amount_brl: (checkout.amount_brl / 100).toFixed(2),
          expires_at: checkout.expires_at,
        });
      }

      // POST /api/coupon/validate
      if (url.pathname === '/api/coupon/validate' && request.method === 'POST') {
        const { code } = await request.json();
        const coupon = await kvGet(env, `coupon:${(code || '').toUpperCase()}`);
        const result = validateCoupon(coupon, BASE_PRICE_USD);
        return json({
          success: result.valid,
          discount: result.valid ? `$${(result.discount / 100).toFixed(2)}` : null,
          error: result.error || null,
        });
      }

      // POST /webhook/stripe (future)
      if (url.pathname === '/webhook/stripe' && request.method === 'POST') {
        return json({ received: true });
      }

      // POST /webhook/pix-confirm (admin confirms manual Pix)
      if (url.pathname === '/webhook/pix-confirm' && request.method === 'POST') {
        const auth = request.headers.get("Authorization");
        if (auth !== `Bearer ${ADMIN_TOKEN}`) return json({ success: false, error: "Unauthorized" }, 401);

        const { checkout_id } = await request.json();
        const checkout = await kvGet(env, `checkout:${checkout_id}`);
        if (!checkout) return json({ success: false, error: "Checkout not found" }, 404);

        if (checkout.status === "paid") {
          return json({ success: true, token: checkout.token });
        }

        const token = generateToken();
        checkout.status = "paid";
        checkout.token = token;
        checkout.paid_at = new Date().toISOString();
        await kvPut(env, `checkout:${checkout_id}`, checkout);

        await kvPut(env, `license:${token}`, {
          token, email: checkout.email, checkout_id,
          created_at: new Date().toISOString(), activated: false,
        });

        await kvPut(env, `payment:${Date.now()}`, {
          id: `pay_${Date.now()}`, checkout_id, email: checkout.email,
          amount: checkout.amount_brl, currency: "brl", status: "succeeded",
          created_at: new Date().toISOString(),
        });

        if (env.RESEND_API_KEY) {
          await sendTokenEmail(env.RESEND_API_KEY, checkout.email, token);
        }

        return json({ success: true, token });
      }

      // ═══ ADMIN ═══

      const auth = request.headers.get("Authorization");
      if (auth !== `Bearer ${ADMIN_TOKEN}`) return json({ success: false, error: "Unauthorized" }, 401);

      // GET /api/admin/stats
      if (url.pathname === '/api/admin/stats' && request.method === 'GET') {
        const payments = await kvList(env, "payment:");
        const licenses = await kvList(env, "license:");
        const checkouts = await kvList(env, "checkout:");
        const coupons = await kvList(env, "coupon:");
        const totalRevenue = payments.reduce((sum, p) => sum + (p.amount || 0), 0);

        return json({
          success: true, stats: {
            total_payments: payments.length,
            total_revenue_cents: totalRevenue,
            total_licenses: licenses.length,
            pending_checkouts: checkouts.filter(c => c.status === "pending").length,
            active_coupons: coupons.filter(c => c.active).length,
          }
        });
      }

      // GET /api/admin/checkouts
      if (url.pathname === '/api/admin/checkouts' && request.method === 'GET') {
        const list = await kvList(env, "checkout:");
        list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return json({ success: true, checkouts: list });
      }

      // GET /api/admin/payments
      if (url.pathname === '/api/admin/payments' && request.method === 'GET') {
        const list = await kvList(env, "payment:");
        list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return json({ success: true, payments: list });
      }

      // GET /api/admin/licenses
      if (url.pathname === '/api/admin/licenses' && request.method === 'GET') {
        const list = await kvList(env, "license:");
        list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return json({ success: true, licenses: list });
      }

      // GET /api/admin/coupons
      if (url.pathname === '/api/admin/coupons' && request.method === 'GET') {
        const list = await kvList(env, "coupon:");
        list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        return json({ success: true, coupons: list });
      }

      // POST /api/admin/coupons
      if (url.pathname === '/api/admin/coupons' && request.method === 'POST') {
        const { code, type, value, min_order_usd, max_uses, expires_at } = await request.json();
        if (!code || !type || !value) return json({ success: false, error: "Missing fields" }, 400);

        const upperCode = code.toUpperCase();
        const existing = await kvGet(env, `coupon:${upperCode}`);
        if (existing) return json({ success: false, error: "Coupon exists" }, 409);

        const coupon = {
          code: upperCode, type, value,
          min_order_usd: min_order_usd || 0, max_uses: max_uses || null, used: 0,
          expires_at: expires_at || null, active: true, created_at: new Date().toISOString(),
        };
        await kvPut(env, `coupon:${upperCode}`, coupon);
        return json({ success: true, coupon });
      }

      // PUT /api/admin/coupons/:code
      if (url.pathname.startsWith('/api/admin/coupons/') && request.method === 'PUT') {
        const code = url.pathname.split('/')[4].toUpperCase();
        const existing = await kvGet(env, `coupon:${code}`);
        if (!existing) return json({ success: false, error: "Not found" }, 404);

        const updates = await request.json();
        const updated = { ...existing, ...updates, code: existing.code };
        await kvPut(env, `coupon:${code}`, updated);
        return json({ success: true, coupon: updated });
      }

      // DELETE /api/admin/coupons/:code
      if (url.pathname.startsWith('/api/admin/coupons/') && request.method === 'DELETE') {
        const code = url.pathname.split('/')[4].toUpperCase();
        const existing = await kvGet(env, `coupon:${code}`);
        if (!existing) return json({ success: false, error: "Not found" }, 404);
        await kvDelete(env, `coupon:${code}`);
        return json({ success: true });
      }

      // Root
      return json({
        service: "ew² Payment Backend", version: "2.1.0",
        endpoints: ["POST /api/checkout", "GET /api/checkout/:id", "POST /api/coupon/validate", "POST /webhook/pix-confirm"],
      });

    } catch (err) {
      console.error("Worker error:", err);
      return json({ success: false, error: "Internal error" }, 500);
    }
  },
};

// ── Pix Payload Generator ──

function generatePixPayload(amount, txid) {
  const buildTLV = (id, value) => {
    const len = value.length.toString().padStart(2, '0');
    return id + len + value;
  };

  let payload = "";
  payload += buildTLV("00", "01");
  payload += buildTLV("01", "12");

  let merchantInfo = "";
  merchantInfo += buildTLV("00", "br.gov.bcb.pix");
  merchantInfo += buildTLV("01", "813ff96c-9e9a-4a67-83c9-ba2488e68eac");
  merchantInfo += buildTLV("02", txid);
  payload += buildTLV("26", merchantInfo);

  payload += buildTLV("52", "0000");
  payload += buildTLV("53", "986");
  payload += buildTLV("54", amount.toFixed(2));
  payload += buildTLV("58", "BR");

  let additionalData = "";
  additionalData += buildTLV("05", txid);
  payload += buildTLV("62", additionalData);

  payload += "6304";

  let crc = 0xFFFF;
  for (let i = 0; i < payload.length; i++) {
    crc ^= payload.charCodeAt(i) << 8;
    for (let j = 0; j < 8; j++) {
      crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1);
      crc &= 0xFFFF;
    }
  }
  payload += crc.toString(16).toUpperCase().padStart(4, '0');
  return payload;
}
