import { encodeWav, flatten, openAudio, startRecording } from "/static/audio.js";
import { clock, createMeter } from "/static/meter.js";

const $ = (id) => document.getElementById(id);
let SAMPLE_RATE_HZ = null; // lấy từ server lúc mở trang, không đoán
const TOTAL_SCENARIOS_LABEL = (done, total) => `${done}/${total}`;
const el = (tag, props = {}, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
};

let audio = null;
let busy = false; // chỉ thu một câu mỗi lúc
let unsaved = 0; // số câu đã thu mà chưa lưu
let scenarioCount = 0;

function banner(text, kind = "error") {
  $("banner").hidden = !text;
  $("banner").className = `banner ${kind}`;
  $("banner").textContent = text || "";
}

function token() {
  return sessionStorage.getItem("collector-admin-token") || "";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}), "X-Admin-Token": token() };
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    sessionStorage.removeItem("collector-admin-token");
    showLogin("Token không đúng.");
    throw new Error("unauthorised");
  }
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response;
}

window.addEventListener("beforeunload", (event) => {
  if (unsaved > 0) event.preventDefault();
});

// --- đăng nhập -----------------------------------------------------------------------------

function showLogin(note) {
  $("login").hidden = false;
  $("panel").hidden = true;
  $("export").hidden = true;
  $("logout").hidden = true;
  banner(note || "");
}

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  sessionStorage.setItem("collector-admin-token", $("token").value.trim());
  await open();
});

$("logout").addEventListener("click", () => {
  sessionStorage.removeItem("collector-admin-token");
  showLogin();
});

async function open() {
  try {
    SAMPLE_RATE_HZ = (await (await api("/api/admin/config")).json()).sample_rate_hz;
    await loadLines(); // cần số tình huống trước khi vẽ bảng người thu
    await Promise.all([loadInvites(), loadRecordings()]);
  } catch (error) {
    if (error.message !== "unauthorised") banner(`Không tải được dữ liệu: ${error.message}`);
    return;
  }
  banner("");
  $("login").hidden = true;
  $("panel").hidden = false;
  $("export").hidden = false;
  $("logout").hidden = false;
}

// --- 1. Giọng tổng đài ---------------------------------------------------------------------

function botLine(text) {
  const node = el("div", { className: "bot-line" });
  text.split("/").forEach((part, index) => {
    if (index) node.append(el("span", { className: "slash", textContent: "/" }));
    node.append(part);
  });
  return node;
}

async function loadLines() {
  const lines = await (await api("/api/admin/lines")).json();
  const groups = new Map();
  for (const line of lines) {
    if (!groups.has(line.script)) groups.set(line.script, { title: line.title, lines: [] });
    groups.get(line.script).lines.push(line);
  }
  scenarioCount = groups.size;
  const saved = lines.filter((line) => line.recorded).length;
  $("prompt-progress").textContent = `Đã lưu ${saved}/${lines.length} câu`;

  const container = $("groups");
  const openBefore = new Set([...container.querySelectorAll("details[open]")].map((d) => d.dataset.script));
  container.replaceChildren();
  let firstIncomplete = true;
  for (const [script, group] of groups) {
    const done = group.lines.filter((line) => line.recorded).length;
    const complete = done === group.lines.length;
    const details = el("details");
    details.dataset.script = script;
    details.open = openBefore.size ? openBefore.has(script) : !complete && firstIncomplete;
    if (!complete) firstIncomplete = false;
    details.append(
      el(
        "summary",
        { className: "group" },
        el("span", { className: "name", textContent: group.title }),
        el("span", { className: `badge ${complete ? "ok" : done ? "warn" : "off"}`, textContent: complete ? "Đủ" : `${done}/${group.lines.length}` }),
      ),
    );
    const rows = el("div");
    for (const line of group.lines) rows.append(lineRow(line, details));
    details.append(rows);
    container.append(details);
  }
}

