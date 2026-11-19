"use strict";

const element = (id) => document.getElementById(id);
const unlock = element("unlock");
const workspace = element("workspace");
const lock = element("lock");
const key = element("access-key");
const project = element("project");
const query = element("query");
const results = element("results");
const evidence = element("evidence");
const messages = element("messages");
const first = element("first");
const next = element("next");
const statusPanel = element("status-panel");
const statusButton = element("show-status");
const statusRows = element("status-rows");
const statusFeedback = element("status-feedback");

let token = "";
let lookupRequest;
let conversationRequest;
let statusRequest;
let statusTimer;

const answerStates = {
  completed: "Answer ready.",
  partial: "Partial answer",
  insufficient_evidence: "There is insufficient evidence for an answer.",
  verification_failed: "The answer could not be verified.",
};

function textNode(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}

function action(label, callback) {
  const button = textNode("button", label, "quiet");
  button.type = "button";
  button.addEventListener("click", callback);
  return button;
}

function provenance(record) {
  const details = record.provenance;
  return [details.source, details.project, record.started_at, record.document_id]
    .filter(Boolean)
    .join(" · ");
}

function clearEvidence() {
  conversationRequest?.abort();
  evidence.hidden = true;
  messages.replaceChildren();
  element("conversation-provenance").textContent = "";
  element("evidence-status").textContent = "";
  first.hidden = true;
  next.hidden = true;
  first.onclick = null;
  next.onclick = null;
}

function clearResults() {
  lookupRequest?.abort();
  results.replaceChildren();
  element("query-status").textContent = "";
  element("results-heading").hidden = true;
  clearEvidence();
}

function showLock(message = "") {
  token = "";
  clearResults();
  closeStatus();
  workspace.hidden = true;
  lock.hidden = true;
  unlock.hidden = false;
  element("access-status").textContent = message;
  key.focus();
}

unlock.addEventListener("submit", (event) => {
  event.preventDefault();
  token = key.value.trim();
  key.value = "";
  if (!token) return;
  unlock.hidden = true;
  workspace.hidden = false;
  lock.hidden = false;
  project.focus();
  resolveSessionTarget();
});

lock.addEventListener("click", () => {
  project.value = "";
  query.value = "";
  showLock();
});

window.addEventListener("pagehide", () => {
  project.value = "";
  query.value = "";
  key.value = "";
  showLock();
});

async function read(operation, payload, signal) {
  const response = await fetch("/api/" + operation, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
    },
    body: JSON.stringify(payload),
    signal,
    cache: "no-store",
    credentials: "omit",
  });
  if (!response.ok) {
    if (response.status === 401 && !signal.aborted) {
      showLock("The key was rejected. Enter the current access key.");
    }
    if (response.status === 503) {
      const failure = await response.json();
      if (failure.error === "synthesis_unconfigured") {
        throw new Error("Deep Recall needs synthesis configuration.");
      }
    }
    const message = response.status === 400
      ? "Check the project slug and request."
      : "This operation is unavailable.";
    throw new Error(message);
  }
  return response.json();
}

const sourceLabels = {
  chatgpt: "ChatGPT", "claude-chat": "Claude Chat", "claude-code": "Claude Code", codex: "Codex",
};
const outcomeLabels = {
  healthy: "Healthy", waiting: "Waiting", partial: "Partial", failed: "Failed",
  unobserved: "No completed attempt recorded",
};
const errorLabels = {
  source: "Source", hash: "Content fingerprint", state_read: "Read import state",
  sanitize: "Sanitization", classify: "Classification", enrich: "Enrichment",
  archive: "Archive", retain: "Retention", state_write: "Write import state",
  configuration: "Configuration", state: "Import state", memory: "Memory service",
  internal: "Internal", unknown: "Unknown",
};
const modelLabels = { architecture: "Architecture", stack: "Technology stack", decisions: "Decisions" };
const refreshLabels = {
  ready: "Ready", missing: "Missing", pending: "Pending", failed: "Failed", unavailable: "Unavailable",
};
const freshnessLabels = { current: "Current", stale: "Stale", unknown: "Unknown" };

function resetStatus() {
  statusRequest?.abort();
  clearTimeout(statusTimer);
  statusRows.replaceChildren();
  statusFeedback.textContent = "";
}

function closeStatus() {
  resetStatus();
  statusPanel.hidden = true;
  statusButton.setAttribute("aria-expanded", "false");
}

