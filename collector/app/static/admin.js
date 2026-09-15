import { encodeWav, flatten, openAudio, startRecording } from "/static/audio.js";

const $ = (id) => document.getElementById(id);
const status = (text) => ($("status").textContent = text);
const SAMPLE_RATE_HZ = 16000;
let audio;

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}), "X-Admin-Token": $("token").value };
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response;
}

function cell(row, content) {
  const td = document.createElement("td");
  if (content instanceof Node) td.append(content);
  else td.textContent = content;
  row.append(td);
}

async function loadInvites() {
  const invites = await (await api("/api/admin/invites")).json();
  const body = $("invites");
  body.replaceChildren();
  for (const invite of invites) {
    const row = document.createElement("tr");
    cell(row, invite.speaker_id);
    cell(row, invite.consented ? "có" : "chưa");
    cell(row, String(invite.recordings));
    const link = document.createElement("input");
    link.readOnly = true;
    link.value = `${location.origin}/?t=${invite.token}`;
    link.addEventListener("focus", () => link.select());
    cell(row, link);
    body.append(row);
  }
}

async function loadLines() {
  const lines = await (await api("/api/admin/lines")).json();
  const body = $("lines");
  body.replaceChildren();
  for (const line of lines) {
    const row = document.createElement("tr");
    cell(row, `${line.script} / ${line.step}${line.recorded ? " ✓" : ""}`);
    cell(row, line.bot);
    const controls = document.createElement("div");
    const record = document.createElement("button");
    const listen = document.createElement("button");
    const save = document.createElement("button");
    record.textContent = "Thu";
    listen.textContent = "Nghe";
    save.textContent = "Lưu";
    listen.disabled = !line.recorded;
    save.disabled = true;
    let recording = null;
    let blob = null;

    record.addEventListener("click", async () => {
      if (!audio) audio = await openAudio(SAMPLE_RATE_HZ);
      await audio.ctx.resume();
      if (!recording) {
        recording = startRecording(audio.ctx, audio.stream);
        await recording.started;
        record.textContent = "Dừng";
      } else {
        recording.stop();
        blob = encodeWav([flatten(recording.chunks[0])], SAMPLE_RATE_HZ);
        recording = null;
        record.textContent = "Thu lại";
        listen.disabled = false;
        save.disabled = false;
      }
    });
    listen.addEventListener("click", async () => {
      const source = blob || (await (await api(`/api/admin/prompts/${line.script}/${line.step}.wav`)).blob());
      new Audio(URL.createObjectURL(source)).play();
    });
    save.addEventListener("click", async () => {
      const form = new FormData();
      form.append("script", line.script);
      form.append("step", String(line.step));
      form.append("audio", blob, "prompt.wav");
      try {
        await api("/api/admin/prompts", { method: "POST", body: form });
        status(`Đã lưu ${line.script} / ${line.step}`);
        save.disabled = true;
        row.firstChild.textContent = `${line.script} / ${line.step} ✓`;
      } catch (error) {
        status(`Lưu không thành công: ${error.message}`);
      }
    });
    controls.append(record, listen, save);
    cell(row, controls);
    body.append(row);
  }
}

$("load").addEventListener("click", async () => {
  try {
    await loadInvites();
    await loadLines();
    $("panel").hidden = false;
    status("");
  } catch (error) {
    status(`Không mở được: ${error.message}`);
  }
});

$("invite").addEventListener("click", async () => {
  await api("/api/admin/invites", { method: "POST" });
  await loadInvites();
});

$("export").addEventListener("click", async () => {
  status("Đang đóng gói dữ liệu...");
  const blob = await (await api("/api/admin/export")).blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "turnwise-collector.zip";
  link.click();
  status("");
});
