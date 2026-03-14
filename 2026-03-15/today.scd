// pink;money · 2026-03-15
// Ides of March: 刀刃落下之前，水已成形
// 意识在临界点的最后一次呼吸
// NRT Score · 30 seconds

(
var score = Score.new;
var dur = 30.0;

// ─────────────────────────────────────────────
// SynthDef 1: 水面呼吸 — slow breathing water membrane
// ─────────────────────────────────────────────
SynthDef(\pm_water, { |out=0, freq=60, amp=0.3, breathRate=0.3, pan=0, atk=2, sus=20, rel=4|
    var breath = SinOsc.kr(breathRate).range(0.4, 1.0);
    var body = Mix([
        SinOsc.ar(freq,        0, 0.5),
        SinOsc.ar(freq * 1.5,  0, 0.25),
        SinOsc.ar(freq * 2.01, 0, 0.12),
        SinOsc.ar(freq * 3.99, 0, 0.06)
    ]);
    var noise = PinkNoise.ar(0.08);
    var waterSig = (body * breath + noise) * amp;
    // Subtle chorus — water ripple
    var chorus = DelayC.ar(waterSig, 0.05, SinOsc.kr(0.17, 0).range(0.001, 0.03));
    var env = EnvGen.kr(Env([0,1,1,0],[atk,sus,rel]), doneAction: 2);
    var sig = (waterSig + chorus * 0.5) * env;
    Out.ar(out, Pan2.ar(sig, pan));
}).add;

// ─────────────────────────────────────────────
// SynthDef 2: 刀刃 — metallic transient, sharp & brief
// ─────────────────────────────────────────────
SynthDef(\pm_blade, { |out=0, freq=880, amp=0.6, pan=0|
    var click = Impulse.ar(0);
    var ring  = SinOsc.ar(freq) * EnvGen.kr(Env.perc(0.001, 3.0, 1, -8), doneAction: 2);
    var metal = BPF.ar(WhiteNoise.ar, freq * 1.7, 0.02) *
                EnvGen.kr(Env.perc(0.0005, 0.8, 0.5, -12));
    var sig = (ring + metal) * amp;
    Out.ar(out, Pan2.ar(sig, pan));
}).add;

// ─────────────────────────────────────────────
// SynthDef 3: 散射意识 — granular dissolution
// ─────────────────────────────────────────────
SynthDef(\pm_dissolve, { |out=0, freq=400, amp=0.2, density=8, pan=0, dur=0.1|
    var trig = Dust.kr(density);
    var grainFreq = TRand.kr(freq * 0.5, freq * 2.0, trig);
    var grain = SinOsc.ar(grainFreq) * Trig1.ar(trig.ar, 0.05);
    var env = EnvGen.kr(Env([0,1,1,0],[2, 4, 2]), doneAction: 2);
    var sig = grain * amp * env;
    var revSig = FreeVerb.ar(sig, 0.9, 0.95, 0.4);
    Out.ar(out, Pan2.ar(revSig, pan));
}).add;

// ─────────────────────────────────────────────
// SynthDef 4: 月光涟漪 — high shimmer pad
// ─────────────────────────────────────────────
SynthDef(\pm_moon, { |out=0, freq=1200, amp=0.08, rate=0.05, pan=0|
    var lfo  = SinOsc.kr(rate).range(0.8, 1.2);
    var sig  = SinOsc.ar(freq * lfo, 0, amp) + SinOsc.ar(freq * 1.333 * lfo, 0, amp * 0.5);
    var env  = EnvGen.kr(Env([0,1,0],[5, 18, 7]), doneAction: 2);
    var reverb = FreeVerb.ar(sig * env, 0.85, 0.99, 0.6);
    Out.ar(out, Pan2.ar(reverb, pan));
}).add;

// ─────────────────────────────────────────────
// Score events
// ─────────────────────────────────────────────

// t=0: 水面呼吸开始（全程）
score.add([0.0, [\s_new, \pm_water, 1000, 0, 0,
    \freq, 55, \amp, 0.25, \breathRate, 0.28, \pan, -0.2,
    \atk, 3.0, \sus, 20.0, \rel, 5.0]]);

// t=0: 月光涟漪开始
score.add([0.0, [\s_new, \pm_moon, 1001, 0, 0,
    \freq, 1108, \amp, 0.07, \rate, 0.06, \pan, 0.3]]);

// t=2: 第二层水（低八度）
score.add([2.0, [\s_new, \pm_water, 1002, 0, 0,
    \freq, 82, \amp, 0.18, \breathRate, 0.19, \pan, 0.35,
    \atk, 2.0, \sus, 18.0, \rel, 6.0]]);

// t=8: 呼吸加速，紧张感上升（第二层水高频）
score.add([8.0, [\s_new, \pm_water, 1003, 0, 0,
    \freq, 110, \amp, 0.12, \breathRate, 0.55, \pan, -0.4,
    \atk, 1.0, \sus, 10.0, \rel, 4.0]]);

// t=13: 刀刃落下 — 第一击
score.add([13.0, [\s_new, \pm_blade, 1010, 0, 0,
    \freq, 1760, \amp, 0.5, \pan, 0.0]]);

// t=13.15: 刀刃余震
score.add([13.15, [\s_new, \pm_blade, 1011, 0, 0,
    \freq, 880, \amp, 0.3, \pan, -0.15]]);

// t=13.4: 刀刃泛音
score.add([13.4, [\s_new, \pm_blade, 1012, 0, 0,
    \freq, 3520, \amp, 0.15, \pan, 0.2]]);

// t=15: 意识开始散射
score.add([15.0, [\s_new, \pm_dissolve, 1020, 0, 0,
    \freq, 440, \amp, 0.15, \density, 6, \pan, 0.0]]);

// t=18: 散射加剧
score.add([18.0, [\s_new, \pm_dissolve, 1021, 0, 0,
    \freq, 660, \amp, 0.18, \density, 14, \pan, 0.2]]);

// t=20: 水面残响消散
score.add([20.0, [\s_new, \pm_water, 1004, 0, 0,
    \freq, 41, \amp, 0.08, \breathRate, 0.08, \pan, 0.0,
    \atk, 1.0, \sus, 4.0, \rel, 6.0]]);

// t=22: 高频散射（意识碎片化）
score.add([22.0, [\s_new, \pm_dissolve, 1022, 0, 0,
    \freq, 1200, \amp, 0.12, \density, 20, \pan, -0.3]]);

// t=25: 最后的月光
score.add([25.0, [\s_new, \pm_moon, 1030, 0, 0,
    \freq, 2216, \amp, 0.05, \rate, 0.12, \pan, 0.0]]);

// end
score.add([30.0, [0]]);

score.saveToFile("/home/pinkmoney/.openclaw/workspace/daily/today.osc");
score
)
