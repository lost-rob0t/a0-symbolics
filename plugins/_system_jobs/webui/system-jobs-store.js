import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
import {
  toastFrontendError,
  toastFrontendInfo,
  toastFrontendSuccess,
} from "/components/notifications/notification-store.js";

const API = "/plugins/_system_jobs/jobs";
const TITLE = "System Jobs";

function emptyEditor() {
  return {
    id: "",
    name: "",
    schedule: "0 * * * *",
    workdir: "/a0/usr/workdir",
    enabled: true,
    script: "",
  };
}

export const store = createStore("systemJobsStore", {
  jobs: [],
  status: {},
  loading: false,
  editorOpen: false,
  editor: emptyEditor(),
  logJob: null,
  logText: "",

  async onOpen() {
    await this.refresh();
  },

  cleanup() {
    this.logJob = null;
    this.logText = "";
  },

  async refresh() {
    this.loading = true;
    try {
      const data = await callJsonApi(API, { action: "list" });
      this.jobs = Array.isArray(data?.jobs) ? data.jobs : [];
      this.status = data?.status || {};
    } catch (error) {
      toastFrontendError(`Could not load jobs: ${error}`, TITLE);
    } finally {
      this.loading = false;
    }
  },

  newJob() {
    this.editor = emptyEditor();
    this.editorOpen = true;
  },

  editJob(job) {
    this.editor = {
      id: job.id || "",
      name: job.name || "",
      schedule: job.schedule || "0 * * * *",
      workdir: job.workdir || "/a0/usr/workdir",
      enabled: job.enabled !== false,
      script: job.script || "",
    };
    this.editorOpen = true;
  },

  cancelEdit() {
    this.editorOpen = false;
    this.editor = emptyEditor();
  },

  async saveJob() {
    if (!this.editor.name.trim() || !this.editor.schedule.trim() || !this.editor.script.trim()) {
      toastFrontendError("Name, schedule, and script are required.", TITLE);
      return;
    }
    try {
      await callJsonApi(API, { action: "save", ...this.editor });
      toastFrontendSuccess(this.editor.id ? "Job updated." : "Job created.", TITLE);
      this.cancelEdit();
      await this.refresh();
    } catch (error) {
      toastFrontendError(`Could not save job: ${error}`, TITLE);
    }
  },

  async deleteJob(job) {
    try {
      await callJsonApi(API, { action: "delete", id: job.id });
      toastFrontendSuccess("Job deleted.", TITLE);
      if (this.logJob?.id === job.id) {
        this.logJob = null;
        this.logText = "";
      }
      await this.refresh();
    } catch (error) {
      toastFrontendError(`Could not delete job: ${error}`, TITLE);
    }
  },

  async runJob(job) {
    try {
      const data = await callJsonApi(API, { action: "run", id: job.id });
      toastFrontendSuccess(`Started PID ${data?.run?.pid || "?"}.`, TITLE);
      this.logJob = job;
      await this.loadLog(job);
    } catch (error) {
      toastFrontendError(`Could not run job: ${error}`, TITLE);
    }
  },

  async loadLog(job) {
    try {
      const data = await callJsonApi(API, { action: "log", id: job.id });
      this.logJob = job;
      this.logText = data?.log || "";
      if (!this.logText) toastFrontendInfo("This job has no log output yet.", TITLE);
    } catch (error) {
      toastFrontendError(`Could not load log: ${error}`, TITLE);
    }
  },

  closeLog() {
    this.logJob = null;
    this.logText = "";
  },

  async syncCron() {
    try {
      await callJsonApi(API, { action: "sync" });
      toastFrontendSuccess("Crontab synchronized.", TITLE);
      await this.refresh();
    } catch (error) {
      toastFrontendError(`Could not synchronize crontab: ${error}`, TITLE);
    }
  },
});
