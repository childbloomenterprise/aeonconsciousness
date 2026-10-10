import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { api } from "../worker/api.js";
import { environment, headers } from "./harness.mjs";

test("retry after saved submission loses response creates exactly one job; edits create another", async () => {
  const env = environment();
  await api.request("https://console.test/session", { headers: headers("owner") }, env);
  const form = {
    values: { title: "Lost reply fixture", brief: "Create a local Markdown checklist. No research needed.",
      kind: "general", max_tokens: "1000", deadline_minutes: "5",
      grant: '{"external_actions":[],"browser_write_domains":[],"recipients":[],"max_spend":0,"currency":"USD"}' },
    button: { disabled: false }, querySelector() { return this.button; },
  };
  const nodes = new Map([["#task-form", form], ["#dialog", { close() {} }],
    ["#form-error", { textContent: "" }]]);
  let loseResponse = true;
  const context = vm.createContext({
    document: { querySelector: (selector) => nodes.get(selector) }, crypto,
    AbortSignal, FormData: class { constructor(target) { this.values = target.values; }
      get(name) { return this.values[name]; } },
    fetch: async (url, options) => {
      const response = await api.request("https://console.test" + url.slice(4), {
        ...options, headers: headers("owner", options.headers),
      }, env);
      if (loseResponse) { loseResponse = false; throw new Error("Simulated lost reply after DB commit"); }
      return response;
    },
  });
  const source = readFileSync(new URL("../ui/app.js", import.meta.url), "utf8");
  vm.runInContext(source.slice(0, source.indexOf('$("#close").onclick')), context);
  vm.runInContext('state.org="org_primary"; modal=()=>{}; refresh=async()=>{}; notice=()=>{}; createTask();', context);
  const submit = () => form.onsubmit({ preventDefault() {}, target: form });
  await submit();
  assert.match(nodes.get("#form-error").textContent, /Cannot reach AEON/);
  await submit();
  let jobs = await api.request("https://console.test/orgs/org_primary/jobs", { headers: headers("owner") }, env);
  assert.equal((await jobs.json()).jobs.length, 1, "Lost response retry duplicated a saved assignment");
  form.values.brief += " Include three items.";
  await submit();
  jobs = await api.request("https://console.test/orgs/org_primary/jobs", { headers: headers("owner") }, env);
  assert.equal((await jobs.json()).jobs.length, 2, "Changed input needs its own submission key");
  env.DB.close?.();
});