function statusField(fields, label, value) {
  fields.append(textNode("dt", label), textNode("dd", value));
}

function statusGroup(title, records, display) {
  const section = document.createElement("section");
  section.append(textNode("h3", title));
  const grid = textNode("div", "", "status-grid");
  for (const record of records) {
    const row = textNode("article", "", "status-card");
    const fields = document.createElement("dl");
    const heading = display(record, fields);
    row.append(textNode("h4", heading), fields);
    grid.append(row);
  }
  section.append(grid);
  statusRows.append(section);
}

function renderStatus(data) {
  const stamp = (value) => value ?? "Not recorded";
  if (data.source_status === "unavailable") {
    statusRows.append(textNode("p", "Import status is unavailable."));
  } else {
    statusGroup("Import sources", data.sources, (source, fields) => {
      statusField(fields, "Latest outcome", outcomeLabels[source.outcome]);
      statusField(fields, "Last attempt", stamp(source.last_attempt_at));
      statusField(fields, "Last successful import", stamp(source.last_success_at));
      if (source.deferred_count) statusField(fields, "Deferred sessions", source.deferred_count);
      if (source.error_categories.length) {
        const labels = source.error_categories.map((category) => errorLabels[category] ?? "Unknown");
        statusField(fields, "Error categories", labels.join(", "));
      }
      return sourceLabels[source.source];
    });
  }
  if (data.models.length) {
    statusGroup("Project models", data.models, (model, fields) => {
      statusField(fields, "Refresh state", refreshLabels[model.refresh_state]);
      statusField(fields, "Freshness", freshnessLabels[model.freshness]);
      statusField(fields, "Last successful refresh", stamp(model.last_refreshed_at));
      if (model.last_refresh_failed_at) {
        statusField(fields, "Last failed refresh", model.last_refresh_failed_at);
      }
      return modelLabels[model.kind];
    });
  } else {
    statusRows.append(textNode("p", "Enter a project slug to check its models."));
  }
}

async function loadStatus() {
  resetStatus();
  if (!token || statusPanel.hidden) return;
  const scope = project.value.trim();
  const request = new AbortController();
  statusRequest = request;
  statusFeedback.textContent = "Reading status...";
  try {
    const data = await read("status", scope ? { project: scope } : {}, request.signal);
    if (request.signal.aborted) return;
    statusFeedback.textContent = "";
    renderStatus(data);
  } catch (error) {
    if (!request.signal.aborted) statusFeedback.textContent = error.message;
  }
}

statusButton.addEventListener("click", () => {
  if (!statusPanel.hidden) {
    closeStatus();
    return;
  }
  statusPanel.hidden = false;
  statusButton.setAttribute("aria-expanded", "true");
  loadStatus();
});

element("refresh-status").addEventListener("click", loadStatus);
function scheduleStatusRefresh() {
  if (statusPanel.hidden) return;
  resetStatus();
  statusTimer = setTimeout(loadStatus, 250);
}

project.addEventListener("input", scheduleStatusRefresh);

function showSearch(data, scope) {
  const status = element("query-status");
  if (!data.results.length) {
    status.textContent = "No matches in this project.";
    return;
  }
  const count = data.results.length;
  status.textContent = count === 1 ? "1 match" : count + " matches";
  for (const hit of data.results) {
    const row = textNode("article", "", "result");
    row.append(
      textNode("p", hit.content, "content"),
      textNode("p", provenance(hit), "metadata"),
      action("Open conversation", () => openConversation(hit.document_id, 0, scope)),
    );
    results.append(row);
  }
}

function showCoverage(data, label = "Coverage limitations") {
  if (data.uncertainty.length) {
    const details = document.createElement("details");
    details.append(
      textNode("summary", label),
      textNode("p", data.uncertainty.map((reason) => reason.replaceAll("_", " ")).join(" · ")),
    );
    results.append(details);
  }
}

function citedEvidence(anchor, scope, label) {
  const citation = textNode("blockquote", "", "citation");
  citation.append(
    textNode("p", anchor.quote, "content"),
    textNode("p", [anchor.document_id, anchor.timestamp].filter(Boolean).join(" · "), "metadata"),
    action(label, () => openConversation(anchor.document_id, anchor.message_index, scope, anchor)),
  );
  return citation;
}

