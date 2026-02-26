"use client";

import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  isSparkle: boolean;
}

const GRID_SPACING = 45;
const JITTER = 8;

// Mouse magnify — lens distortion
const MAGNIFY_RADIUS = 70;
const MAGNIFY_SCALE = 1.6;
const MAGNIFY_ALPHA = 0.32;
const MAGNIFY_PUSH = 0.15;

// Planet colors [r, g, b]
const PLANET_COLORS: [number, number, number][] = [
  [160, 190, 255], // cool blue
  [255, 210, 170], // warm amber
  [190, 170, 255], // lavender
  [170, 240, 210], // mint
  [255, 190, 190], // soft rose
];

interface DotGridBackgroundProps {
  subtle?: boolean;
  magnify?: boolean;
}

export function DotGridBackground({ subtle = false, magnify = true }: DotGridBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let stars: Star[] = [];
    let starBuffer: HTMLCanvasElement | null = null;
    let mouseX: number | null = null;
    let mouseY: number | null = null;

    // Mouse tracking
    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    const onMouseLeave = () => {
      mouseX = null;
      mouseY = null;
    };
    window.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseleave", onMouseLeave);

    function weightedRandom(min: number, max: number, skew: number): number {
      const u = Math.random();
      return min + (max - min) * Math.pow(u, skew);
    }

    function buildGrid() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas!.width = w * devicePixelRatio;
      canvas!.height = h * devicePixelRatio;
      canvas!.style.width = `${w}px`;
      canvas!.style.height = `${h}px`;
      ctx!.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

      stars = [];

      const spacing = subtle ? 30 : GRID_SPACING;
      const cols = Math.floor(w / spacing) + 1;
      const rows = Math.floor(h / spacing) + 1;
      const offsetX = (w - (cols - 1) * spacing) / 2;
      const offsetY = (h - (rows - 1) * spacing) / 2;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (subtle) {
            stars.push({
              x: offsetX + c * spacing,
              y: offsetY + r * spacing,
              radius: 0.6,
              alpha: 0.07,
              isSparkle: false,
            });
          } else {
            const jx = (Math.random() - 0.5) * 2 * JITTER;
            const jy = (Math.random() - 0.5) * 2 * JITTER;
            stars.push({
              x: offsetX + c * spacing + jx,
              y: offsetY + r * spacing + jy,
              radius: weightedRandom(0.5, 2.2, 2),
              alpha: weightedRandom(0.08, 0.25, 1.8),
              isSparkle: Math.random() < 0.15,
            });
          }
        }
      }

      // Pre-render to offscreen buffer
      starBuffer = document.createElement("canvas");
      starBuffer.width = canvas!.width;
      starBuffer.height = canvas!.height;
      const bufCtx = starBuffer.getContext("2d")!;
      bufCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

      // Draw stars
      for (const star of stars) {
        bufCtx.globalAlpha = star.alpha;
        if (star.isSparkle) {
          bufCtx.strokeStyle = "white";
          bufCtx.lineWidth = 0.5;
          bufCtx.beginPath();
          bufCtx.moveTo(star.x, star.y - 1.5);
          bufCtx.lineTo(star.x, star.y + 1.5);
          bufCtx.stroke();
          bufCtx.beginPath();
          bufCtx.moveTo(star.x - 1.5, star.y);
          bufCtx.lineTo(star.x + 1.5, star.y);
          bufCtx.stroke();
        } else {
          bufCtx.fillStyle = "white";
          bufCtx.beginPath();
          bufCtx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
          bufCtx.fill();
        }
      }

      // Draw planets (skip in subtle mode)
      if (!subtle) {
        const planetCount = 3 + Math.floor(Math.random() * 3);
        for (let i = 0; i < planetCount; i++) {
          const px = 60 + Math.random() * (w - 120);
          const py = 60 + Math.random() * (h - 120);
          const pr = 3 + Math.random() * 5;
          const [cr, cg, cb] =
            PLANET_COLORS[Math.floor(Math.random() * PLANET_COLORS.length)];

          // Soft glow
          const gradient = bufCtx.createRadialGradient(
            px, py, 0,
            px, py, pr * 3,
          );
          gradient.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, 0.07)`);
          gradient.addColorStop(1, `rgba(${cr}, ${cg}, ${cb}, 0)`);
          bufCtx.globalAlpha = 1;
          bufCtx.fillStyle = gradient;
          bufCtx.beginPath();
          bufCtx.arc(px, py, pr * 3, 0, Math.PI * 2);
          bufCtx.fill();

          // Planet body
          bufCtx.globalAlpha = 0.12;
          bufCtx.fillStyle = `rgb(${cr}, ${cg}, ${cb})`;
          bufCtx.beginPath();
          bufCtx.arc(px, py, pr, 0, Math.PI * 2);
          bufCtx.fill();

          // Ring (~30% chance)
          if (Math.random() < 0.3) {
            bufCtx.globalAlpha = 0.08;
            bufCtx.strokeStyle = `rgb(${cr}, ${cg}, ${cb})`;
            bufCtx.lineWidth = 0.8;
            bufCtx.beginPath();
            bufCtx.ellipse(px, py, pr * 1.8, pr * 0.35, -0.2, 0, Math.PI * 2);
            bufCtx.stroke();
          }
        }
      }

      bufCtx.globalAlpha = 1;
    }

    function draw(now: number) {
      const w = canvas!.width / devicePixelRatio;
      const h = canvas!.height / devicePixelRatio;

      ctx!.clearRect(0, 0, w, h);

      // Draw star buffer
      if (starBuffer) {
        ctx!.setTransform(1, 0, 0, 1, 0, 0);
        ctx!.drawImage(starBuffer, 0, 0);
        ctx!.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      }

      // Mouse magnify — lens distortion effect (skip in subtle mode)
      // Stars near cursor get pushed outward and scaled up
      if (magnify && !subtle && mouseX !== null && mouseY !== null) {
        for (const star of stars) {
          const dx = star.x - mouseX;
          const dy = star.y - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < MAGNIFY_RADIUS && dist > 1) {
            const t = 1 - Math.pow(dist / MAGNIFY_RADIUS, 2);

            // Push position outward from cursor
            const pushFactor = 1 + t * MAGNIFY_PUSH;
            const drawX = mouseX + dx * pushFactor;
            const drawY = mouseY + dy * pushFactor;

            const scaledRadius = star.radius * (1 + (MAGNIFY_SCALE - 1) * t);
            const scaledAlpha = star.alpha + (MAGNIFY_ALPHA - star.alpha) * t;

            ctx!.globalAlpha = scaledAlpha;
            if (star.isSparkle) {
              const arm = 1.5 * (1 + (MAGNIFY_SCALE - 1) * t);
              ctx!.strokeStyle = "white";
              ctx!.lineWidth = 0.5 + t * 0.5;
              ctx!.beginPath();
              ctx!.moveTo(drawX, drawY - arm);
              ctx!.lineTo(drawX, drawY + arm);
              ctx!.stroke();
              ctx!.beginPath();
              ctx!.moveTo(drawX - arm, drawY);
              ctx!.lineTo(drawX + arm, drawY);
              ctx!.stroke();
            } else {
              ctx!.fillStyle = "white";
              ctx!.beginPath();
              ctx!.arc(drawX, drawY, scaledRadius, 0, Math.PI * 2);
              ctx!.fill();
            }
          }
        }
        ctx!.globalAlpha = 1;
      }

      animationId = requestAnimationFrame(draw);
    }

    buildGrid();
    animationId = requestAnimationFrame(draw);

    const onResize = () => buildGrid();
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden="true"
    />
  );
}
