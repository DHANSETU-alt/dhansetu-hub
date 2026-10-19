# DNS flow: annotated launch path

```mermaid
flowchart LR
 A[Wrong A 104.x/172.x]:::bad --> CF[Cloudflare]
 U[Browser] --> CF
 CF -->|1 delete wrong A| D[CNAME @ + www -> dhansetu-hub.onrender.com]
 D -->|2 Render custom domain| R[Render edge]
 R -->|3 health 200| O[Next.js origin]
 classDef bad fill:#401010,color:#ff7777; classDef good fill:#10351d,color:#66ff99;
```

Fix order: delete conflicting A/AAAA records; add CNAMEs; attach both domains in Render; purge cache; verify `/api/health`.
