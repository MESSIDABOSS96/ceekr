interface QualityBannerProps {
  quality: "strong" | "moderate" | "weak";
  count: number;
}

const CONFIG = {
  strong: {
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.2)",
    color: "rgb(16,185,129)",
    text: (n: number) => `Found ${n} highly relevant accounts`,
  },
  moderate: {
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.2)",
    color: "rgb(245,158,11)",
    text: (n: number) =>
      `Found ${n} accounts — consider refining for better results`,
  },
  weak: {
    bg: "rgba(239,68,68,0.08)",
    border: "rgba(239,68,68,0.2)",
    color: "rgb(239,68,68)",
    text: (n: number) =>
      `Found ${n} accounts — relevance is low, try refining`,
  },
};

export function QualityBanner({ quality, count }: QualityBannerProps) {
  const c = CONFIG[quality];
  return (
    <div
      className="mb-4 rounded-xl px-4 py-3 text-[0.88rem] font-medium"
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        color: c.color,
      }}
    >
      {c.text(count)}
    </div>
  );
}
