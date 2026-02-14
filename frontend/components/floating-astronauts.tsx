export function FloatingAstronauts() {
  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden"
      style={{ zIndex: 2 }}
    >
      {astronauts.map((a, i) => (
        <img
          key={i}
          src="/astro.png"
          alt=""
          aria-hidden="true"
          className={`absolute astronaut-corner-${a.corner}`}
          style={{
            top: a.top,
            left: a.left,
            width: `${a.size}px`,
            height: "auto",
            opacity: a.opacity,
            rotate: `${a.rotate}deg`,
            scale: a.flip ? "-1 1" : undefined,
          }}
        />
      ))}
    </div>
  );
}

const astronauts = [
  { top: "4%",  left: "8%",  size: 60, opacity: 0.25, rotate: -20, corner: "tl", flip: false },
  { top: "12%", left: "78%", size: 55, opacity: 0.22, rotate: 25,  corner: "tr", flip: true  },
  { top: "58%", left: "3%",  size: 50, opacity: 0.2,  rotate: 40,  corner: "bl", flip: false },
  { top: "68%", left: "85%", size: 55, opacity: 0.22, rotate: -30, corner: "br", flip: true  },
];
