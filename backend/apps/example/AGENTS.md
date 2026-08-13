# Example Domain App Contract

## Ownership

`example` owns the `Item` record and the Item CRUD workflow. It is a reference
domain app for the service/selector split, not a shared utility module.

## Public interface

- `apps.example.selectors`: read Item data.
- `apps.example.services`: create, update, or safe-delete Item data.
- `apps.example.contracts`: reserved for intentionally shared DTOs or
  protocols when this app gains a cross-domain consumer.

Other apps must not import `apps.example.models`, `views`, templates, admin,
forms, or private helpers.

## Dependencies

- Allowed platform dependencies: `apps.core.models.BaseModel` for the shared
  model base, `apps.core.selectors.user_has_permission` for global RBAC, and
  the public `apps.platform_runtime.tasks`, `.realtime`, `.webhooks`, and
  `.maintenance` modules.
- No domain-app dependencies are currently allowed.

## Rules for changes

- Keep Item writes in `services.py` and reads in `selectors.py`.
- Keep Django views as adapters; they call the public interface and do not
  contain Item business rules.
- If another domain needs an Item workflow, expose a narrow selector or service
  here, record it in `docs/architecture/app-map.md`, and add a contract test.