function showAnswer(data, scope) {
  element("query-status").textContent = answerStates[data.status] ?? "Answer unavailable.";
  showCoverage(data);
  for (const entry of data.timeline) {
    const row = textNode("article", "", "result");
    row.append(textNode("p", entry.text, "content"));
    for (const anchor of entry.citations) {
      row.append(citedEvidence(anchor, scope, "Open cited message"));
    }
    results.append(row);
  }
}

const decisionStates = {
  completed: "Decision history ready.",
  partial: "Partial decision history.",
  insufficient_evidence: "There is insufficient evidence for this decision.",
  verification_failed: "The decision history could not be verified.",
};

const decisionKinds = {
  proposal: "Proposal",
  adoption: "Adoption",
  revision: "Revision",
  supersession: "Supersession",
};

function showDecisionEvents(events, scope, heading) {
  if (!events.length) return;
  results.append(textNode("h3", heading));
  const list = textNode("ol", "", "decision-events");
  for (const event of events) {
    const row = textNode("li", "", "result");
    const time = event.occurred_at ?? (
      event.chronology === "disputed" ? "Date disputed" : "Date unknown"
    );
    row.append(textNode("h4", decisionKinds[event.kind]), textNode("p", time, "metadata"));
    if (event.ordering_uncertain) row.append(textNode("p", "Order uncertain", "metadata"));
    if (event.prior_version) {
      row.append(textNode("p", "Previous version · " + event.prior_version, "content"));
    }
    row.append(textNode("p", event.version, "content"));
    if (event.reason) {
      row.append(textNode("p", event.reason, "content"));
    } else if (event.kind === "supersession") {
      row.append(textNode("p", "Reason undocumented", "metadata"));
    }
    row.append(citedEvidence(event.action, scope, "Open event source"));
    for (const anchor of event.context) {
      row.append(citedEvidence(anchor, scope, "Open supporting message"));
    }
    list.append(row);
  }
  results.append(list);
}

function showDecisionHistory(data, scope) {
  element("query-status").textContent = decisionStates[data.status] ?? "History unavailable.";
  showCoverage(data, "Uncertainty and coverage");
  showDecisionEvents(data.events.filter((event) => event.chronology === "known"), scope, "Dated events");
  showDecisionEvents(
    data.events.filter((event) => event.chronology !== "known"), scope, "Uncertain dates",
  );
  if (!data.conflicts.length) return;
  results.append(textNode("h3", "Unresolved conflicts"));
  for (const conflict of data.conflicts) {
    const row = textNode("article", "", "result");
    const accounts = document.createElement("ul");
    row.append(textNode("h4", conflict.summary, "content"), accounts);
    for (const account of conflict.accounts) {
      const item = document.createElement("li");
      item.append(textNode("p", account.text, "content"));
      for (const anchor of account.citations) {
        item.append(citedEvidence(anchor, scope, "Open account source"));
      }
      accounts.append(item);
    }
    results.append(row);
  }
}

project.addEventListener("input", clearResults);

element("lookup").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResults();
  const operation = event.submitter?.value || "search";
  const decisionHistory = operation === "decision-history";
  const payload = { project: project.value.trim(), query: query.value.trim() };
  if (decisionHistory) payload.mode = "decision_history";
  const status = element("query-status");
  const request = new AbortController();
  lookupRequest = request;
  const heading = element("results-heading");
  heading.textContent = decisionHistory ? "Decision history · " + payload.query : "Results";
  heading.hidden = false;
  status.textContent = operation === "search" ? "Searching…" : "Checking source evidence…";
  try {
    const route = decisionHistory ? "deep-recall" : operation;
    const data = await read(route, payload, request.signal);
    if (request.signal.aborted) return;
    if (operation === "search") showSearch(data, payload.project);
    else if (decisionHistory) showDecisionHistory(data, payload.project);
    else showAnswer(data, payload.project);
  } catch (error) {
    if (!request.signal.aborted) {
      status.textContent = error instanceof TypeError ? "This operation is unavailable." : error.message;
    }
  }
});

