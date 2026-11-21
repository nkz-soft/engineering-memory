# Research

## Provider identifier and route

OpenRouter publishes `openai/gpt-oss-20b`. LiteLLM routes native OpenRouter models by prepending `openrouter/`, so the installed value under `PRODUCT_PROVIDER_MODEL` is `openrouter/openai/gpt-oss-20b`. Keep `PRODUCT_PROVIDER_API_BASE` at the editable preset `https://openrouter.ai/api/v1`. The existing `engineering-extraction` alias remains the model requested by Hindsight. Confirm the mapping with the pinned LiteLLM image and a controlled completion during implementation. [OpenRouter model](https://openrouter.ai/openai/gpt-oss-20b) · [LiteLLM provider documentation](https://docs.litellm.ai/docs/providers/openrouter)

## Wizard and profile ownership

Use the installed PyInstaller onedir executable from the new wizard page after the file installation step. A shared helper avoids an additional packaged runtime and keeps transactional profile rules in Python. Writing profile files directly from Pascal would duplicate parsing, validation, ACL, locking and recovery. Continuing to launch the terminal would retain the existing extra UI step.

Use Inno's capture API to invoke the helper without a console and read its allowlisted output. Use a temporary process environment value for the save operation, with no persistent environment change. This works through a same-user launch and avoids a plaintext handoff file. Verify process inheritance and cleanup with the exact installer toolchain and PyInstaller bootstrap. [Inno Setup ExecAndCaptureOutput](https://jrsoftware.org/inno-setup/documentation/topic_isxfunc_execandcaptureoutput.htm) · [Windows process inheritance](https://learn.microsoft.com/en-us/windows/win32/procthread/inheritance)
