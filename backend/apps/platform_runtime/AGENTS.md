# Platform Runtime Domain Contract

## Ownership

`platform_runtime` owns generic contracts and operational records for
Background Tasks, Webhook Events, Realtime Events, and Runtime Logs. It does
not own Domain App business models or business semantics.

## Public interface

- `apps.platform_runtime.tasks`: public task decorator and task contract.
- `apps.platform_runtime.webhooks`: public provider registration, inbound
  verification, and replay contract.
- `apps.platform_runtime.realtime`: public `publish_realtime_event` contract;
  notifications are best-effort and safe payloads only.
- `apps.platform_runtime.maintenance`: public retention cleanup operation for
  deployment maintenance processes.

Other apps must not import private task signal wiring or backend internals.
`models`, `observability`, `redaction`, `signals`, and `consumers` are private
implementation details unless a later contract explicitly promotes them.

## Dependencies

- Platform Runtime may depend on Django task contracts and `core` shared model
  primitives.
- Domain Apps may consume Platform Runtime public interfaces but must own their
  own business state and idempotency semantics.

## Rules for changes

- Keep task contracts backend-neutral.
- Do not persist task arguments or unrestricted return values in Runtime Logs.
- Add retries, idempotency, transactions, and post-commit behavior through
  later reliability slices rather than hiding them in the basic contract.
