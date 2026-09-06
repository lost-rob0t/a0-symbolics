import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
import {
  toastFrontendSuccess,
  toastFrontendError,
} from "/components/notifications/notification-store.js";

export const store = createStore("prologRlmPolicyStore", {
  busy: false,
  loaded: false,
  reasoning_mode: "auto",
  context_budget_percent: 30,
  core_loop_enabled: true,

  async init() {
    if (this.loaded) return;
    try {
      const res = await callJsonApi("/plugins/_prolog_rlm/runtime_policy", {
        action: "get",
      });
      if (res?.ok) {
        this.reasoning_mode = res.reasoning_mode || "auto";
        this.context_budget_percent =
          res.context_budget_percent != null ? res.context_budget_percent : 30;
        this.core_loop_enabled = res.core_loop_enabled !== false;
        this.loaded = true;
      }
    } catch (e) {
      // Control stays hidden defaults; settings remain authoritative.
    }
  },

  async apply(patch) {
    this.busy = true;
    try {
      const res = await callJsonApi("/plugins/_prolog_rlm/runtime_policy", {
        action: "set",
        ...patch,
      });
      if (!res?.ok) throw new Error(res?.message || "Failed to save policy");
      this.reasoning_mode = res.reasoning_mode;
      this.context_budget_percent = res.context_budget_percent;
      this.core_loop_enabled = res.core_loop_enabled;
      toastFrontendSuccess("Prolog-RLM policy updated", "Prolog-RLM");
    } catch (e) {
      toastFrontendError(e.message, "Prolog-RLM");
    } finally {
      this.busy = false;
    }
  },

  setMode(mode) {
    this.apply({ reasoning_mode: this.reasoning_mode });
  },

  setBudget() {
    this.apply({ context_budget_percent: this.context_budget_percent });
  },
});
