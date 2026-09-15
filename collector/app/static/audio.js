// Phần ghi âm dùng chung cho trang người thu và trang thu giọng bot.

// Tắt cả ba bộ xử lý tự động của Chrome: chúng sửa đúng tín hiệu mà dự án đo.
export const MIC_CONSTRAINTS = {
  audio: {
    channelCount: 1,
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
  },
};

export async function openAudio(sampleRate) {
  const stream = await navigator.mediaDevices.getUserMedia(MIC_CONSTRAINTS);
  const ctx = new AudioContext({ sampleRate });
  await ctx.audioWorklet.addModule("/static/recorder-worklet.js");
  const settings = stream.getAudioTracks()[0].getSettings();
  return { stream, ctx, settings };
}

// Ghi hai kênh: kênh 0 là micro, kênh 1 là chính tín hiệu bot đã gửi ra tai nghe.
// Trả về `bot`, một nút để nối nguồn phát câu bot vào (vừa ra tai nghe, vừa vào kênh 1).
export function startRecording(ctx, stream) {
  const mic = ctx.createMediaStreamSource(stream);
  const merger = ctx.createChannelMerger(2);
  const bot = ctx.createGain();
  mic.connect(merger, 0, 0);
  bot.connect(merger, 0, 1);
  bot.connect(ctx.destination);

  const node = new AudioWorkletNode(ctx, "recorder", {
    numberOfInputs: 1,
    numberOfOutputs: 1,
    outputChannelCount: [1],
    channelCount: 2,
    channelCountMode: "explicit",
    channelInterpretation: "discrete",
  });
  merger.connect(node);
  // Nút không ghi gì ra output (im lặng), nhưng phải nối tới đích để trình duyệt chắc chắn xử lý nó.
  node.connect(ctx.destination);

  const recording = { chunks: [[], []], frames: 0, startFrame: null, bot };
  recording.started = new Promise((resolve) => {
    node.port.onmessage = (event) => {
      if (event.data.type === "start") {
        recording.startFrame = event.data.frame;
        resolve();
      } else {
        event.data.channels.forEach((ch, c) => recording.chunks[c].push(ch));
        recording.frames += event.data.channels[0].length;
      }
    };
  });
  recording.stop = () => {
    node.port.postMessage("stop");
    merger.disconnect();
    mic.disconnect();
  };
  // Vị trí mẫu trong file ứng với một thời điểm trên đồng hồ AudioContext.
  recording.sampleAt = (contextTime) => Math.round(contextTime * ctx.sampleRate) - recording.startFrame;
  return recording;
}

export function encodeWav(channels, sampleRate) {
  const frames = channels[0].length;
  const count = channels.length;
  const buffer = new ArrayBuffer(44 + frames * count * 2);
  const view = new DataView(buffer);
  const text = (offset, s) => [...s].forEach((ch, i) => view.setUint8(offset + i, ch.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + frames * count * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, count, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * count * 2, true);
  view.setUint16(32, count * 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, frames * count * 2, true);
  let offset = 44;
  for (let i = 0; i < frames; i++) {
    for (let c = 0; c < count; c++) {
      const s = Math.max(-1, Math.min(1, channels[c][i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export function flatten(chunks) {
  const total = chunks.reduce((n, ch) => n + ch.length, 0);
  const out = new Float32Array(total);
  let offset = 0;
  for (const ch of chunks) {
    out.set(ch, offset);
    offset += ch.length;
  }
  return out;
}
