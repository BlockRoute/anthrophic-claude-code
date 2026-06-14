import React, { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, {
  Circle,
  Defs,
  Ellipse,
  G,
  Path,
  RadialGradient,
  Stop,
} from 'react-native-svg';
import { palette } from '../lib/theme';
import type { PlantState } from '../lib/plant';

const AG = Animated.createAnimatedComponent(G);

/** Interpolate between the lush green and a dry rust as vitality drops. */
function leafColor(vitality: number) {
  const t = Math.max(0, Math.min(1, vitality));
  const lush = [91, 231, 168];
  const dry = [148, 120, 78];
  const c = lush.map((v, i) => Math.round(dry[i] + (v - dry[i]) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

interface LeafCluster {
  cx: number;
  cy: number;
  r: number;
}

/** Canopy clusters that appear progressively with stage index (0..5). */
const CLUSTERS: LeafCluster[][] = [
  [], // seed — handled separately
  [{ cx: 100, cy: 150, r: 14 }], // sprout
  [
    { cx: 100, cy: 118, r: 20 },
    { cx: 86, cy: 134, r: 14 },
    { cx: 116, cy: 134, r: 14 },
  ], // sapling
  [
    { cx: 100, cy: 96, r: 28 },
    { cx: 74, cy: 116, r: 20 },
    { cx: 126, cy: 116, r: 20 },
    { cx: 100, cy: 128, r: 18 },
  ], // young
  [
    { cx: 100, cy: 80, r: 34 },
    { cx: 66, cy: 104, r: 24 },
    { cx: 134, cy: 104, r: 24 },
    { cx: 82, cy: 122, r: 20 },
    { cx: 118, cy: 122, r: 20 },
  ], // flourishing
  [
    { cx: 100, cy: 70, r: 38 },
    { cx: 58, cy: 96, r: 28 },
    { cx: 142, cy: 96, r: 28 },
    { cx: 76, cy: 118, r: 24 },
    { cx: 124, cy: 118, r: 24 },
    { cx: 100, cy: 128, r: 22 },
  ], // ancient
];

/** Trunk path grows taller with the stage. */
function trunkPath(stageIndex: number): string {
  const topY = [176, 150, 132, 120, 110, 102][stageIndex];
  const spread = 3 + stageIndex * 0.8;
  return `M ${100 - spread} 196
          C ${100 - spread} 180, ${100 - spread - 1} ${topY + 14}, ${100 - spread / 2} ${topY}
          L ${100 + spread / 2} ${topY}
          C ${100 + spread + 1} ${topY + 14}, ${100 + spread} 180, ${100 + spread} 196 Z`;
}

export function Plant({ plant, size = 240 }: { plant: PlantState; size?: number }) {
  const sway = useSharedValue(0);
  const breathe = useSharedValue(1);

  useEffect(() => {
    const amp = plant.withering ? 0.4 : 1.6;
    sway.value = withRepeat(
      withSequence(
        withTiming(amp, { duration: 2600 }),
        withTiming(-amp, { duration: 2600 }),
      ),
      -1,
      true,
    );
    breathe.value = withRepeat(
      withSequence(
        withTiming(1.015, { duration: 2600 }),
        withTiming(0.985, { duration: 2600 }),
      ),
      -1,
      true,
    );
  }, [plant.withering, sway, breathe]);

  const canopyProps = useAnimatedProps(() => ({
    // rotate the canopy gently around the trunk top
    transform: [
      { translateX: 100 },
      { translateY: 120 },
      { rotateZ: `${sway.value}deg` },
      { scale: breathe.value },
      { translateX: -100 },
      { translateY: -120 },
    ] as any,
  }));

  const color = leafColor(plant.withering ? plant.vitality * 0.7 : Math.max(0.5, plant.vitality));
  const clusters = CLUSTERS[plant.stageIndex] ?? [];
  const isSeed = plant.stageIndex === 0;

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size} viewBox="0 0 200 210">
        <Defs>
          <RadialGradient id="soil" cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={palette.glowDeep} stopOpacity={0.9} />
            <Stop offset="100%" stopColor={palette.base} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="halo" cx="50%" cy="40%" r="60%">
            <Stop offset="0%" stopColor={palette.glow} stopOpacity={plant.withering ? 0.04 : 0.16} />
            <Stop offset="100%" stopColor={palette.glow} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="leaf" cx="38%" cy="32%" r="75%">
            <Stop offset="0%" stopColor={color} stopOpacity={1} />
            <Stop offset="100%" stopColor={color} stopOpacity={0.78} />
          </RadialGradient>
        </Defs>

        {/* Ambient glow */}
        <Circle cx={100} cy={110} r={96} fill="url(#halo)" />

        {/* Soil mound */}
        <Ellipse cx={100} cy={196} rx={62} ry={16} fill="url(#soil)" />
        <Path
          d="M 46 196 Q 100 178 154 196 Q 100 208 46 196 Z"
          fill={palette.surfaceRaised}
          opacity={0.9}
        />

        {isSeed ? (
          <>
            {/* a seed / first shoot */}
            <Path
              d={`M 100 196 L 100 ${196 - 18 * (0.4 + plant.stageProgress)}`}
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
            />
            <Ellipse cx={100} cy={196 - 18 * (0.4 + plant.stageProgress)} rx={7} ry={4}
              fill={color} transform={`rotate(-25 100 ${196 - 18 * (0.4 + plant.stageProgress)})`} />
            <Circle cx={100} cy={194} r={5} fill={palette.fat} opacity={0.7} />
          </>
        ) : (
          <>
            {/* Trunk */}
            <Path d={trunkPath(plant.stageIndex)} fill="#5A4A38" />
            <Path d={trunkPath(plant.stageIndex)} fill={palette.void} opacity={0.18} />

            {/* Canopy — animated as a group */}
            <AG animatedProps={canopyProps}>
              {clusters.map((c, i) => (
                <Circle key={i} cx={c.cx} cy={c.cy} r={c.r} fill="url(#leaf)" />
              ))}
              {/* a few fruit/blossoms once flourishing */}
              {plant.stageIndex >= 4 &&
                !plant.withering &&
                clusters.slice(0, 3).map((c, i) => (
                  <Circle key={`f${i}`} cx={c.cx + (i - 1) * 6} cy={c.cy + 4} r={2.6} fill={palette.gold} />
                ))}
            </AG>

            {/* withering: a couple of falling leaves */}
            {plant.withering && (
              <>
                <Ellipse cx={72} cy={170} rx={4} ry={2.4} fill={palette.wither} transform="rotate(40 72 170)" />
                <Ellipse cx={132} cy={182} rx={4} ry={2.4} fill={palette.wither} transform="rotate(-30 132 182)" />
              </>
            )}
          </>
        )}
      </Svg>
    </View>
  );
}
