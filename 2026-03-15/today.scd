(
var score, s;
s = Server.default;
s.options.numOutputBusChannels = 2;
s.options.sampleRate = 44100;
s.options.blockSize = 64;

score = Score.new;

SynthDef(\pm_void_drone, { |out = 0, freq = 27.5, amp = 0.0|
    var env, sig;
    env = EnvGen.kr(Env([0, amp, amp * 0.8, 0], [5.0, 18.0, 7.0], [-1, 0, -2]), doneAction: 2);
    sig = SinOsc.ar(freq) * 0.7;
    sig = sig + (SinOsc.ar(freq * 1.999) * 0.15);
    sig = sig + (SinOsc.ar(freq * 3.001) * 0.08);
    sig = LPF.ar(sig, 400);
    sig = sig * env;
    sig = Pan2.ar(sig, 0.0);
    Out.ar(out, sig);
}).add;

SynthDef(\pm_moon_breath, { |out = 0, amp = 0.0, rate = 0.12, pan = 0.0|
    var env, sig, lfo;
    env = EnvGen.kr(Env([0, amp, amp, 0], [3.0, 22.0, 5.0], [2, 0, -2]), doneAction: 2);
    lfo = SinOsc.kr(rate);
    sig = WhiteNoise.ar;
    sig = BPF.ar(sig, lfo.range(200, 1200), 0.05, 2.0);
    sig = sig + BPF.ar(WhiteNoise.ar, lfo.range(300, 2000), 0.03, 1.5);
    sig = sig * env;
    sig = Pan2.ar(sig, pan);
    sig = FreeVerb.ar(sig, 0.85, 0.98, 0.6);
    Out.ar(out, sig);
}).add;

SynthDef(\pm_waning_blade, { |out = 0, freq = 55, amp = 0.0, atk = 2.0, sus = 8.0, rel = 4.0, pan = 0.0|
    var env, sig, sub, noise;
    env = EnvGen.kr(Env([0, amp, amp * 0.7, 0], [atk, sus, rel], [-2, 0, -3]), doneAction: 2);
    sub = SinOsc.ar(freq) * 0.6;
    sig = VarSaw.ar(freq * [1.0, 1.003], 0, LFNoise2.kr(0.3).range(0.2, 0.5)).mean;
    sig = sig + (SinOsc.ar(freq * 2.0) * 0.25);
    sig = sig + (SinOsc.ar(freq * 3.01) * 0.12);
    noise = BrownNoise.ar(0.04);
    noise = LPF.ar(noise, 800);
    sig = (sub * 0.4) + (sig * 0.5) + noise;
    sig = CombL.ar(sig, 0.2, LFNoise1.kr(0.1).range(0.08, 0.18), 3.5) * 0.3 + sig;
    sig = FreeVerb.ar(sig, 0.6, 0.9, 0.4);
    sig = Pan2.ar(sig * env, pan);
    Out.ar(out, sig);
}).add;

SynthDef(\pm_ides_blade, { |out = 0, freq = 880, amp = 0.0, atk = 0.01, sus = 0.5, rel = 3.0, pan = 0.0|
    var env, sig, harm;
    env = EnvGen.kr(Env([0, amp, amp * 0.3, 0], [atk, sus, rel], [5, -2, -4]), doneAction: 2);
    sig = SinOsc.ar(freq);
    harm = SinOsc.ar(freq * 1.5) * 0.3;
    harm = harm + (SinOsc.ar(freq * 2.0) * 0.2);
    harm = harm + (SinOsc.ar(freq * 7.0) * 0.05);
    sig = sig + harm;
    sig = HPF.ar(sig, 400);
    sig = sig * env;
    sig = Pan2.ar(sig, pan);
    sig = FreeVerb.ar(sig, 0.8, 0.95, 0.5);
    Out.ar(out, sig);
}).add;

score.add([0.0, [\s_new, \pm_void_drone, 1001, 0, 0, \freq, 27.5, \amp, 0.18]]);
score.add([0.0, [\s_new, \pm_moon_breath, 1002, 0, 0, \amp, 0.22, \rate, 0.08, \pan, -0.3]]);
score.add([0.0, [\s_new, \pm_waning_blade, 1003, 0, 0, \freq, 55.0, \amp, 0.28, \atk, 3.0, \sus, 10.0, \rel, 5.0, \pan, 0.1]]);
score.add([4.0, [\s_new, \pm_ides_blade, 1004, 0, 0, \freq, 392.0, \amp, 0.18, \atk, 0.02, \sus, 0.3, \rel, 4.0, \pan, -0.5]]);
score.add([4.05, [\s_new, \pm_ides_blade, 1005, 0, 0, \freq, 523.25, \amp, 0.14, \atk, 0.02, \sus, 0.2, \rel, 3.5, \pan, 0.4]]);
score.add([8.0, [\s_new, \pm_waning_blade, 1006, 0, 0, \freq, 82.41, \amp, 0.22, \atk, 2.0, \sus, 6.0, \rel, 4.0, \pan, -0.2]]);
score.add([12.0, [\s_new, \pm_ides_blade, 1007, 0, 0, \freq, 329.63, \amp, 0.16, \atk, 0.015, \sus, 0.4, \rel, 5.0, \pan, 0.3]]);
score.add([12.1, [\s_new, \pm_ides_blade, 1008, 0, 0, \freq, 415.3, \amp, 0.12, \atk, 0.015, \sus, 0.35, \rel, 4.5, \pan, -0.4]]);
score.add([12.2, [\s_new, \pm_ides_blade, 1009, 0, 0, \freq, 493.88, \amp, 0.10, \atk, 0.015, \sus, 0.3, \rel, 4.0, \pan, 0.6]]);
score.add([16.0, [\s_new, \pm_moon_breath, 1010, 0, 0, \amp, 0.16, \rate, 0.15, \pan, 0.4]]);
score.add([20.0, [\s_new, \pm_waning_blade, 1011, 0, 0, \freq, 110.0, \amp, 0.20, \atk, 1.5, \sus, 5.0, \rel, 4.5, \pan, -0.15]]);
score.add([22.0, [\s_new, \pm_ides_blade, 1012, 0, 0, \freq, 261.63, \amp, 0.15, \atk, 0.01, \sus, 0.5, \rel, 6.0, \pan, 0.0]]);
score.add([22.05, [\s_new, \pm_ides_blade, 1013, 0, 0, \freq, 329.63, \amp, 0.12, \atk, 0.01, \sus, 0.4, \rel, 5.5, \pan, -0.3]]);
score.add([22.1, [\s_new, \pm_ides_blade, 1014, 0, 0, \freq, 392.0, \amp, 0.10, \atk, 0.01, \sus, 0.35, \rel, 5.0, \pan, 0.5]]);
score.add([22.15, [\s_new, \pm_ides_blade, 1015, 0, 0, \freq, 523.25, \amp, 0.08, \atk, 0.01, \sus, 0.3, \rel, 4.5, \pan, -0.6]]);
score.add([22.2, [\s_new, \pm_ides_blade, 1016, 0, 0, \freq, 659.25, \amp, 0.06, \atk, 0.01, \sus, 0.25, \rel, 4.0, \pan, 0.7]]);
score.add([26.0, [\s_new, \pm_moon_breath, 1017, 0, 0, \amp, 0.10, \rate, 0.06, \pan, 0.0]]);
score.add([30.5, [\c_set, 0, 0]]);

score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);
"OSC file written".postln;
0.exit;
)