function normalized(value) {
  // Match Python str.split() for the whitespace accepted by the evidence verifier.
  return value.replace(/[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/gu, " ")
    .replace(/^ | $/g, "");
}

function comparableTime(timestamp) {
  return timestamp?.replace(/\+00:00$/, "Z") ?? null;
}

function evidenceField(message, anchor) {
  if (anchor.field === "text") return message?.text;
  const tool = message?.tool_activity[anchor.tool_index];
  if (anchor.field === "tool_request") return tool?.request;
  if (anchor.field === "tool_result") return tool?.result;
  return null;
}

function recordedText(value, label) {
  if (value.length <= 2000 && value.split("\n").length <= 20) return textNode("pre", value, "content");
  const view = textNode("div", "", "long-text");
  const preview = textNode("pre", value.split("\n").slice(0, 20).join("\n").slice(0, 2000), "content preview");
  const disclosure = document.createElement("details");
  disclosure.className = "full-output";
  disclosure.append(textNode("summary", "Show complete recorded " + label), textNode("pre", value, "content"));
  disclosure.addEventListener("toggle", () => { preview.hidden = disclosure.open; });
  view.append(preview, disclosure);
  return view;
}

function recordedField(value, field) {
  if (value === null || value === undefined) {
    return textNode("p", "No " + field + " recorded on this occurrence.", "metadata");
  }
  if (value === "") return textNode("p", "Empty " + field + ".", "metadata");
  const view = textNode("div", "", "recorded-field");
  let decoded;
  try { decoded = JSON.parse(value); } catch { /* Literal fallback. */ }
  if (decoded && typeof decoded === "object" && !Array.isArray(decoded)) {
    const id = decoded.id ?? decoded.tool_use_id ?? decoded.call_id;
    if (typeof id === "string") view.append(textNode("p", "Call: " + id, "metadata"));
    if (decoded.is_error === true) view.append(textNode("p", "Recorded error", "metadata"));
    const input = decoded.input;
    if (input && typeof input === "object" &&
        typeof input.old_string === "string" && typeof input.new_string === "string") {
      view.append(textNode("p", "Recorded edit: before / after", "metadata"),
        recordedText(input.old_string, "before text"), recordedText(input.new_string, "after text"));
    }
    const content = decoded.content ?? decoded.output ?? decoded.arguments ?? decoded.input;
    if (content !== undefined) {
      const text = typeof content === "string" ? content : JSON.stringify(content, null, 2);
      if (text.includes("*** Begin Patch") || /^--- .+\n\+\+\+ /m.test(text)) {
        view.append(textNode("p", "Recorded patch", "metadata"));
      }
      view.append(recordedText(text, "output"));
      const raw = document.createElement("details");
      raw.append(textNode("summary", "Original recorded field"), recordedText(value, field));
      view.append(raw);
      return view;
    }
  }
  if (value.includes("*** Begin Patch") || /^--- .+\n\+\+\+ /m.test(value)) {
    view.append(textNode("p", "Recorded patch", "metadata"));
  }
  view.append(recordedText(value, field));
  return view;
}

function sessionLink(documentId, scope, index, toolIndex, field = "text") {
  const params = new URLSearchParams({view: "session", project: scope, document: documentId,
    message: String(index)});
  if (toolIndex !== undefined) params.set("tool", String(toolIndex));
  params.set("field", field);
  const link = textNode("a", toolIndex === undefined ? "Link to message" :
    "Link to " + (field === "tool_request" ? "request" : "result"), "metadata");
  link.href = "#" + params.toString();
  link.addEventListener("click", (event) => {
    if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey &&
        location.hash === link.hash) {
      event.preventDefault();
      resolveSessionTarget();
    }
  });
  link.title = "Link to this position in the current archived snapshot; unlock required.";
  return link;
}

function showMessage(message, index, anchor, documentId, scope) {
  const row = textNode("article", "", anchor ? "message cited" : "message");
  row.append(textNode(
    "p",
    [message.role, "Message " + (index + 1), message.sent_at].filter(Boolean).join(" · "),
    "metadata",
  ));
  row.dataset.message = index;
  row.tabIndex = -1;
  row.append(sessionLink(documentId, scope, index));
  if (anchor) {
    const fields = { text: "Message text", tool_request: "Tool request", tool_result: "Tool result" };
    row.append(textNode("p", fields[anchor.field], "metadata"), textNode("mark", anchor.quote));
  }
  if (message.text) row.append(recordedText(message.text, "message"));
  for (const part of message.non_text_parts ?? []) {
    row.append(textNode("p", "Archived non-text content: " + part.kind, "metadata"));
  }
  for (const [toolIndex, activity] of message.tool_activity.entries()) {
    const tool = document.createElement("details");
    tool.open = true;
    tool.append(textNode("summary", activity.name || "Tool activity"));
    for (const [field, label] of [["request", "Request"], ["result", "Result"]]) {
      const container = textNode("section", "", "tool-field");
      container.dataset.tool = toolIndex;
      container.dataset.field = "tool_" + field;
      container.tabIndex = -1;
      container.append(textNode("p", label, "metadata"),
        sessionLink(documentId, scope, index, toolIndex, "tool_" + field),
        recordedField(activity[field], field));
      tool.append(container);
    }
    row.append(tool);
  }
  return row;
}