function lineRow(line, details) {
  const status = el("span", { className: `badge ${line.recorded ? "ok" : "off"}`, textContent: line.recorded ? "Đã lưu" : "Chưa thu" });
  const record = el("button", { textContent: line.recorded ? "Thu lại" : "Thu" });
  const listen = el("button", { textContent: "Nghe", disabled: !line.recorded });
  const text = el("div", { className: "text" }, el("span", { className: "small muted", textContent: `Câu ${line.step + 1}` }), botLine(line.bot));
  const row = el("div", { className: "row" }, text, el("div", { className: "actions", style: "margin: 0" }, status, record, listen));

  listen.addEventListener("click", async () => {
    const blob = await (await api(`/api/admin/prompts/${line.script}/${line.step}.wav`)).blob();
    new Audio(URL.createObjectURL(blob)).play();
  });

  const start = async () => {
    if (busy) return banner("Đang thu một câu khác. Dừng câu đó trước.", "info");
    try {
      if (!audio) audio = await openAudio(SAMPLE_RATE_HZ);
      await audio.ctx.resume();
    } catch {
      return banner("Không mở được micro. Hãy cho phép trình duyệt dùng micro rồi thử lại.");
    }
    banner("");
    busy = true;
    record.disabled = true;
    listen.disabled = true;
    const panel = recorderPanel(line, () => {
      busy = false;
      record.disabled = false;
      listen.disabled = !line.recorded;
    }, start);
    text.append(panel);
  };
  record.addEventListener("click", start);
  return row;
}

function recorderPanel(line, release, restart) {
  const dot = el("span", { className: "rec-dot" });
  const label = el("span", { className: "rec-label", textContent: "Đang ghi" });
  const canvas = el("canvas");
  const time = el("span", { className: "rec-time", textContent: "00:00" });
  const bar = el("div", { className: "recorder recording" }, dot, label, canvas, time);
  const stop = el("button", { className: "primary", textContent: "Dừng" });
  const actions = el("div", { className: "actions" }, stop);
  const panel = el("div", { className: "panel" }, bar, actions);

  const { ctx, stream } = audio;
  const recording = startRecording(ctx, stream);
  let meter;
  let timer;
  let blob = null;
  let counted = false;
  recording.started.then(() => {
    const startedAt = ctx.currentTime;
    meter = createMeter(ctx, ctx.createMediaStreamSource(stream), canvas);
    timer = setInterval(() => (time.textContent = clock(ctx.currentTime - startedAt)), 250);
  });

  const close = () => {
    if (counted) unsaved -= 1;
    panel.remove();
    release();
  };

  stop.addEventListener("click", () => {
    recording.stop();
    meter?.stop();
    clearInterval(timer);
    bar.classList.remove("recording");
    label.textContent = "Đã dừng";
    blob = encodeWav([flatten(recording.chunks[0])], SAMPLE_RATE_HZ);
    unsaved += 1;
    counted = true;

    const player = el("audio", { controls: true, src: URL.createObjectURL(blob) });
    const save = el("button", { className: "primary", textContent: "Lưu" });
    const redo = el("button", { textContent: "Thu lại" });
    const discard = el("button", { className: "link", textContent: "Bỏ" });
    const hint = el("span", { className: "badge warn", textContent: "Chưa lưu" });
    actions.replaceChildren(save, redo, discard, hint);
    bar.after(player);

    save.addEventListener("click", async () => {
      save.disabled = true;
      save.textContent = "Đang lưu…";
      const form = new FormData();
      form.append("script", line.script);
      form.append("step", String(line.step));
      form.append("audio", blob, "prompt.wav");
      try {
        await api("/api/admin/prompts", { method: "POST", body: form });
      } catch (error) {
        banner(`Chưa lưu được: ${error.message}`);
        save.disabled = false;
        save.textContent = "Lưu";
        return;
      }
      close();
      await loadLines();
      banner(`Đã lưu câu ${line.step + 1} của “${line.title}”.`, "info");
    });
    redo.addEventListener("click", () => {
      close();
      restart();
    });
    discard.addEventListener("click", close);
  });
  return panel;
}

// --- 2. Người thu --------------------------------------------------------------------------

async function copy(text, button) {
  await navigator.clipboard.writeText(text);
  const label = button.textContent;
  button.textContent = "Đã chép";
  setTimeout(() => (button.textContent = label), 1500);
}

