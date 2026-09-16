// Thanh sóng âm nhảy theo giọng: cho người đang nói thấy ngay là micro đang thu.
// Chỉ đọc tín hiệu để vẽ, không sửa gì trong bản ghi.

const BARS = 48;
const FRAME_MS = 33;
export const VOICE_LEVEL = 0.45; // khoảng -37 dBFS trên thang -60..-10

export function createMeter(ctx, source, canvas, onLevel) {
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  const history = new Array(BARS).fill(0);
  const paint = canvas.getContext("2d");
  const style = getComputedStyle(canvas);
  const on = style.getPropertyValue("--meter-on").trim() || "#2f5d8a";
  const off = style.getPropertyValue("--meter-off").trim() || "#cfd4d9";
  let running = true;
  let last = 0;
  let frame = 0;

  const draw = (time) => {
    if (!running) return;
    frame = requestAnimationFrame(draw);
    if (time - last < FRAME_MS) return;
    last = time;

    analyser.getFloatTimeDomainData(samples);
    let sum = 0;
    for (const x of samples) sum += x * x;
    const db = 20 * Math.log10(Math.max(Math.sqrt(sum / samples.length), 1e-6));
    const level = Math.min(1, Math.max(0, (db + 60) / 50));
    history.shift();
    history.push(level);
    if (onLevel) onLevel(level);

    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    if (!width || !height) return;
    if (canvas.width !== Math.round(width * ratio)) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    paint.setTransform(ratio, 0, 0, ratio, 0, 0);
    paint.clearRect(0, 0, width, height);
    // Khung hẹp (điện thoại) vẽ ít vạch hơn, để mỗi vạch vẫn đủ dày mà nhìn.
    const count = Math.max(12, Math.min(BARS, Math.floor(width / 9)));
    const shown = history.slice(-count);
    const gap = 3;
    const bar = (width - gap * (count - 1)) / count;
    shown.forEach((value, index) => {
      const barHeight = Math.max(3, value * height);
      paint.fillStyle = value >= VOICE_LEVEL ? on : off;
      paint.beginPath();
      paint.roundRect(index * (bar + gap), (height - barHeight) / 2, bar, barHeight, bar / 2);
      paint.fill();
    });
  };
  frame = requestAnimationFrame(draw);

  return {
    stop() {
      running = false;
      cancelAnimationFrame(frame);
      try {
        source.disconnect(analyser);
      } catch {
        // nguồn đã bị ngắt từ trước
      }
    },
  };
}

export function clock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
