"use client";

import { useEffect, useRef } from "react";

// Continuous ambient background -- runs the whole time this page is mounted
// (a real setInterval-free requestAnimationFrame loop, cleaned up on
// unmount). "24x7" here means "for as long as the tab is open", same
// honest scope as every other "live" thing on this site (polled, not a
// server-side process) -- there's no version of this that runs with the
// tab closed, and pretending otherwise would be the wrong kind of claim.
//
// Shared by Mission Control and LivingSystemBackground -- one real
// implementation, not two. Extracted here so the marketing-site background
// and the internal dashboard use the identical, already-tested effect.
export function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const fontSize = 15;
    let width = 0, height = 0, columns = 0, drops: number[] = [];
    const glyphs = "アイウエオカキクケコサシスセソ0123456789SHAKTHI";

    function resize() {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
      columns = Math.max(1, Math.floor(width / fontSize));
      drops = new Array(columns).fill(0).map(() => Math.random() * -50);
    }
    resize();
    window.addEventListener("resize", resize);

    let raf = 0;
    function draw() {
      if (!ctx) return;
      ctx.fillStyle = "rgba(5,7,10,0.09)";
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "rgba(52,211,153,0.6)";
      ctx.font = `${fontSize}px monospace`;
      for (let i = 0; i < drops.length; i++) {
        const glyph = glyphs[Math.floor(Math.random() * glyphs.length)];
        ctx.fillText(glyph, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
      }
      raf = requestAnimationFrame(draw);
    }
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ opacity: 0.16, pointerEvents: "none" }}
    />
  );
}

// Ambient fireflies -- 100-200 soft glowing points drifting across the
// screen. Pre-renders a handful of glow "sprites" once (radial gradients
// baked onto small offscreen canvases at device pixel ratio) and just
// drawImage()s them every frame -- far cheaper than building a fresh
// gradient per bug per frame at this count, and the pre-bake is what keeps
// 150+ of them crisp instead of soft/blurry at any screen density. Each
// bug wanders with a small random turn per frame (not a straight line) and
// blinks on an independent sine cycle that floors at 0 -- real fireflies
// flash and go fully dark between pulses, they don't glow continuously.
export function FireflySwarm({ count = 160 }: { count?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const spriteSize = 48;
    // Warm yellow -> yellow-green -> green: the real bioluminescent range,
    // so 160 identical dots don't read as one repeated sprite.
    const hues = [52, 72, 92];
    const sprites = hues.map((hue) => {
      const s = document.createElement("canvas");
      s.width = spriteSize * dpr;
      s.height = spriteSize * dpr;
      const sctx = s.getContext("2d")!;
      sctx.scale(dpr, dpr);
      const c = spriteSize / 2;
      const grad = sctx.createRadialGradient(c, c, 0, c, c, c);
      grad.addColorStop(0, `hsla(${hue}, 100%, 82%, 1)`);
      grad.addColorStop(0.22, `hsla(${hue}, 100%, 72%, 0.95)`);
      grad.addColorStop(0.55, `hsla(${hue}, 100%, 62%, 0.35)`);
      grad.addColorStop(1, `hsla(${hue}, 100%, 55%, 0)`);
      sctx.fillStyle = grad;
      sctx.beginPath();
      sctx.arc(c, c, c, 0, Math.PI * 2);
      sctx.fill();
      return s;
    });

    type Bug = { x: number; y: number; angle: number; speed: number; size: number; sprite: number; blinkPhase: number; blinkSpeed: number };
    let width = 0, height = 0;
    let bugs: Bug[] = [];

    function spawn(): Bug {
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        angle: Math.random() * Math.PI * 2,
        speed: 0.12 + Math.random() * 0.32,
        size: 9 + Math.random() * 15,
        sprite: Math.floor(Math.random() * sprites.length),
        blinkPhase: Math.random() * Math.PI * 2,
        blinkSpeed: 0.006 + Math.random() * 0.016,
      };
    }

    function resize() {
      if (!canvas) return;
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      bugs = Array.from({ length: count }, spawn);
    }
    resize();
    window.addEventListener("resize", resize);

    let raf = 0;
    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      for (const b of bugs) {
        b.angle += (Math.random() - 0.5) * 0.22;
        b.x += Math.cos(b.angle) * b.speed;
        b.y += Math.sin(b.angle) * b.speed * 0.6;
        if (b.x < -24) b.x = width + 24;
        if (b.x > width + 24) b.x = -24;
        if (b.y < -24) b.y = height + 24;
        if (b.y > height + 24) b.y = -24;

        b.blinkPhase += b.blinkSpeed;
        const blink = Math.max(0, Math.sin(b.blinkPhase));
        ctx.globalAlpha = 0.12 + blink * 0.88;
        ctx.drawImage(sprites[b.sprite], b.x - b.size / 2, b.y - b.size / 2, b.size, b.size);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    }
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, [count]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full"
      style={{ pointerEvents: "none", zIndex: 5 }}
    />
  );
}