async function openConversation(documentId, offset, scope, anchor, target) {
  clearEvidence();
  evidence.hidden = false;
  element("evidence-heading").focus();
  const status = element("evidence-status");
  status.textContent = "Opening conversation…";
  const request = new AbortController();
  conversationRequest = request;
  try {
    const record = await read("conversation", {
      document_id: documentId, offset, page_size: 50,
    }, request.signal);
    if (request.signal.aborted) return;
    if (record.document_id !== documentId || record.offset !== offset ||
        record.provenance.project !== scope) {
      status.textContent = anchor ? "Cited evidence is unavailable." : "Conversation is unavailable.";
      return;
    }
    if (anchor) {
      const message = record.messages[0];
      const value = evidenceField(message, anchor);
      const quote = normalized(anchor.quote);
      if (comparableTime(message?.sent_at) !== comparableTime(anchor.timestamp) ||
          typeof value !== "string" || !quote || !normalized(value).includes(quote)) {
        status.textContent = "Cited evidence is unavailable.";
        return;
      }
    }
    element("conversation-provenance").textContent = provenance(record);
    record.messages.forEach((message, index) => {
      messages.append(showMessage(message, record.offset + index, index === 0 ? anchor : null, documentId, scope));
    });
    const selected = target ?? anchor;
    if (selected) {
      const message = record.messages[0];
      let node = messages.firstElementChild;
      if (selected.field !== "text") {
        if (!message?.tool_activity?.[selected.tool_index]) node = null;
        else node = node?.querySelector(`[data-tool="${selected.tool_index}"][data-field="${selected.field}"]`);
      }
      if (!node) {
        messages.replaceChildren();
        status.textContent = "Session target is unavailable.";
        return;
      }
      node.classList.add("cited");
      node.querySelectorAll("details.full-output").forEach((details) => { details.open = true; });
      node.focus();
      node.scrollIntoView({block: "nearest"});
    }
    status.textContent = record.messages.length ? "" : "No messages on this page.";
    first.hidden = offset === 0;
    first.onclick = () => openConversation(documentId, 0, scope);
    next.hidden = record.next_offset === null;
    next.onclick = () => openConversation(documentId, record.next_offset, scope);
  } catch (error) {
    if (!request.signal.aborted) {
      status.textContent = anchor ? "Cited evidence is unavailable." : "Conversation is unavailable.";
    }
  }
}

function resolveSessionTarget() {
  if (!location.hash) { clearEvidence(); return; }
  try {
    if (location.hash.length > 4096) throw new Error();
    const params = new URLSearchParams(location.hash.slice(1));
    const allowed = ["view", "project", "document", "message", "tool", "field"];
    for (const key of params.keys()) {
      if (!allowed.includes(key) || params.getAll(key).length !== 1) throw new Error();
    }
    const integer = (key) => {
      const value = params.get(key);
      if (!/^\d+$/.test(value ?? "") || !Number.isSafeInteger(Number(value))) throw new Error();
      return Number(value);
    };
    const scope = params.get("project");
    const doc = params.get("document");
    if (params.get("view") !== "session" || !scope || !doc) throw new Error();
    const offset = integer("message");
    const field = params.get("field") ?? "text";
    if (!["text", "tool_request", "tool_result"].includes(field) ||
        (field === "text") === params.has("tool")) throw new Error();
    const target = {field};
    if (params.has("tool")) target.tool_index = integer("tool");
    if (!token) return;
    clearResults();
    if (project.value !== scope) {
      project.value = scope;
      scheduleStatusRefresh();
    }
    openConversation(doc, offset, scope, null, target);
  } catch {
    clearEvidence();
    evidence.hidden = false;
    element("evidence-status").textContent = "Session target is unavailable.";
  }
}

window.addEventListener("hashchange", resolveSessionTarget);
