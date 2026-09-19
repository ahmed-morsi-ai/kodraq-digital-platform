import { useEffect, useRef } from "react";

interface NeuralParticlesProps {
  className?: string;
  particleCount?: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

export default function NeuralParticles({
  className = "",
  particleCount = 72,
}: NeuralParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");

    if (!context) {
      return;
    }

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const parent = canvas.parentElement;

    if (!parent) {
      return;
    }

    let animationFrame = 0;
    let width = 0;
    let height = 0;
    let dpr = 1;

    const pointer = {
      x: 0,
      y: 0,
      active: false,
    };

    const particles: Particle[] = [];

    const resize = () => {
      const rect = parent.getBoundingClientRect();

      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      context.setTransform(dpr, 0, 0, dpr, 0, 0);

      particles.length = 0;

      for (let index = 0; index < particleCount; index += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.28,
          vy: (Math.random() - 0.5) * 0.28,
          radius: Math.random() * 1.6 + 0.7,
        });
      }
    };

    const drawBackgroundGlow = () => {
      const centerX = width * 0.5;
      const centerY = height * 0.5;
      const radius = Math.max(width, height) * 0.42;

      const gradient = context.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        radius,
      );

      gradient.addColorStop(0, "rgba(16, 185, 129, 0.14)");
      gradient.addColorStop(0.42, "rgba(34, 211, 238, 0.06)");
      gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

      context.fillStyle = gradient;
      context.fillRect(0, 0, width, height);
    };

    const draw = () => {
      context.clearRect(0, 0, width, height);
      drawBackgroundGlow();

      for (const particle of particles) {
        if (!reduceMotion) {
          particle.x += particle.vx;
          particle.y += particle.vy;

          if (particle.x < -20 || particle.x > width + 20) {
            particle.vx *= -1;
          }

          if (particle.y < -20 || particle.y > height + 20) {
            particle.vy *= -1;
          }

          if (pointer.active) {
            const dx = pointer.x - particle.x;
            const dy = pointer.y - particle.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance > 0 && distance < 150) {
              const force = (150 - distance) / 150;
              particle.vx += (dx / distance) * force * 0.0015;
              particle.vy += (dy / distance) * force * 0.0015;
            }
          }
        }

        context.beginPath();
        context.arc(
          particle.x,
          particle.y,
          particle.radius,
          0,
          Math.PI * 2,
        );
        context.fillStyle = "rgba(110, 231, 183, 0.78)";
        context.fill();
      }

      for (let first = 0; first < particles.length; first += 1) {
        for (let second = first + 1; second < particles.length; second += 1) {
          const a = particles[first];
          const b = particles[second];

          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 135) {
            const opacity = ((135 - distance) / 135) * 0.18;

            context.beginPath();
            context.moveTo(a.x, a.y);
            context.lineTo(b.x, b.y);
            context.strokeStyle = `rgba(45, 212, 191, ${opacity})`;
            context.lineWidth = 0.7;
            context.stroke();
          }
        }
      }

      if (pointer.active) {
        const glow = context.createRadialGradient(
          pointer.x,
          pointer.y,
          0,
          pointer.x,
          pointer.y,
          120,
        );

        glow.addColorStop(0, "rgba(34, 211, 238, 0.11)");
        glow.addColorStop(1, "rgba(34, 211, 238, 0)");

        context.fillStyle = glow;
        context.beginPath();
        context.arc(pointer.x, pointer.y, 120, 0, Math.PI * 2);
        context.fill();
      }

      animationFrame = window.requestAnimationFrame(draw);
    };

    const handlePointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();

      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.active = true;
    };

    const handlePointerLeave = () => {
      pointer.active = false;
    };

    resize();
    draw();

    window.addEventListener("resize", resize);
    canvas.addEventListener("pointermove", handlePointerMove);
    canvas.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("pointermove", handlePointerMove);
      canvas.removeEventListener("pointerleave", handlePointerLeave);
    };
  }, [particleCount]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    />
  );
}
