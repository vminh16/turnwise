// Chạy trong luồng âm thanh của trình duyệt. Chuyển nguyên từng khối mẫu về luồng chính.
// Khối đầu tiên báo `currentFrame`: đó là mốc 0 của file ghi âm trên đồng hồ AudioContext,
// và mọi mốc phát câu bot được quy về mốc này — nhờ vậy nhật ký phát khớp từng mẫu.
class Recorder extends AudioWorkletProcessor {
  constructor() {
    super();
    this.started = false;
    this.stopped = false;
    this.port.onmessage = (event) => {
      if (event.data === "stop") this.stopped = true;
    };
  }

  process(inputs) {
    if (this.stopped) return false;
    const input = inputs[0];
    const length = input.length > 0 ? input[0].length : 128;
    if (!this.started) {
      this.started = true;
      this.port.postMessage({ type: "start", frame: currentFrame });
    }
    const channels = [];
    for (let c = 0; c < 2; c++) {
      channels.push(input[c] ? input[c].slice() : new Float32Array(length));
    }
    this.port.postMessage({ type: "data", channels }, channels.map((ch) => ch.buffer));
    return true;
  }
}

registerProcessor("recorder", Recorder);
