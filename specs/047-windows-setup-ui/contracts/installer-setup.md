# Installer setup contract

The internal operations are available only to the installed Windows helper. Execute the known absolute executable under the same unelevated user as the wizard. If that identity cannot be guaranteed, defer guided setup and direct the operator to run the CLI from their user session.

| Operation | Input | Result |
| --- | --- | --- |
| `setup --installer-ui read` | No wizard values | Versioned redacted fields and a saved-key boolean. Include an opaque, nonsecret token for detecting stale edits to visible fields. An absent profile returns defaults without writing. |
| `setup --installer-ui save` | Versioned editable fields, token, optional replacement key in a process-only environment envelope | Success or fixed error/status codes keyed to invalid fields, stale state or write failure. Only this call can carry the replacement key. |
| `setup --installer-ui start` | No wizard values. Called only after explicit consent and successful save. | Fixed statuses for prerequisite, startup and provisioning outcomes. Report whether the stack started when bank provisioning fails. |

Use an ordered, versioned UTF-8 field protocol with explicit escaping for the captured read output. Store the save request in a process-scoped environment envelope using separate allowlisted Unicode variables for typed fields, with no shell interpolation. Restore the wizard process environment in a finally path and remove the payload from the helper environment on entry before any downstream subprocess. Reject unsupported protocol versions and unexpected control characters, and validate again in Python. Use allowlisted statuses to render errors. Never log raw helper output or exception bodies. Keep the stored key out of the read protocol, even on failure.
