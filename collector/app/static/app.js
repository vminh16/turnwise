import { encodeWav, flatten, openAudio, startRecording } from "/static/audio.js";

const token = new URLSearchParams(location.search).get("t") || "";
const $ = (id) => document.getElementById(id);
const status = (text) => ($("status").textContent = text);
const show = (id) => {
  for (const section of document.querySelectorAll("main > section")) section.hidden = section.id !== id;
};

let config;
let audio;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response;
}

async function loadConfig() {
  config = await (await api(`/api/config?t=${encodeURIComponent(token)}`)).json();
  $("controller").textContent = config.data_controller;
}

// --- đồng ý --------------------------------------------------------------------------------

$("consent-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    purpose_evaluation: form.has("purpose_evaluation"),
    purpose_excerpts: form.has("purpose_excerpts"),
    adult: form.has("adult"),
    wired_headphones: form.has("wired_headphones"),
    dialect: form.get("dialect"),
  };
  try {
    await api(`/api/consent?t=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    status("");
    await micCheck();
  } catch (error) {
    status("Chưa gửi được: cần tích mục đích 1, đủ 18 tuổi, tai nghe có dây và chọn vùng giọng.");
  }
});

// --- thử micro -----------------------------------------------------------------------------

async function micCheck() {
  show("miccheck");
  audio = await openAudio(config.sample_rate_hz);
  const off = ["echoCancellation", "noiseSuppression", "autoGainControl"].filter((k) => audio.settings[k]);
  if (off.length) {
    $("mic-warning").hidden = false;
    $("mic-warning").textContent = `Trình duyệt vẫn bật: ${off.join(", ")}. Hãy dùng Chrome bản mới trên máy tính.`;
  }
  const analyser = audio.ctx.createAnalyser();
  audio.ctx.createMediaStreamSource(audio.stream).connect(analyser);
  const buffer = new Float32Array(analyser.fftSize);
  const tick = () => {
    analyser.getFloatTimeDomainData(buffer);
    $("level").value = Math.min(1, Math.sqrt(buffer.reduce((s, x) => s + x * x, 0) / buffer.length) * 8);
    if (!$("miccheck").hidden) requestAnimationFrame(tick);
  };
  tick();
}

$("mic-ok").addEventListener("click", async () => {
  await audio.ctx.resume();
  listScripts();
});

// --- chọn tình huống -----------------------------------------------------------------------

function listScripts() {
  show("scripts");
  const list = $("script-list");
  list.replaceChildren();
  for (const script of config.scripts) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = `${script.title}${script.recorded ? " ✓ đã thu" : ""}`;
    button.disabled = !script.prompts_ready;
    if (!script.prompts_ready) button.title = "Chưa có giọng tổng đài cho tình huống này";
    button.addEventListener("click", () => runScript(script));
    item.append(button);
    list.append(item);
  }
}

// --- chạy một tình huống -------------------------------------------------------------------

async function runScript(script) {
  show("run");
  status("Đang tải giọng tổng đài...");
  const { ctx } = audio;
  const prompts = [];
  for (let step = 0; step < script.steps.length; step++) {
    const response = await api(`/api/prompts/${script.name}/${step}.wav?t=${encodeURIComponent(token)}`);
    prompts.push(await ctx.decodeAudioData(await response.arrayBuffer()));
  }
  status("");

  $("run-title").textContent = script.title;
  $("run-persona").textContent = script.persona;
  $("run-props").replaceChildren(
    ...Object.entries(script.props).map(([key, value]) => {
      const line = document.createElement("p");
      line.textContent = `${key}: ${value}`;
      return line;
    }),
  );
  $("run-instruction").textContent = "Bấm nút bên dưới để gọi tổng đài.";
  $("run-replies").textContent = "";

  const recording = startRecording(ctx, audio.stream);
  await recording.started;
  const playback = [];
  let step = 0;
  const button = $("run-next");
  button.textContent = "Gọi tổng đài";
  button.disabled = false;

  button.onclick = async () => {
    if (step >= script.steps.length) {
      button.disabled = true;
      await finish(script, recording, playback);
      return;
    }
    button.disabled = true;
    const current = step;
    const pressed = recording.sampleAt(ctx.currentTime);
    const when = ctx.currentTime + config.playback_lead_ms / 1000;
    const source = ctx.createBufferSource();
    source.buffer = prompts[current];
    source.connect(recording.bot);
    const start = recording.sampleAt(when);
    source.onended = () => {
      playback.push({ step: current, pressed_sample: pressed, start_sample: start, end_sample: start + prompts[current].length });
      button.textContent = current === script.steps.length - 1 ? "Kết thúc tình huống" : "Tôi nói xong — nghe câu tiếp";
      button.disabled = false;
    };
    source.start(when);
    $("run-instruction").textContent = script.steps[current].customer;
    const replies = script.steps[current].replies;
    $("run-replies").textContent = replies.length ? `Gợi ý, nếu cần: ${replies.join(" · ")}` : "";
    step += 1;
  };
}

async function finish(script, recording, playback) {
  status("Đang lưu...");
  await new Promise((resolve) => setTimeout(resolve, config.tail_ms));
  recording.stop();
  const channels = recording.chunks.map(flatten);
  const wav = encodeWav(channels, config.sample_rate_hz);
  const client = {
    user_agent: navigator.userAgent,
    base_latency_s: audio.ctx.baseLatency,
    output_latency_s: audio.ctx.outputLatency,
    track_settings: audio.settings,
    guide_version: config.guide_version,
  };
  const form = new FormData();
  form.append("t", token);
  form.append("script", script.name);
  form.append("playback", JSON.stringify(playback));
  form.append("client", JSON.stringify(client));
  form.append("audio", wav, `${script.name}.wav`);
  try {
    await api("/api/recordings", { method: "POST", body: form });
    status("Đã lưu tình huống. Cảm ơn bạn!");
    await loadConfig();
    listScripts();
  } catch (error) {
    status(`Lưu không thành công, hãy thu lại tình huống này. (${error.message})`);
    listScripts();
  }
}

// --- khởi động -----------------------------------------------------------------------------

(async () => {
  if (!token) return status("Link không hợp lệ. Hãy dùng đúng link đã được gửi cho bạn.");
  try {
    await loadConfig();
  } catch {
    return status("Link không hợp lệ. Hãy dùng đúng link đã được gửi cho bạn.");
  }
  if (!config.consented) show("consent");
  else await micCheck();
})();
