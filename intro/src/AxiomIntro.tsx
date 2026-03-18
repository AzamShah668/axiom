import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Img,
  Sequence,
  AbsoluteFill,
  staticFile,
  Easing,
} from "remotion";

/*
 * AXIOM UNIVERSAL INTRO — Reusable across every video.
 * No topic or subject text. Pure brand animation.
 *
 * The voice-over (generated separately via TTS) plays on top of this visual.
 * The voice says the topic; the video just shows the AXIOM brand.
 *
 * TIMELINE (7 seconds @ 30fps = 210 frames):
 * ───────────────────────────────────────────────────
 *  0–20   (0–0.7s)   Dark fade-in from black
 * 20–75   (0.7–2.5s) AXIOM logo scales up with spring bounce + golden glow pulse
 * 75–120  (2.5–4s)   Tagline fades in: "Learn. Understand. Excel."
 * 120–150 (4–5s)     Subtle shimmer pass across logo
 * 150–180 (5–6s)     Hold + gentle particles
 * 180–210 (6–7s)     Everything fades to black (transition to main video)
 * ───────────────────────────────────────────────────
 */

// Floating particle for ambient premium feel
const Particle = ({ delay, x, y, size }: { delay: number; x: number; y: number; size: number }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame - delay, [0, 40, 160, 195], [0, 0.5, 0.5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(frame - delay, [0, 210], [0, -80], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const drift = interpolate(frame - delay, [0, 210], [0, Math.sin(delay) * 30], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(200, 180, 130, 0.9), transparent)",
        opacity,
        transform: `translateY(${translateY}px) translateX(${drift}px)`,
        filter: "blur(0.5px)",
      }}
    />
  );
};

export const AxiomIntro = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // === BACKGROUND FADE IN ===
  const bgOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  // === LOGO ENTRANCE (spring bounce) ===
  const logoScale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 10, stiffness: 80, mass: 1.2 },
  });

  const logoOpacity = interpolate(frame, [15, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtle breathing glow
  const glowIntensity = interpolate(
    Math.sin((frame - 40) * 0.04),
    [-1, 1],
    [12, 40]
  );

  // === SHIMMER PASS (a light sweep across the logo at ~4s) ===
  const shimmerX = interpolate(frame, [120, 155], [-200, 600], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });
  const shimmerOpacity = interpolate(frame, [120, 130, 145, 155], [0, 0.6, 0.6, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // === TAGLINE ===
  const taglineOpacity = interpolate(frame, [75, 95], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineY = interpolate(frame, [75, 100], [25, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // === DECORATIVE LINES ===
  const lineWidth = spring({
    frame: frame - 65,
    fps,
    config: { damping: 200 },
  });

  // === MASTER FADE OUT ===
  const fadeOut = interpolate(frame, [durationInFrames - 30, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Particles (deterministic positions)
  const particles = Array.from({ length: 25 }, (_, i) => ({
    delay: (i * 8) % 50,
    x: ((i * 37 + 13) % 96) + 2,
    y: ((i * 53 + 27) % 75) + 12,
    size: ((i * 11) % 4) + 2,
  }));

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>

      {/* Deep dark gradient background */}
      <AbsoluteFill
        style={{
          opacity: bgOpacity,
          background:
            "radial-gradient(ellipse at 50% 40%, #1a1a2e 0%, #0f0f1f 45%, #060612 100%)",
        }}
      />

      {/* Floating ambient particles */}
      {particles.map((p, i) => (
        <Particle key={i} {...p} />
      ))}

      {/* Radial ambient light behind logo */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 700,
          height: 700,
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(200, 175, 120, ${interpolate(
            logoOpacity, [0, 1], [0, 0.1]
          )}) 0%, transparent 65%)`,
          opacity: logoOpacity,
        }}
      />

      {/* AXIOM Logo — centered with spring + glow */}
      <Sequence from={15} premountFor={10}>
        <div
          style={{
            position: "absolute",
            top: "38%",
            left: "50%",
            transform: `translate(-50%, -50%) scale(${logoScale})`,
            opacity: logoOpacity,
            filter: `drop-shadow(0 0 ${glowIntensity}px rgba(200, 175, 120, 0.5))`,
          }}
        >
          <Img
            src={staticFile("axiom_logo.png")}
            style={{
              width: 450,
              height: "auto",
            }}
          />
          {/* Shimmer sweep overlay */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: shimmerX,
              width: 80,
              height: "100%",
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
              opacity: shimmerOpacity,
              transform: "skewX(-15deg)",
              pointerEvents: "none",
            }}
          />
        </div>
      </Sequence>

      {/* Golden decorative lines (left and right) */}
      <Sequence from={65} premountFor={10}>
        <div
          style={{
            position: "absolute",
            top: "57%",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            alignItems: "center",
            gap: 20,
          }}
        >
          <div
            style={{
              width: `${lineWidth * 140}px`,
              height: 1.5,
              background:
                "linear-gradient(90deg, transparent, rgba(200, 175, 120, 0.7))",
            }}
          />
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "rgba(200, 175, 120, 0.8)",
              boxShadow: "0 0 8px rgba(200, 175, 120, 0.4)",
            }}
          />
          <div
            style={{
              width: `${lineWidth * 140}px`,
              height: 1.5,
              background:
                "linear-gradient(270deg, transparent, rgba(200, 175, 120, 0.7))",
            }}
          />
        </div>
      </Sequence>

      {/* Tagline: "Learn. Understand. Excel." */}
      <Sequence from={75} premountFor={10}>
        <div
          style={{
            position: "absolute",
            top: "63%",
            width: "100%",
            textAlign: "center",
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
          }}
        >
          <span
            style={{
              fontFamily: "'Segoe UI', 'Inter', sans-serif",
              fontSize: 22,
              fontWeight: 300,
              color: "rgba(200, 190, 170, 0.65)",
              letterSpacing: "8px",
              textTransform: "uppercase",
            }}
          >
            Learn · Understand · Excel
          </span>
        </div>
      </Sequence>

    </AbsoluteFill>
  );
};
