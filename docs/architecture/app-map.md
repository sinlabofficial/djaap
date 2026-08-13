# Application Map

This starterkit serves one organization per deployment. Cross-domain imports
are default-deny and must use an explicit public interface.

| App | Owns | Public boundary |
| --- | --- | --- |
| `core` | global users, roles, permissions, and organization settings | models, selectors, and services used by platform adapters |
| `platform_runtime` | generic tasks, webhooks, realtime events, and operational Runtime Logs | `tasks`, `realtime`, `webhooks`, and `maintenance` public interfaces |
| `dashboard` | session-authenticated Django template UI | views, forms, selectors, and services for server-rendered flows |
| `api` | optional REST integration adapter | serializers and viewsets for external clients |
| `example` | replaceable Domain App reference and Item CRUD flow | its own selectors, services, forms, and templates; `core.selectors.user_has_permission` for RBAC |

`dashboard` and `api` may adapt `core`, `platform_runtime`, and Domain App
public interfaces. Domain Apps may consume only the explicitly listed
`platform_runtime` public modules and must not import another app's private
models, views, forms, admin modules, observability, or task signal wiring.
Workspace, Data, and Agent apps are intentionally absent.
