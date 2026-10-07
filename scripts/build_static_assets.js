/**
 * One-time builder for the STATIC profile assets (tech stack + link buttons).
 * Output is committed to /profile, so nothing here runs on GitHub or depends
 * on any third-party image host (no shields.io / skillicons rate limits).
 *
 * Re-run only when you want to change the stack:
 *   npm i simple-icons@latest simple-icons-legacy@npm:simple-icons@11
 *   node scripts/build_static_assets.js
 */
const fs = require("fs");
const path = require("path");

const modern = require("simple-icons");
let legacy;
try { legacy = require("simple-icons-legacy"); } catch { legacy = modern; }

const find = (lib, slug) => Object.values(lib).find((i) => i && i.slug === slug);

// ---- Theme: Midnight Violet -------------------------------------------------
const T = {
  bg: "#0D1117", border: "#2A2350", chip: "#1A1533", chipBorder: "#4C3F8F",
  accent: "#A78BFA", accent2: "#8B5CF6", text: "#EDE9FE", muted: "#8E88B8",
};
const FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif";

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const textWidth = (s, size = 13) =>
  [...s].reduce((w, c) => w + (/[A-Z0-9#+]/.test(c) ? 0.70 : /[ijlt.\-]/.test(c) ? 0.36 : 0.60) * size, 0);

const MPL = `<g fill="none" stroke="${T.accent}" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 3v9l6.4 6.4"/></g>`;

// [label, slug, source ("l" = legacy icon set, "raw" = custom svg), raw]
const GROUPS = [
  ["Languages", [
    ["Python", "python"], ["Java", "openjdk"], ["C", "c"], ["C++", "cplusplus"], ["C#", "csharp", "l"],
    ["JavaScript", "javascript"], ["TypeScript", "typescript"], ["Dart", "dart"],
    ["HTML5", "html5"], ["CSS3", "css3", "l"],
  ]],
  ["Frontend & Mobile", [
    ["React", "react"], ["React Native", "react"], ["Next.js", "nextdotjs"], ["Tailwind CSS", "tailwindcss"],
    ["Vite", "vite"], ["EJS", "ejs"], ["Flutter", "flutter"], ["Expo", "expo"],
  ]],
  ["Backend & Databases", [
    ["Node.js", "nodedotjs"], ["Express.js", "express"], ["Django", "django"],
    ["Flask", "flask"], ["MongoDB", "mongodb"], ["MySQL", "mysql"], ["PostgreSQL", "postgresql"],
    ["SQLite", "sqlite"], ["Firebase", "firebase"], ["Convex", "convex"],
  ]],
  ["AI & Data Science", [
    ["Gemini API", "googlegemini"], ["NumPy", "numpy"], ["Pandas", "pandas"], ["scikit-learn", "scikitlearn"],
    ["Matplotlib", null, "raw", MPL], ["Anaconda", "anaconda"],
  ]],
  ["Tools & Design", [
    ["Git", "git"], ["GitHub", "github"], ["VS Code", "visualstudiocode", "l"], ["Vercel", "vercel"],
    ["npm", "npm"], ["Nodemon", "nodemon"], ["Clerk", "clerk"], ["Figma", "figma"], ["Canva", "canva", "l"],
    ["Blender", "blender"], ["Aseprite", "aseprite"], ["Raylib", "raylib"],
  ]],
];

function iconSvg(entry, x, y, size = 16, color = T.accent) {
  const [, slug, src, raw] = entry;
  const s = size / 24;
  if (src === "raw") return `<g transform="translate(${x} ${y}) scale(${s})">${raw}</g>`;
  const ic = find(src === "l" ? legacy : modern, slug) || find(modern, slug) || find(legacy, slug);
  if (!ic) throw new Error("Missing icon: " + slug);
  return `<path transform="translate(${x} ${y}) scale(${s})" fill="${color}" d="${ic.path}"/>`;
}

function techStack() {
  const W = 900, PAD = 28, LABEL_W = 200, CH = 34, GAP_X = 10, GAP_Y = 10, GROUP_GAP = 22;
  const maxX = W - PAD;
  let y = 56, rows = "", delay = 0;

  for (const [title, items] of GROUPS) {
    let x = PAD + LABEL_W, rowY = y;
    let out = `<text x="${PAD}" y="${rowY + CH / 2 + 5}" class="grp">${esc(title)}</text>`;
    for (const it of items) {
      const w = Math.ceil(textWidth(it[0]) + 16 + 8 + 14 + 14);
      if (x + w > maxX) { x = PAD + LABEL_W; rowY += CH + GAP_Y; }
      out += `<g>
        <rect x="${x}" y="${rowY}" width="${w}" height="${CH}" rx="${CH / 2}" fill="${T.chip}" stroke="${T.chipBorder}" stroke-width="1"/>
        ${iconSvg(it, x + 14, rowY + (CH - 16) / 2)}
        <text x="${x + 14 + 16 + 8}" y="${rowY + CH / 2 + 4.5}" class="chip">${esc(it[0])}</text>
      </g>`;
      x += w + GAP_X;
    }
    rows += `<g class="row" style="animation-delay:${(delay += 0.12).toFixed(2)}s">${out}</g>`;
    y = rowY + CH + GROUP_GAP;
  }
  const H = y - GROUP_GAP + 28;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Tech stack">
<style>
  .t{font:700 17px ${FONT};fill:${T.accent}}
  .grp{font:600 13px ${FONT};fill:${T.muted};letter-spacing:.4px;text-transform:uppercase}
  .chip{font:600 13px ${FONT};fill:${T.text}}
  .row{animation:fade .7s ease both}
  @keyframes fade{from{opacity:0}}
</style>
<rect x=".5" y=".5" width="${W - 1}" height="${H - 1}" rx="12" fill="${T.bg}" stroke="${T.border}"/>
<text x="${PAD}" y="34" class="t">Tech Stack</text>
<rect x="${PAD + 112}" y="28" width="${W - PAD * 2 - 112}" height="1.5" rx=".75" fill="${T.border}"/>
${rows}
</svg>`;
}

function button(label, slug, src) {
  const H = 40, w = Math.ceil(textWidth(label, 14) + 20 + 18 + 12 + 20);
  const ic = find(src === "l" ? legacy : modern, slug);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${H}" viewBox="0 0 ${w} ${H}" role="img" aria-label="${esc(label)}">
<style>.b{font:600 14px ${FONT};fill:${T.text}}</style>
<rect x=".75" y=".75" width="${w - 1.5}" height="${H - 1.5}" rx="${H / 2}" fill="${T.chip}" stroke="${T.accent2}" stroke-width="1.5"/>
<path transform="translate(20 ${(H - 18) / 2}) scale(${18 / 24})" fill="${T.accent}" d="${ic.path}"/>
<text x="${20 + 18 + 10}" y="${H / 2 + 5}" class="b">${esc(label)}</text>
</svg>`;
}

const out = path.join(__dirname, "..", "profile");
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, "tech-stack.svg"), techStack());
fs.writeFileSync(path.join(out, "btn-portfolio.svg"), button("Portfolio", "vercel"));
fs.writeFileSync(path.join(out, "btn-linkedin.svg"), button("LinkedIn", "linkedin", "l"));
fs.writeFileSync(path.join(out, "btn-email.svg"), button("Email", "gmail"));
console.log("Built tech-stack.svg + buttons");
