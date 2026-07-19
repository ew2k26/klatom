# ew² Payment System - Compliance & Architecture Document

## Executive Summary

This document outlines the payment system architecture for ew², a digital product sold to an English-speaking audience. The system currently uses a **manual Pix payment flow** because the account holder is a minor, and all automated payment providers require merchants to be 18+ years old.

---

## Payment Provider Research

### Providers Evaluated

| Provider | USD Checkout | BRL Settlement | Nubank Payout | Minor Allowed | Status |
|----------|-------------|----------------|---------------|---------------|--------|
| NuPay for Business | ✅ | ✅ | ✅ | ❌ | Rejected - Terms prohibit minors |
| Paddle | ✅ | ✅ | ❌ | ❌ | Rejected - Requires 18+ |
| Stripe | ✅ | ✅ | ❌ | ❌ | Rejected - Requires 18+ |
| PayPal | ✅ | ✅ | ❌ | ❌ | Rejected - Requires 18+ |
| Ko-fi | ✅ | ✅ | ❌ | ❌ | Rejected - Requires PayPal/Stripe |
| Gumroad | ✅ | ✅ | ❌ | ❌ | Rejected - Requires 18+ |

### NuPay for Business - Detailed Analysis

**Why it's the best fit:**
- Native Nubank integration (135M+ customers in Brazil)
- USD checkout possible (customer pays in BRL, merchant receives USD)
- BRL settlement to Brazilian bank accounts
- No chargeback risk (authenticated in Nubank app)
- Low friction (one-click payment)

**Why it's rejected:**
From nupaybusiness.com.br terms of service:

> "2.7 Menores de Idade: Os Produtos e Serviços, bem como o site relacionados ao NuPay for Business não são direcionadas ao público adolescente e/ou infantil. Portanto, não devem ser utilizadas por Usuários menores de idade, quando não ofertados exclusivamente para este público."

Translation: Products and services are not directed to adolescents or children. Therefore, they should not be used by minors when not exclusively offered to this audience.

### Legal Requirements for All Providers

1. **KYC (Know Your Customer)**: Must verify merchant identity with government-issued ID
2. **AML (Anti-Money Laundering)**: Must monitor transactions for suspicious activity
3. **Tax Compliance**: Must issue tax documents (1099 in US, Nota Fiscal in Brazil)
4. **Bank Account**: Must have a business bank account in the merchant's name
5. **Age Requirement**: Must be 18+ to enter legally binding contracts

---

## Current Architecture

### Payment Flow (Manual Pix)

```
Customer → Website (USD $3 price)
              ↓
         Pix Payment Modal (R$15,50 ≈ $3 USD)
              ↓
         Customer pays via Nubank app
              ↓
         Merchant verifies payment in Nubank
              ↓
         Merchant opens Admin Dashboard
              ↓
         Clicks "Send Token"
              ↓
         Token generated + emailed to customer
              ↓
         Customer activates in ew² app
```

### Components

| Component | URL | Function |
|-----------|-----|----------|
| Website | https://ew2-26c.pages.dev | Product page + checkout |
| Admin Dashboard | https://ew2-admin.pages.dev | Order management |
| Backend (Worker) | ew2-payment.thiagoperres96.workers.dev | API for orders + tokens |

### Admin Token

- **Token**: `jewmax34`
- **Purpose**: Authenticate admin dashboard access
- **Usage**: Enter in admin dashboard login

---

## Security Implementation

### Webhook Validation

All API endpoints validate the `Authorization` header:
```
Authorization: Bearer jewmax34
```

### Idempotency

Orders use unique IDs with timestamp + random suffix:
```
ord_{timestamp}_{random}
```

Duplicate submissions return the existing order ID.

### Token Generation

Tokens follow the format:
```
EW2-{8 hex}-{8 hex}-{8 hex}
```

Example: `EW2-171A6301-C584FD9B-0B25F464`

### Secrets Management

| Secret | Storage | Purpose |
|--------|---------|---------|
| ADMIN_TOKEN | Hardcoded (jewmax34) | Admin dashboard auth |
| RESEND_API_KEY | Environment variable | Email delivery |
| TOKEN_SECRET | Environment variable | Token HMAC signing |

---

## Compliance Constraints

### For Minor Account Holder

