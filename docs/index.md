# Welcome to the Eden Documentation 🌿

Eden is a high-performance, async-first web framework designed for developers who value aesthetics, security, and developer experience.

---

## 🚀 Getting Started

Learn the core concepts and the philosophy behind the framework.

- **[The Eden Philosophy](guides/philosophy.md)**: Why we built an "Integrated Framework" and how it solves micro-framework fatigue.
- **[Quickstart Guide](getting-started/quickstart.md)**: Get your first app running in 30 seconds.


## 🏢 Scaling & Architecture

Deep dives into the advanced features that make Eden production-ready.

- **[Multi-Tenancy Master Class](guides/multi-tenancy.md)**: Implementing Row-Level and Dedicated Schema isolation at scale.
- **[Identity & RBAC Master Class](guides/identity-rbac.md)**: Managing users, hierarchies, and model-level security rules.
- **[Advanced UI Orchestration](guides/advanced-ui-orchestration.md)**: Mastering the Widget Engine, Action Engine, and Asset Bundling.

## 🛠️ Productivity Recipes

Practical guides for common development tasks.

- **[The Model-to-Form Bridge](recipes/forms-and-validation.md)**: Automatically deriving high-fidelity forms from your database models.
- **[Storage & File Management](guides/storage.md)**: Local, S3, and Cloudfront integration.
- **[Payments with Stripe](guides/payments.md)**: Subscriptions, checkouts, and webhooks.


---

## 🛡️ Security First

Eden is built on a "Defense in Depth" philosophy.

- **Fail-Secure Tenancy**: Queries return empty results by default if no tenant is found.
- **CSRF & Security Headers**: Integrated middleware protects your app out of the box.
- **Unified Auth API**: A single entry point for all authentication needs.

---

## 🧘 Standard Practice: The Single-Tenant Project

Building a simple side project or a single-tenant application? You can ignore the `tenancy` modules completely. Eden operates as a standard, high-performance web framework by default.

**Tenancy is an opt-in enhancement, not a requirement.**
