import { useCallback, useEffect, useRef, useState } from "react";

const CANVAS_WIDTH = 640;
const CANVAS_HEIGHT = 480;

function truncateText(ctx, text, maxWidth) {
  if (!text) return "";
  if (ctx.measureText(text).width <= maxWidth) return text;
  const ell = "…";
  let low = 0;
  let high = text.length;
  while (low < high) {
    const mid = Math.ceil((low + high) / 2);
    const slice = text.slice(0, mid) + ell;
    if (ctx.measureText(slice).width <= maxWidth) low = mid;
    else high = mid - 1;
  }
  return text.slice(0, Math.max(0, low)) + ell;
}

export default function ImageRoiCanvas({ imageUrl, detectionBox, inspectionOverlay, onRoiChange }) {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState(null);
  const [currentRoi, setCurrentRoi] = useState(null);
  const [imageEpoch, setImageEpoch] = useState(0);

  const draw = useCallback(
    (roiOverride) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const roi = roiOverride !== undefined ? roiOverride : currentRoi;

      ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      if (imageRef.current) {
        ctx.drawImage(imageRef.current, 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
      }

      if (roi && roi.width > 2 && roi.height > 2) {
        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 2;
        ctx.strokeRect(roi.x, roi.y, roi.width, roi.height);
      }

      if (detectionBox && detectionBox.width > 0 && detectionBox.height > 0) {
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2;
        ctx.strokeRect(detectionBox.x, detectionBox.y, detectionBox.width, detectionBox.height);
      }

      if (inspectionOverlay && inspectionOverlay.status) {
        const good = inspectionOverlay.status === "GOOD";
        const padX = 12;
        const padY = 10;
        const maxInnerW = CANVAS_WIDTH - 24 - padX * 2;
        const statusText = inspectionOverlay.status;
        const timeText =
          inspectionOverlay.processingTimeMs != null
            ? `${inspectionOverlay.processingTimeMs} ms`
            : null;

        ctx.font = "13px Segoe UI, system-ui, sans-serif";
        let dataText = inspectionOverlay.decodedData || "";
        if (dataText) {
          dataText = truncateText(ctx, dataText, maxInnerW);
        }

        let maxLineW = 0;
        ctx.font = "bold 26px Segoe UI, system-ui, sans-serif";
        maxLineW = Math.max(maxLineW, ctx.measureText(statusText).width);
        if (timeText) {
          ctx.font = "13px Segoe UI, system-ui, sans-serif";
          maxLineW = Math.max(maxLineW, ctx.measureText(timeText).width);
        }
        if (dataText) {
          ctx.font = "13px Segoe UI, system-ui, sans-serif";
          maxLineW = Math.max(maxLineW, ctx.measureText(dataText).width);
        }

        const innerW = Math.min(maxInnerW, Math.max(maxLineW, 72));
        const blockW = innerW + padX * 2;
        const lineGap = 4;
        let lineY = 12 + padY;
        let blockH = padY * 2 + 28;
        if (timeText) blockH += 16 + lineGap;
        if (dataText) blockH += 16 + lineGap;

        const bx = 12;
        const by = 12;
        ctx.fillStyle = "rgba(7, 11, 16, 0.82)";
        ctx.fillRect(bx, by, blockW, blockH);
        ctx.strokeStyle = good ? "rgba(61, 224, 139, 0.85)" : "rgba(255, 95, 95, 0.9)";
        ctx.lineWidth = 2;
        ctx.strokeRect(bx + 0.5, by + 0.5, blockW - 1, blockH - 1);

        ctx.textBaseline = "top";
        ctx.font = "bold 26px Segoe UI, system-ui, sans-serif";
        ctx.fillStyle = good ? "#3de08b" : "#ff5f5f";
        ctx.fillText(statusText, bx + padX, lineY);
        lineY += 28;

        if (timeText) {
          ctx.font = "13px Segoe UI, system-ui, sans-serif";
          ctx.fillStyle = "#91a4b8";
          ctx.fillText(timeText, bx + padX, lineY);
          lineY += 16 + lineGap;
        }

        if (dataText) {
          ctx.font = "13px Segoe UI, system-ui, sans-serif";
          ctx.fillStyle = "#e6edf4";
          ctx.fillText(dataText, bx + padX, lineY);
        }
      }
    },
    [currentRoi, detectionBox, inspectionOverlay]
  );

  useEffect(() => {
    if (!imageUrl) {
      imageRef.current = null;
      setImageEpoch((n) => n + 1);
      return;
    }
    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
      setImageEpoch((n) => n + 1);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  useEffect(() => {
    draw();
  }, [draw, imageEpoch]);

  const toRoi = (x0, y0, x1, y1) => {
    const x = Math.max(0, Math.min(x0, x1));
    const y = Math.max(0, Math.min(y0, y1));
    const width = Math.min(CANVAS_WIDTH - x, Math.abs(x1 - x0));
    const height = Math.min(CANVAS_HEIGHT - y, Math.abs(y1 - y0));
    return { x, y, width, height };
  };

  const getMousePos = (event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: Math.round(((event.clientX - rect.left) / rect.width) * CANVAS_WIDTH),
      y: Math.round(((event.clientY - rect.top) / rect.height) * CANVAS_HEIGHT)
    };
  };

  const onMouseDown = (event) => {
    if (!imageUrl) return;
    const point = getMousePos(event);
    setDrawing(true);
    setStartPoint(point);
  };

  const onMouseMove = (event) => {
    if (!drawing || !startPoint) return;
    const current = getMousePos(event);
    const roi = toRoi(startPoint.x, startPoint.y, current.x, current.y);
    setCurrentRoi(roi);
    draw(roi);
  };

  const onMouseUp = () => {
    setDrawing(false);
    if (currentRoi && onRoiChange) {
      onRoiChange(currentRoi);
    }
  };

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      className="roi-canvas"
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    />
  );
}
