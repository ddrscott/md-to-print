# ASCII Diagram Test

Here's a deployment lifecycle diagram:

```bob
┌─────────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT RECORD LIFECYCLE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   DEPLOY TRIGGERED                                                   │
│   (user or workflow initiates deployment)                            │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────────┐                                               │
│   │ DEPLOYMENT      │  createDeployment() captures:                  │
│   │ RECORD CREATED  │  - ymirYmlVersion                              │
│   │                 │  - siteManifestVersion                         │
│   └────────┬────────┘  - dockerfileVersion                           │
│            │           - combinedHash (for deduplication)            │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │ INFRASTRUCTURE  │  ymir project:deploy executes                  │
│   │ DEPLOYED        │  - Lambda updated                              │
│   └────────┬────────┘  - CloudFront invalidated                      │
│            │                                                         │
│            ▼                                                         │
│   ┌─────────────────┐                                               │
│   │ ENVIRONMENT     │  recordDeploymentToEnvironment():              │
│   │ LINKED          │  - deployedDeploymentId = deployment.id        │
│   └─────────────────┘  - Cache fields updated for UI                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

And a simpler flow:

```ascii
    .----.      .----.      .----.
   | User | -> | API  | -> | DB   |
    '----'      '----'      '----'
```
