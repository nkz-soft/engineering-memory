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

let token = "";
let lookupRequest;
let conversationRequest;

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

function showMessage(message, index, anchor) {
  const row = textNode("article", "", anchor ? "message cited" : "message");
  row.append(textNode(
    "p",
    [message.role, "Message " + (index + 1), message.sent_at].filter(Boolean).join(" · "),
    "metadata",
  ));
  if (anchor) {
    const fields = { text: "Message text", tool_request: "Tool request", tool_result: "Tool result" };
    row.append(textNode("p", fields[anchor.field], "metadata"), textNode("mark", anchor.quote));
  }
  if (message.text) row.append(textNode("p", message.text, "content"));
  for (const activity of message.tool_activity) {
    const tool = document.createElement("details");
    tool.append(textNode("summary", activity.name || "Tool activity"));
    for (const [field, label] of [["request", "Request"], ["result", "Result"]]) {
      if (activity[field]) {
        tool.append(textNode("p", label, "metadata"), textNode("p", activity[field], "content"));
      }
    }
    row.append(tool);
  }
  return row;
}

async function openConversation(documentId, offset, scope, anchor) {
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
      messages.append(showMessage(message, record.offset + index, index === 0 ? anchor : null));
    });
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
