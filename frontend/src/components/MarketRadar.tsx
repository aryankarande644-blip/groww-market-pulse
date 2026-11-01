import { useMemo, useState } from "react";
import type { MarketStateItem } from "../types";
import { SEVERITY_STYLES, severityRadius } from "../lib/format";

interface MarketRadarProps {
  items: MarketStateItem[];
  onSelect: (symbol: string) => void;
  selectedSymbol?: string | null;
}

interface PlacedNode extends MarketStateItem {
  x: number;
  y: number;
  r: number;
}

const VIEW_SIZE = 560;
const CENTER = VIEW_SIZE / 2;

/** A stable hash so node placement is deterministic across re-renders (no
 * jitter/reshuffling every time the query refetches) while still looking
 * organically scattered rather than arranged in a perfect circle. */
function hash(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h << 5) - h + str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function placeNodes(items: MarketStateItem[]): PlacedNode[] {
  const count = items.length || 1;
  return items.map((item, index) => {
    const angleJitter = ((hash(item.symbol) % 1000) / 1000) * 0.5 - 0.25;
    const angle = (index / count) * Math.PI * 2 + angleJitter;

    // Higher attention is pulled closer to the center of the field -- the
    // radar's core metaphor: attention has gravity.
    const pullIn = (item.attention_score / 100) * 130;
    const baseOrbit = 190;
    const orbit = baseOrbit - pullIn + ((hash(item.symbol + "r") % 100) / 100) * 20;

    const x = CENTER + Math.cos(angle) * orbit;
    const y = CENTER + Math.sin(angle) * orbit;
    const r = severityRadius(item.attention_score);
    return { ...item, x, y, r };
  });
}

export function MarketRadar({ items, onSelect, selectedSymbol }: MarketRadarProps) {
  const nodes = useMemo(() => placeNodes(items), [items]);
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="relative w-full aspect-square max-w-[560px] mx-auto select-none">
      <svg viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} className="w-full h-full overflow-visible">
        {/* Concentric attention-field guides */}
        {[70, 120, 170, 220].map((r) => (
          <circle key={r} cx={CENTER} cy={CENTER} r={r} fill="none" stroke="#E7E5DF" strokeWidth={1} />
        ))}
        <circle cx={CENTER} cy={CENTER} r={3} fill="#0B0E14" />
        <text x={CENTER} y={CENTER - 12} textAnchor="middle" className="fill-gray-400 text-[10px] font-mono uppercase tracking-wider">
          your attention
        </text>

        {nodes.map((node) => {
          const style = SEVERITY_STYLES[node.severity];
          const isHovered = hovered === node.symbol;
          const isSelected = selectedSymbol === node.symbol;
          const isHot = node.severity === "HIGH" || node.severity === "CRITICAL";
          const dotColor =
            node.severity === "CRITICAL" ? "#B3261E" :
            node.severity === "HIGH" ? "#D96E2C" :
            node.severity === "MODERATE" ? "#D9A441" :
            node.severity === "LOW" ? "#8AA6C2" : "#9CA3AF";

          return (
            <g
              key={node.symbol}
              transform={`translate(${node.x}, ${node.y})`}
              onClick={() => onSelect(node.symbol)}
              onMouseEnter={() => setHovered(node.symbol)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-pointer"
            >
              {isHot && (
                <circle r={node.r} fill={dotColor} opacity={0.35} className="animate-pulseRing" />
              )}
              <circle
                r={node.r}
                fill={dotColor}
                opacity={isHot ? 0.16 : 0.10}
                stroke={dotColor}
                strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.25}
              />
              <circle r={4} fill={dotColor} />
              <text
                y={node.r + 16}
                textAnchor="middle"
                className={`font-mono text-[11px] ${isHot ? "font-semibold" : "font-normal"}`}
                fill={isHot ? "#0B0E14" : "#6B7280"}
              >
                {node.symbol}
              </text>
              {(isHovered || isSelected) && (
                <text y={node.r + 30} textAnchor="middle" className="font-mono text-[10px]" fill={dotColor}>
                  {Math.round(node.attention_score)}/100
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="flex items-center justify-center gap-4 mt-3 flex-wrap">
        {(["CRITICAL", "HIGH", "MODERATE", "LOW", "NORMAL"] as const).map((sev) => (
          <div key={sev} className="flex items-center gap-1.5 text-xs text-muted">
            <span className={`inline-block w-2 h-2 rounded-full ${SEVERITY_STYLES[sev].dot}`} />
            {SEVERITY_STYLES[sev].label}
          </div>
        ))}
      </div>
    </div>
  );
}
