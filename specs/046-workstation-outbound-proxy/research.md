# Research: Workstation outbound HTTP(S) proxy

## Compose routing

**Decision** — Use a static, bundled Compose override when a workstation profile opts into managed proxy routing. Forward the configured proxy only to LiteLLM. Interpolate private `WORKSTATION_` fields already covered by the environment filter. Explicitly set uppercase and lowercase HTTP(S), bypass and empty catch-all settings in that service. Docker client defaults can inject both cases. Clear those inherited proxy variables in Hindsight when the overlay is active to preserve direct local health and LiteLLM requests. Retain existing base Compose behavior for profiles without managed routing.

**Rationale** — Repository deployment already uses LiteLLM's proxy environment. A conditional override preserves the installed deployment's current behavior when disabled, including operator-managed Docker defaults. The profile owns effective routing when enabled. The same Compose project, mounts and volumes survive toggling the override. A normal `up` should recreate LiteLLM when effective configuration changes. Confirm this on the pinned deployment.

**Alternatives considered** — Unconditionally mapping variables in the base Compose file could change legacy behavior when Docker supplies proxy defaults. Configuring Docker globally would affect unrelated workloads and would put proxy changes outside the workstation wizard. A separate application-level proxy client would duplicate LiteLLM's provider transport.

## Endpoint semantics and validation

**Decision** — Store independent HTTP and HTTPS destination routes. Accept HTTP(S) endpoints, with optional URL-encoded userinfo. Document an HTTP forward proxy for an HTTPS provider using CONNECT and validate the pinned provider path with the actual image, including TLS to the proxy when using an HTTPS proxy URL. Preserve TLS verification. Use a container-reachable hostname such as `host.docker.internal` for an appropriately bound host proxy. Include loopback and local service aliases in the bypass.

**Rationale** — The destination scheme selects the routing variable. The provider API base still names the origin. Loopback inside a container identifies the container itself. Reusing provider URL validation would reject authenticated proxy URLs and conflate different endpoints.

## Diagnostics and evidence

**Decision** — Offer an explicit synthetic completion through the installed LiteLLM endpoint. Return fixed guidance on failure. Use a dedicated acceptance fixture with a proxy reachable from LiteLLM, an origin reachable only through the proxy and a trusted fixture CA where TLS is used.

**Rationale** — Stack health and rendered configuration do not exercise provider egress. A proxy-side observation plus failed direct control and successful completion distinguishes actual routing from a healthy container and from silent direct fallback. Proxy status may be obscured by LiteLLM, so give bounded generic guidance when the cause cannot be classified safely.

References: [Docker CLI proxy configuration](https://docs.docker.com/engine/cli/proxy/) and [HTTPX proxy semantics](https://www.python-httpx.org/advanced/proxies/).
