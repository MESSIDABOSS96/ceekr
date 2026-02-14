"use client";

import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  isSparkle: boolean;
}

interface Comet {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  startTime: number;
  duration: number;
}

const GRID_SPACING = 45;
const JITTER = 8;

// Comet constants — fewer but bolder
const COMET_HEAD_ALPHA = 0.4;
const COMET_HEAD_RADIUS = 2.5;
const COMET_TAIL_LENGTH = 10;
const COMET_TAIL_PX = 70;
const COMET_SPEED_MIN = 180; // px/s
const COMET_SPEED_MAX = 320; // px/s
const SPAWN_INTERVAL_MIN = 3000;
const SPAWN_INTERVAL_MAX = 6000;
const MAX_COMETS = 3;

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

export function DotGridBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let stars: Star[] = [];
    let comets: Comet[] = [];
    let lastSpawnTime = 0;
    let nextSpawnDelay =
      SPAWN_INTERVAL_MIN +
      Math.random() * (SPAWN_INTERVAL_MAX - SPAWN_INTERVAL_MIN);
    let starBuffer: HTMLCanvasElement | null = null;
    let reducedMotion = false;
    let mouseX: number | null = null;
    let mouseY: number | null = null;

    // Check prefers-reduced-motion
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reducedMotion = motionQuery.matches;
    const onMotionChange = (e: MediaQueryListEvent) => {
      reducedMotion = e.matches;
      if (reducedMotion) comets = [];
    };
    motionQuery.addEventListener("change", onMotionChange);

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
      const cols = Math.floor(w / GRID_SPACING) + 1;
      const rows = Math.floor(h / GRID_SPACING) + 1;
      const offsetX = (w - (cols - 1) * GRID_SPACING) / 2;
      const offsetY = (h - (rows - 1) * GRID_SPACING) / 2;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const jx = (Math.random() - 0.5) * 2 * JITTER;
          const jy = (Math.random() - 0.5) * 2 * JITTER;
          stars.push({
            x: offsetX + c * GRID_SPACING + jx,
            y: offsetY + r * GRID_SPACING + jy,
            radius: weightedRandom(0.5, 2.2, 2),
            alpha: weightedRandom(0.08, 0.25, 1.8),
            isSparkle: Math.random() < 0.15,
          });
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

      // Draw planets
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

      bufCtx.globalAlpha = 1;
      comets = [];
    }

    function spawnComet(now: number) {
      const w = canvas!.width / devicePixelRatio;
      const h = canvas!.height / devicePixelRatio;
      const margin = 60;

      // Pick a random edge to enter from
      const edge = Math.floor(Math.random() * 4);
      let fromX: number, fromY: number, toX: number, toY: number;

      // Drift adds angle variation so comets don't travel perfectly straight
      const drift = (Math.random() - 0.5) * 0.6;

      switch (edge) {
        case 0: // top → bottom
          fromX = Math.random() * w;
          fromY = -margin;
          toX = fromX + w * drift;
          toY = h + margin;
          break;
        case 1: // right → left
          fromX = w + margin;
          fromY = Math.random() * h;
          toX = -margin;
          toY = fromY + h * drift;
          break;
        case 2: // bottom → top
          fromX = Math.random() * w;
          fromY = h + margin;
          toX = fromX + w * drift;
          toY = -margin;
          break;
        default: // left → right
          fromX = -margin;
          fromY = Math.random() * h;
          toX = w + margin;
          toY = fromY + h * drift;
          break;
      }

      const dist = Math.sqrt((toX - fromX) ** 2 + (toY - fromY) ** 2);
      const speed =
        COMET_SPEED_MIN + Math.random() * (COMET_SPEED_MAX - COMET_SPEED_MIN);
      const duration = (dist / speed) * 1000;

      comets.push({ fromX, fromY, toX, toY, startTime: now, duration });
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

      // Mouse magnify — lens distortion effect
      // Stars near cursor get pushed outward and scaled up
      if (mouseX !== null && mouseY !== null) {
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

      if (reducedMotion) {
        animationId = requestAnimationFrame(draw);
        return;
      }

      // Spawn new comets
      if (now - lastSpawnTime > nextSpawnDelay) {
        if (comets.length < MAX_COMETS) {
          spawnComet(now);
        }
        lastSpawnTime = now;
        nextSpawnDelay =
          SPAWN_INTERVAL_MIN +
          Math.random() * (SPAWN_INTERVAL_MAX - SPAWN_INTERVAL_MIN);
      }

      // Remove expired comets
      comets = comets.filter((c) => now - c.startTime < c.duration + 100);

      // Draw comets
      for (const comet of comets) {
        const elapsed = now - comet.startTime;
        if (elapsed < 0) continue;
        const progress = Math.min(elapsed / comet.duration, 1);

        const dx = comet.toX - comet.fromX;
        const dy = comet.toY - comet.fromY;
        const totalDist = Math.sqrt(dx * dx + dy * dy);

        const headX = comet.fromX + dx * progress;
        const headY = comet.fromY + dy * progress;

        // Pixel-based tail spacing
        const tailStep = (COMET_TAIL_PX / COMET_TAIL_LENGTH) / totalDist;

        // Tail segments
        for (let i = COMET_TAIL_LENGTH; i >= 1; i--) {
          const tailProgress = progress - i * tailStep;
          if (tailProgress < 0) continue;
          const tx = comet.fromX + dx * tailProgress;
          const ty = comet.fromY + dy * tailProgress;
          const tailFade = 1 - i / (COMET_TAIL_LENGTH + 1);
          const tailRadius = COMET_HEAD_RADIUS * (0.2 + 0.8 * tailFade);
          const tailAlpha = COMET_HEAD_ALPHA * tailFade * 0.6;

          ctx!.fillStyle = `rgba(255, 255, 255, ${tailAlpha})`;
          ctx!.beginPath();
          ctx!.arc(tx, ty, tailRadius, 0, Math.PI * 2);
          ctx!.fill();
        }

        // Head — bright glow
        const headGlow = ctx!.createRadialGradient(
          headX, headY, 0,
          headX, headY, COMET_HEAD_RADIUS * 3,
        );
        headGlow.addColorStop(0, `rgba(255, 255, 255, ${COMET_HEAD_ALPHA})`);
        headGlow.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx!.fillStyle = headGlow;
        ctx!.beginPath();
        ctx!.arc(headX, headY, COMET_HEAD_RADIUS * 3, 0, Math.PI * 2);
        ctx!.fill();

        // Head core
        ctx!.fillStyle = `rgba(255, 255, 255, ${COMET_HEAD_ALPHA * 1.2})`;
        ctx!.beginPath();
        ctx!.arc(headX, headY, COMET_HEAD_RADIUS, 0, Math.PI * 2);
        ctx!.fill();
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
      motionQuery.removeEventListener("change", onMotionChange);
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
