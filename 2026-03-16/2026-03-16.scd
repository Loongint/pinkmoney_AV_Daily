var score = Score.new;
var duration = 30.5;

score.add([0.0, ["/d_recv", SynthDef(\pm_gravity_drone, {
    |out = 0, freq = 32.5, amp = 0.0, atk = 4.0, rel = 8.0, pan = 0.0|
    var env = EnvGen.kr(Env([0, amp, amp, 0], [atk, duration - atk - rel, rel]), doneAction: 2);
    var sig = Mix.ar([
        SinOsc.ar(freq, 0, 0.5),
        SinOsc.ar(freq * 2.0013, 0, 0.25),
        SinOsc.ar(freq * 3.002, 0, 0.12),
        SinOsc.ar(freq * 0.4998, 0, 0.18)
    ]);
    var tremolo = SinOsc.kr(0.07, 0) * 0.04 + 1.0;
    sig = sig * tremolo * env;
    sig = LPF.ar(sig, 280 + SinOsc.kr(0.03) * 40);
    Out.ar(out, Pan2.ar(sig, pan));
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_eclipse_tone, {
    |out = 0, freq = 195.0, amp = 0.0, atk = 3.0, rel = 5.0, pan = 0.0, gate = 1|
    var env = EnvGen.kr(Env.asr(atk, amp, rel), gate, doneAction: 2);
    var lfo1 = SinOsc.kr(0.11, 0) * 0.8 + 1.0;
    var lfo2 = LFNoise1.kr(0.3) * 0.5;
    var sig = Mix.ar([
        Klank.ar(`[[freq, freq * 1.502, freq * 2.004], nil, [2.5, 1.8, 1.2]], WhiteNoise.ar(0.006)),
        SinOsc.ar(freq + lfo2 * 0.4, 0, 0.3 * lfo1),
        SinOsc.ar(freq * 1.5 + lfo2 * 0.2, 0, 0.12)
    ]);
    sig = sig * env;
    sig = RLPF.ar(sig, 900 + SinOsc.kr(0.06) * 200, 0.4);
    Out.ar(out, Pan2.ar(sig, pan));
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_shadow_texture, {
    |out = 0, amp = 0.0, atk = 2.0, rel = 4.0|
    var env = EnvGen.kr(Env([0, amp, amp, 0], [atk, 10.0, rel]), doneAction: 2);
    var noise = BrownNoise.ar(1.0);
    var filtered = BPF.ar(noise, 80, 0.15) * 0.6
                 + BPF.ar(noise, 140, 0.2) * 0.4
                 + BPF.ar(noise, 55, 0.25) * 0.5;
    filtered = filtered * env;
    Out.ar(out, [filtered * 0.7, filtered * 0.8]);
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_archive_signal, {
    |out = 0, freq = 1240.0, amp = 0.0, dur = 0.08, pan = 0.0|
    var env = EnvGen.kr(Env([0, amp, 0], [0.003, dur]), doneAction: 2);
    var sig = SinOsc.ar(freq) * env;
    sig = sig + (SinOsc.ar(freq * 2.0) * env * 0.3);
    Out.ar(out, Pan2.ar(sig, pan));
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_corona_shimmer, {
    |out = 0, amp = 0.0, atk = 5.0, rel = 8.0|
    var env = EnvGen.kr(Env([0, amp, 0], [atk, rel]), doneAction: 2);
    var freqs = [880, 1108, 1320, 1760, 2200];
    var sig = Mix.ar(freqs.collect { |f|
        SinOsc.ar(f + LFNoise2.kr(0.15) * 3, 0,
            env * (0.06 + LFNoise1.kr(0.08) * 0.04))
    });
    sig = FreeVerb.ar(sig, 0.85, 0.95, 0.3);
    Out.ar(out, [sig, sig * 0.9]);
}).asBytes]]);

score.add([1.0, ["/s_new", "pm_gravity_drone", 1000, 0, 0,
    "freq", 32.5, "amp", 0.28, "atk", 5.0, "rel", 7.0, "pan", -0.2]]);

score.add([1.5, ["/s_new", "pm_gravity_drone", 1001, 0, 0,
    "freq", 48.75, "amp", 0.18, "atk", 6.0, "rel", 6.0, "pan", 0.3]]);

score.add([2.0, ["/s_new", "pm_shadow_texture", 1002, 0, 0,
    "amp", 0.12, "atk", 3.0, "rel", 5.0]]);

score.add([4.0, ["/s_new", "pm_eclipse_tone", 1003, 0, 0,
    "freq", 97.5, "amp", 0.22, "atk", 3.5, "rel", 5.0, "pan", 0.0]]);

score.add([7.0, ["/s_new", "pm_corona_shimmer", 1004, 0, 0,
    "amp", 0.15, "atk", 4.0, "rel", 8.0]]);

score.add([9.0, ["/s_new", "pm_eclipse_tone", 1005, 0, 0,
    "freq", 195.0, "amp", 0.14, "atk", 2.5, "rel", 4.5, "pan", -0.4]]);

score.add([11.5, ["/s_new", "pm_archive_signal", 1010, 0, 0,
    "freq", 1240.0, "amp", 0.18, "dur", 0.12, "pan", 0.5]]);

score.add([12.1, ["/s_new", "pm_archive_signal", 1011, 0, 0,
    "freq", 1860.0, "amp", 0.12, "dur", 0.08, "pan", -0.3]]);

score.add([12.9, ["/s_new", "pm_archive_signal", 1012, 0, 0,
    "freq", 2480.0, "amp", 0.08, "dur", 0.05, "pan", 0.1]]);

score.add([13.8, ["/s_new", "pm_archive_signal", 1013, 0, 0,
    "freq", 992.0, "amp", 0.10, "dur", 0.15, "pan", -0.6]]);

score.add([14.0, ["/s_new", "pm_eclipse_tone", 1006, 0, 0,
    "freq", 65.0, "amp", 0.32, "atk", 2.0, "rel", 6.0, "pan", 0.2]]);

score.add([16.5, ["/n_set", 1002, "gate", 0]]);

score.add([18.0, ["/s_new", "pm_corona_shimmer", 1007, 0, 0,
    "amp", 0.10, "atk", 3.0, "rel", 9.0]]);

score.add([19.0, ["/s_new", "pm_archive_signal", 1014, 0, 0,
    "freq", 880.0, "amp", 0.14, "dur", 0.3, "pan", 0.0]]);

score.add([20.5, ["/s_new", "pm_archive_signal", 1015, 0, 0,
    "freq", 440.0, "amp", 0.10, "dur", 0.4, "pan", -0.2]]);

score.add([22.0, ["/n_set", 1003, "gate", 0]]);
score.add([22.0, ["/n_set", 1005, "gate", 0]]);
score.add([22.0, ["/n_set", 1006, "gate", 0]]);

score.add([23.0, ["/s_new", "pm_gravity_drone", 1008, 0, 0,
    "freq", 24.375, "amp", 0.22, "atk", 2.0, "rel", 5.5, "pan", 0.0]]);

score.add([25.0, ["/s_new", "pm_eclipse_tone", 1009, 0, 0,
    "freq", 130.0, "amp", 0.08, "atk", 2.0, "rel", 4.0, "pan", 0.1, "gate", 1]]);

score.add([26.0, ["/n_set", 1000, "gate", 0]]);
score.add([26.0, ["/n_set", 1001, "gate", 0]]);
score.add([28.0, ["/n_set", 1004, "gate", 0]]);
score.add([28.0, ["/n_set", 1007, "gate", 0]]);
score.add([28.0, ["/n_set", 1008, "gate", 0]]);
score.add([29.0, ["/n_set", 1009, "gate", 0]]);

score.add([30.5, [0]]);

score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);
0.exit;
