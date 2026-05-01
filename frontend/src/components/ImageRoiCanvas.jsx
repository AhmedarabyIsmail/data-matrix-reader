import { useEffect, useRef, useState } from "react";

const CANVAS_WIDTH = 640;
const CANVAS_HEIGHT = 480;

export default function ImageRoiCanvas({ imageUrl, detectionBox, onRoiChange }) {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState(null);
  const [currentRoi, setCurrentRoi] = useState(null);

  useEffect(() => {
    if (!imageUrl) return;
    const img = new Image();
    img.onload = () => {
      imageRef.current = img;
      drawCanvas(currentRoi);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  useEffect(() => {
    drawCanvas(currentRoi);
  }, [detectionBox]);

  const toRoi = (x0, y0, x1, y1) => {
    const x = Math.max(0, Math.min(x0, x1));
    const y = Math.max(0, Math.min(y0, y1));
    const width = Math.min(CANVAS_WIDTH - x, Math.abs(x1 - x0));
    const height = Math.min(CANVAS_HEIGHT - y, Math.abs(y1 - y0));
    return { x, y, width, height };
  };

  const drawCanvas = (roi) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
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
    drawCanvas(roi);
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