async function loadInvites() {
  const invites = await (await api("/api/admin/invites")).json();
  const body = $("invites");
  body.replaceChildren();
  for (const invite of invites) {
    const link = `${location.origin}/?t=${invite.token}`;
    const state = invite.withdrawn
      ? el("span", { className: "badge off", textContent: "Đã rút lại" })
      : invite.consented
        ? el("span", { className: "badge ok", textContent: "Đã đồng ý" })
        : el("span", { className: "badge", textContent: "Chưa mở" });
    const copyButton = el("button", { textContent: "Chép link", disabled: Boolean(invite.withdrawn) });
    copyButton.addEventListener("click", () => copy(link, copyButton));
    const withdraw = el("button", { className: "danger", textContent: "Rút lại & xoá", disabled: Boolean(invite.withdrawn) });
    withdraw.addEventListener("click", async () => {
      if (!confirm(`Xoá vĩnh viễn mọi bản ghi và phiếu đồng ý của ${invite.speaker_id}? Link sẽ hết hiệu lực.`)) return;
      const result = await (await api(`/api/admin/speakers/${invite.speaker_id}`, { method: "DELETE" })).json();
      banner(`${result.speaker_id}: đã xoá ${result.recordings_deleted} bản ghi.`, "info");
      await Promise.all([loadInvites(), loadRecordings()]);
    });
    body.append(
      el(
        "tr",
        {},
        el("td", { className: "mono", textContent: invite.speaker_id }),
        el("td", {}, state),
        el("td", { textContent: TOTAL_SCENARIOS_LABEL(invite.recordings, scenarioCount || "?") }),
        el("td", {}, copyButton),
        el("td", {}, withdraw),
      ),
    );
  }
  if (!invites.length) body.append(el("tr", {}, el("td", { colSpan: 5, className: "muted", textContent: "Chưa có người thu nào." })));
}

$("invite").addEventListener("click", async () => {
  const invite = await (await api("/api/admin/invites", { method: "POST" })).json();
  const link = `${location.origin}/?t=${invite.token}`;
  const copyButton = el("button", { className: "primary", textContent: "Chép link" });
  copyButton.addEventListener("click", () => copy(link, copyButton));
  $("new-invite").hidden = false;
  $("new-invite").replaceChildren(
    el("p", { className: "small", textContent: `Link cho ${invite.speaker_id}. Gửi riêng cho đúng một người.` }),
    el("div", { className: "actions", style: "margin: 0" }, el("input", { type: "text", readOnly: true, value: link, style: "flex: 1; min-width: 14rem" }), copyButton),
  );
  await loadInvites();
});

// --- 3. Bản ghi ----------------------------------------------------------------------------

async function loadRecordings() {
  const recordings = await (await api("/api/admin/recordings")).json();
  $("recording-count").textContent = `${recordings.length} bản ghi`;
  const body = $("recordings");
  body.replaceChildren();
  for (const recording of recordings) {
    const listen = el("button", { textContent: "Nghe" });
    listen.addEventListener("click", async () => {
      listen.disabled = true;
      const blob = await (await api(`/api/admin/recordings/${recording.id}.wav`)).blob();
      listen.replaceWith(el("audio", { controls: true, autoplay: true, src: URL.createObjectURL(blob), style: "min-width: 14rem; margin: 0" }));
    });
    const remove = el("button", { className: "danger", textContent: "Xoá" });
    remove.addEventListener("click", async () => {
      if (!confirm(`Xoá bản ghi “${recording.title}” của ${recording.speaker_id}? Tình huống sẽ hiện lại cho người này.`)) return;
      await api(`/api/admin/recordings/${recording.id}`, { method: "DELETE" });
      banner(`Đã xoá bản ghi “${recording.title}” của ${recording.speaker_id}.`, "info");
      await Promise.all([loadRecordings(), loadInvites()]);
    });
    const stamp = recording.created_at.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2}).*$/, "$3/$2 $4:$5");
    body.append(
      el(
        "tr",
        {},
        el("td", { className: "small", textContent: stamp }),
        el("td", { className: "mono", textContent: recording.speaker_id }),
        el("td", { textContent: recording.title }),
        el("td", { className: "small", textContent: clock(recording.seconds) }),
        el("td", {}, listen),
        el("td", {}, remove),
      ),
    );
  }
  if (!recordings.length) body.append(el("tr", {}, el("td", { colSpan: 6, className: "muted", textContent: "Chưa có bản ghi nào." })));
}

// --- tải dữ liệu ---------------------------------------------------------------------------

$("export").addEventListener("click", async () => {
  $("export").disabled = true;
  $("export").textContent = "Đang đóng gói…";
  try {
    const blob = await (await api("/api/admin/export")).blob();
    el("a", { href: URL.createObjectURL(blob), download: "turnwise-collector.zip" }).click();
  } finally {
    $("export").disabled = false;
    $("export").textContent = "Tải toàn bộ dữ liệu";
  }
});

if (token()) open();