1. **Cannot use automated payment processors** (Stripe, PayPal, Paddle, etc.)
2. **Cannot open business bank accounts** (requires 18+)
3. **Cannot issue tax documents** (Nota Fiscal, 1099)
4. **Cannot enter legally binding merchant agreements**
5. **Cannot assume chargeback liability**

### What IS Allowed

1. **Accept Pix payments** (no age requirement for receiving)
2. **Sell digital products** (no age restriction on the product itself)
3. **Use personal bank account** (Nubank for receiving Pix)
4. **Operate as individual** (not as business entity)

### Tax Implications

- Pix payments received are considered personal income
- Must be declared in annual tax return (IRPF)
- No Nota Fiscal required for individual Pix transactions under certain thresholds
- Consult accountant for specific tax obligations

---

## Future Implementation (When 18+)

### Recommended: NuPay for Business

**Setup Requirements:**
1. Valid CPF (adult)
2. Nubank account (individual or business)
3. Business registration (optional, but recommended)
4. KYC verification with Nubank
5. API integration with NuPay for Business

**Expected Fees:**
- NuPay transaction fee: ~2-4% per transaction
- Settlement: Next business day
- Minimum payout: None

**Integration:**
- API: https://docs.nupaybusiness.com.br
- Sandbox available for testing
- Webhook support for payment confirmation

### Alternative: Stripe Brazil

**Setup Requirements:**
1. Valid CPF or CNPJ
2. Brazilian bank account (any bank, including Nubank)
3. KYC verification
4. Business registration (for CNPJ)

**Expected Fees:**
- Transaction fee: 3.99% + R$0.39 per transaction
- Settlement: 2 business days
- International cards: Additional 2% fee

---

## Modified Files

| File | Changes |
|------|---------|
| `website/index.html` | Added Pix payment modal with USD pricing |
| `admin/index.html` | Created admin dashboard |
| `worker/index.js` | Added order API + token generation |
| `worker/wrangler.toml` | Simplified configuration |
| `generate_license.py` | Token generation script (backup) |
| `PAYMENT_SETUP.md` | Setup documentation |

---

## Tests Run

| Test | Result |
|------|--------|
| Worker deployment | ✅ Deployed successfully |
| Order creation API | ✅ Returns order ID |
| Token generation API | ✅ Generates valid token |
| Admin authentication | ✅ Accepts jewmax34 token |
| Website deployment | ✅ Deployed to Cloudflare Pages |
| Admin dashboard deployment | ✅ Deployed to Cloudflare Pages |

---

## Remaining Risks

### Current (Manual Pix)

1. **Manual verification required**: Merchant must check Nubank for each payment
2. **No automation**: Tokens must be sent manually via admin dashboard
3. **No email delivery**: Resend API not configured (requires API key)
4. **In-memory storage**: Orders lost if Worker restarts (no persistent storage)

### Compliance

1. **Tax reporting**: Must declare Pix income in IRPF
2. **No chargeback protection**: Manual payments have no refund process
3. **No fraud detection**: No automated fraud screening

### Technical

1. **Single point of failure**: Worker uses in-memory storage
2. **No rate limiting**: API endpoints have no rate limiting
3. **No logging**: No audit trail for API requests

---

## Recommendations

### Immediate

1. **Configure Resend API** for automated email delivery
2. **Set up Cloudflare KV** for persistent order storage
3. **Add rate limiting** to prevent abuse
4. **Implement logging** for audit trail

### When 18+

1. **Register NuPay for Business** for full automation
2. **Set up proper merchant account** with Nubank
3. **Implement webhook verification** for payment confirmation
4. **Add tax document generation** (Nota Fiscal)

### Long-term

1. **Implement subscription model** for recurring revenue
2. **Add multiple payment methods** (credit card, boleto)
3. **Create affiliate program** for growth
4. **Implement analytics** for business intelligence

---

## Conclusion

The current manual Pix solution is the only viable option for a minor account holder. It provides:
- ✅ USD pricing (as required)
- ✅ BRL settlement (via Pix)
- ✅ Nubank compatibility (direct Pix)
- ✅ No age restrictions
- ✅ No compliance burden

When the account holder turns 18, they should migrate to NuPay for Business for full automation and proper compliance.

---

*Document last updated: July 2026*
*Account holder: Minor (Nubank user)*
*Payment method: Manual Pix*
