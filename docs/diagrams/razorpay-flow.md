# Razorpay payment flow

```mermaid
flowchart LR
 B[Browser CTA] --> C[Cloudflare DNS]
 C --> R[Render Custom Domain]
 R --> M[Next.js middleware]
 M --> CO[/api/payment/create-order]
 CO --> RP[Razorpay Checkout]
 RP --> WH[/api/payment/webhook]
 WH --> S[Signature verification]
 S --> E[lib/payment/entitlement.ts]
 E --> G[Grant access]
 G --> OK[HTTP 200 + payment success]
 X[Error 1000]:::bad -. blocks CTA before checkout .-> C
 classDef bad fill:#3a0a0a,color:#ff4444,stroke:#ff4444;
```
