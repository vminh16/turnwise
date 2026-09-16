import { encodeWav, flatten, mixForListening, openAudio, startRecording } from "/static/audio.js";
import { VOICE_LEVEL, clock, createMeter } from "/static/meter.js";

const token = new URLSearchParams(location.search).get("t") || "";
const $ = (id) => document.getElementById(id);
const SCREENS = ["consent", "mic", "list", "run", "review", "message"];
const STEP_OF = { consent: "consent", mic: "mic", list: "record", run: "record", review: "record" };
const PROP_LABELS = {
  subscriber_id: "Số thuê bao",
  customer_code: "Mã khách hàng",
  contract_no: "Số hợp đồng",
  appointment_code: "Mã lịch hẹn",
  sms: "Tin nhắn",
  old_address: "Địa chỉ cũ",
  new_address: "Địa chỉ mới",
  plan: "Gói cước",
};

let config;
let audio; // { stream, ctx, settings }
let unsaved = false; // đang thu hoặc có bản thu chưa gửi

// --- tiện ích ------------------------------------------------------------------------------

function show(screen) {
  for (const id of SCREENS) $(id).hidden = id !== screen;
  const order = ["consent", "mic", "record"];
  const current = order.indexOf(STEP_OF[screen]);
  for (const li of $("steps").children) {
    const index = order.indexOf(li.dataset.step);
    li.className = index === current ? "current" : index < current ? "done" : "";
  }
  $("steps").hidden = !(screen in STEP_OF);
  window.scrollTo({ top: 0 });
}

function banner(text, kind = "error") {
  $("banner").hidden = !text;
  $("banner").className = `banner ${kind}`;
  $("banner").textContent = text || "";
}

function message(title, text) {
  $("message-title").textContent = title;
  $("message-text").textContent = text;
  show("message");
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const error = new Error(await response.text());
    error.status = response.status;
    throw error;
  }
  return response;
}

async function loadConfig() {
  config = await (await api(`/api/config?t=${encodeURIComponent(token)}`)).json();
  $("speaker").textContent = `Mã người thu: ${config.speaker_id}`;
  $("controller").textContent = config.data_controller;
}

window.addEventListener("beforeunload", (event) => {
  if (unsaved) event.preventDefault();
});
window.addEventListener("unhandledrejection", (event) => {
  banner(`Có lỗi xảy ra: ${event.reason?.message || event.reason}. Tải lại trang để thử lại.`);
});

// --- 1. Đồng ý -----------------------------------------------------------------------------

const consentForm = $("consent-form");
consentForm.addEventListener("change", () => {
  const form = new FormData(consentForm);
  $("consent-submit").disabled = !(
    form.has("purpose_evaluation") && form.has("adult") && form.has("wired_headphones") && form.get("dialect")
  );
});

consentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(consentForm);
  $("consent-submit").disabled = true;
  try {
    await api(`/api/consent?t=${encodeURIComponent(token)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        purpose_evaluation: form.has("purpose_evaluation"),
        purpose_excerpts: form.has("purpose_excerpts"),
        adult: form.has("adult"),
        wired_headphones: form.has("wired_headphones"),
        dialect: form.get("dialect"),
      }),
    });
    banner("");
    show("mic");
  } catch (error) {
    banner(`Chưa lưu được phiếu đồng ý (${error.message}).`);
    $("consent-submit").disabled = false;
  }
});

// --- 2. Kiểm tra micro ---------------------------------------------------------------------

let micMeter;
$("mic-start").addEventListener("click", async () => {
  $("mic-start").disabled = true;
  try {
    audio = await openAudio(config.sample_rate_hz);
    await audio.ctx.resume();
  } catch (error) {
    $("mic-start").disabled = false;
    banner("Không mở được micro. Hãy cho phép trình duyệt dùng micro (biểu tượng ổ khoá cạnh địa chỉ trang) rồi thử lại.");
    return;
  }
  banner("");
  const processing = ["echoCancellation", "noiseSuppression", "autoGainControl"].filter((key) => audio.settings[key]);
  if (processing.length) banner(`Trình duyệt vẫn đang bật ${processing.join(", ")}. Hãy dùng Chrome bản mới trên máy tính.`, "info");

  $("mic-start").hidden = true;
  $("mic-ok").hidden = false;
  $("mic-recorder").classList.add("recording");
  $("mic-hint").textContent = "Hãy nói thử một câu…";
  let heard = 0;
  micMeter = createMeter(audio.ctx, audio.ctx.createMediaStreamSource(audio.stream), $("mic-meter"), (level) => {
    if (level >= VOICE_LEVEL) heard += 1;
    if (heard >= 10 && $("mic-ok").disabled) {
      $("mic-ok").disabled = false;
      $("mic-hint").textContent = "Micro nghe thấy bạn rõ ràng.";
    }
  });
});

$("mic-ok").addEventListener("click", async () => {
  micMeter?.stop();
  $("mic-recorder").classList.remove("recording");
  await showList();
});

// --- 3a. Danh sách -------------------------------------------------------------------------

async function showList(note) {
  await loadConfig();
  const ready = config.scripts.filter((script) => script.prompts_ready);
  if (config.done === config.total) {
    message("Bạn đã hoàn thành tất cả tình huống", "Cảm ơn bạn đã tham gia. Bạn có thể đóng trang này.");
    return;
  }
  $("remaining").textContent = `Còn ${config.total - config.done} tình huống`;
  $("progress-text").textContent = `Đã gửi ${config.done}/${config.total}`;
  $("progress-bar").style.width = `${(100 * config.done) / config.total}%`;

  const list = $("scenario-list");
  list.replaceChildren();
  if (!ready.length) {
    list.append(Object.assign(document.createElement("p"), { className: "muted", textContent: "Chưa có tình huống nào sẵn sàng. Hãy quay lại sau." }));
  }
  for (const script of ready) {
    const row = document.createElement("div");
    row.className = "scenario";
    const text = document.createElement("div");
    text.append(
      Object.assign(document.createElement("h3"), { textContent: script.title }),
      Object.assign(document.createElement("span"), { className: "small muted", textContent: `${script.steps.length} lượt tổng đài` }),
    );
    const button = document.createElement("button");
    button.textContent = "Bắt đầu";
    button.className = "primary";
    button.addEventListener("click", () => runScript(script));
    row.append(text, button);
    list.append(row);
  }
  banner(note || "", "info");
  show("list");
}

// --- 3b. Thu một tình huống ----------------------------------------------------------------

async function runScript(script) {
  const next = $("run-next");
  next.disabled = true;
  next.onclick = null;
  next.textContent = "Đang tải…";
  banner("");
  $("run-title").textContent = script.title;
  $("run-persona").textContent = script.persona;
  $("run-props").replaceChildren(
    ...Object.entries(script.props).flatMap(([key, value]) => [
      Object.assign(document.createElement("dt"), { textContent: PROP_LABELS[key] || key }),
      Object.assign(document.createElement("dd"), { textContent: value }),
    ]),
  );
  $("run-step").textContent = `${script.steps.length} lượt tổng đài`;
  $("run-status").textContent = "Sẵn sàng";
  $("run-status").className = "pill";
  $("run-instruction").textContent = "Đọc thẻ bên trên. Khi sẵn sàng, bấm Bắt đầu.";
  $("run-replies").replaceChildren();
  $("run-label").textContent = "Chưa ghi";
  $("run-time").textContent = "00:00";
  show("run");

  const { ctx } = audio;
  const prompts = [];
  try {
    for (let step = 0; step < script.steps.length; step++) {
      const response = await api(`/api/prompts/${script.name}/${step}.wav?t=${encodeURIComponent(token)}`);
      prompts.push(await ctx.decodeAudioData(await response.arrayBuffer()));
    }
  } catch (error) {
    banner("Không tải được giọng tổng đài. Kiểm tra mạng rồi thử lại.");
    await showList();
    return;
  }

  let recording = null;
  let meter = null;
  let timer = 0;
  let step = 0;
  const playback = [];

  const stopUi = () => {
    meter?.stop();
    clearInterval(timer);
    $("run-recorder").classList.remove("recording");
  };

  const play = () => {
    const current = step;
    const pressed = recording.sampleAt(ctx.currentTime);
    const when = ctx.currentTime + config.playback_lead_ms / 1000;
    const start = recording.sampleAt(when);
    const source = ctx.createBufferSource();
    source.buffer = prompts[current];
    source.connect(recording.bot);
    source.onended = () => {
      playback.push({ step: current, pressed_sample: pressed, start_sample: start, end_sample: start + prompts[current].length });
      const last = current === script.steps.length - 1;
      $("run-status").textContent = last ? "Đến lượt bạn — nói xong thì bấm Kết thúc" : "Đến lượt bạn — nói xong thì bấm nút";
      $("run-status").className = "pill turn";
      next.textContent = last ? "Kết thúc" : "Tôi nói xong";
      next.disabled = false;
    };
    source.start(when);
    step += 1;
    next.disabled = true;
    next.textContent = "Tổng đài đang nói…";
    $("run-step").textContent = `Lượt ${current + 1}/${script.steps.length}`;
    $("run-status").replaceChildren(document.createTextNode("Tổng đài đang nói"), Object.assign(document.createElement("span"), { className: "dots" }));
    $("run-status").className = "pill";
    $("run-instruction").textContent = script.steps[current].customer;
    $("run-replies").replaceChildren(
      ...script.steps[current].replies.map((reply) => Object.assign(document.createElement("span"), { textContent: reply })),
    );
  };

  const finish = async () => {
    next.disabled = true;
    next.textContent = "Đang hoàn tất…";
    $("run-status").textContent = "Đang hoàn tất";
    await new Promise((resolve) => setTimeout(resolve, config.tail_ms));
    recording.stop();
    stopUi();
    const channels = recording.chunks.map(flatten);
    review(script, channels, playback);
  };

  $("run-cancel").onclick = () => {
    if (recording) {
      recording.stop();
      stopUi();
    }
    unsaved = false;
    showList();
  };

  next.textContent = "Bắt đầu";
  next.disabled = false;
  next.onclick = async () => {
    if (!recording) {
      next.disabled = true;
      recording = startRecording(ctx, audio.stream);
      await recording.started;
      unsaved = true;
      const startedAt = ctx.currentTime;
      $("run-recorder").classList.add("recording");
      $("run-label").textContent = "Đang ghi";
      meter = createMeter(ctx, ctx.createMediaStreamSource(audio.stream), $("run-meter"));
      timer = setInterval(() => ($("run-time").textContent = clock(ctx.currentTime - startedAt)), 250);
      play();
    } else if (step < script.steps.length) {
      play();
    } else {
      await finish();
    }
  };
}

// --- 3c. Nghe lại và gửi -------------------------------------------------------------------

function review(script, channels, playback) {
  const wav = encodeWav(channels, config.sample_rate_hz);
  const listen = encodeWav([mixForListening(channels)], config.sample_rate_hz);
  const player = $("review-audio");
  if (player.src) URL.revokeObjectURL(player.src);
  player.src = URL.createObjectURL(listen);
  $("review-title").textContent = `${script.title} · ${clock(channels[0].length / config.sample_rate_hz)}`;
  $("review-send").disabled = false;
  $("review-send").textContent = "Gửi bản thu";
  show("review");

  $("review-redo").onclick = () => {
    player.pause();
    unsaved = false;
    runScript(script);
  };
  $("review-send").onclick = async () => {
    player.pause();
    $("review-send").disabled = true;
    $("review-send").textContent = "Đang gửi…";
    const form = new FormData();
    form.append("t", token);
    form.append("script", script.name);
    form.append("playback", JSON.stringify(playback));
    form.append("client", JSON.stringify({
      user_agent: navigator.userAgent,
      base_latency_s: audio.ctx.baseLatency,
      output_latency_s: audio.ctx.outputLatency,
      track_settings: audio.settings,
      guide_version: config.guide_version,
    }));
    form.append("audio", wav, `${script.name}.wav`);
    try {
      await api("/api/recordings", { method: "POST", body: form });
    } catch (error) {
      if (error.status !== 409) {
        // Giữ nguyên bản thu để gửi lại, không bắt thu lại vì lỗi mạng.
        banner(`Chưa gửi được (${error.message}). Bản thu vẫn còn, bấm Gửi để thử lại.`);
        $("review-send").disabled = false;
        $("review-send").textContent = "Gửi lại";
        return;
      }
    }
    unsaved = false;
    await showList(`Đã gửi “${script.title}”.`);
  };
}

// --- khởi động -----------------------------------------------------------------------------

(async () => {
  if (!token) return message("Link không hợp lệ", "Hãy mở đúng link đã được gửi cho bạn.");
  try {
    await loadConfig();
  } catch {
    return message("Link không hợp lệ", "Link này không tồn tại hoặc đã hết hiệu lực.");
  }
  show(config.consented ? "mic" : "consent");
})();
