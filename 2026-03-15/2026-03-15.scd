var score, durs, silentPath;

silentPath = "/tmp/pm_silent.wav";
score = Score.new;

score.add([0.0, ["/d_recv", SynthDef(\pm_nullvoid, {
    |out=0, amp=0.3, freq=48.0, pos=0.0|
    var env, sub, body;
    env = EnvGen.kr(Env([0,1,0.6,0], [1.5, 22.0, 6.5], [-2, 0, -4]), doneAction: 2);
    sub = SinOsc.ar(freq * [1.0, 1.001]) * 0.5;
    body = LFNoise2.ar(0.3).range(0.0, 1.0) * PinkNoise.ar(0.15!2);
    body = BLowPass4.ar(body, freq * 3.2, 0.4);
    Out.ar(out, (sub * 0.6 + body * 0.4) * env * amp);
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_blade_ping, {
    |out=0, amp=0.18, freq=880.0, decay=4.2|
    var env, sig;
    env = EnvGen.kr(Env.perc(0.001, decay, 1.0, -6.0), doneAction: 2);
    sig = SinOsc.ar(freq) + (SinOsc.ar(freq * 2.73) * 0.3) + (SinOsc.ar(freq * 4.1) * 0.1);
    sig = sig * env * amp;
    sig = Pan2.ar(sig, LFNoise1.kr(0.05).range(-0.6, 0.6));
    Out.ar(out, sig);
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_verdict_pulse, {
    |out=0, amp=0.22, rate=0.18, freq=60.0|
    var env, trig, pulse, noise;
    env = EnvGen.kr(Env([0,1,1,0], [2.0, 20.0, 8.0], [-1, 0, -3]), doneAction: 2);
    trig = Impulse.ar(rate);
    pulse = Decay.ar(trig, 0.12) * SinOsc.ar(freq);
    noise = BPF.ar(PinkNoise.ar(1.0!2), 320.0, 0.3) * 0.3;
    pulse = (pulse + noise) * env * amp;
    Out.ar(out, Pan2.ar(pulse, 0.0));
}).asBytes]]);

score.add([0.0, ["/d_recv", SynthDef(\pm_scan_hum, {
    |out=0, amp=0.09, freq=180.0|
    var env, hum, mod;
    env = EnvGen.kr(Env([0,0.8,0.8,0], [3.0, 22.0, 5.0], [1, 0, -2]), doneAction: 2);
    mod = SinOsc.kr(0.07, 0.0, 8.0, freq);
    hum = SinOsc.ar(mod!2) * 0.5 + LFNoise1.ar(0.5!2).range(-1.0, 1.0) * 0.15;
    hum = BLowPass.ar(hum, 900.0, 0.6);
    Out.ar(out, hum * env * amp);
}).asBytes]]);

score.add([0.5, ["/s_new", "pm_nullvoid", 1000, 0, 0, "amp", 0.28, "freq", 46.0]]);
score.add([0.5, ["/s_new", "pm_verdict_pulse", 1001, 0, 0, "amp", 0.20, "rate", 0.18, "freq", 58.0]]);
score.add([1.5, ["/s_new", "pm_scan_hum", 1002, 0, 0, "amp", 0.08, "freq", 172.0]]);

score.add([4.0, ["/s_new", "pm_blade_ping", 1010, 0, 0, "amp", 0.16, "freq", 740.0, "decay", 5.0]]);
score.add([8.5, ["/s_new", "pm_blade_ping", 1011, 0, 0, "amp", 0.13, "freq", 1108.0, "decay", 3.8]]);
score.add([12.0, ["/s_new", "pm_blade_ping", 1012, 0, 0, "amp", 0.18, "freq", 520.0, "decay", 6.2]]);

score.add([5.5, ["/s_new", "pm_nullvoid", 1003, 0, 0, "amp", 0.18, "freq", 72.0]]);

score.add([16.5, ["/s_new", "pm_blade_ping", 1013, 0, 0, "amp", 0.12, "freq", 1480.0, "decay", 4.5]]);
score.add([18.0, ["/s_new", "pm_verdict_pulse", 1004, 0, 0, "amp", 0.15, "rate", 0.36, "freq", 62.0]]);
score.add([22.0, ["/s_new", "pm_blade_ping", 1014, 0, 0, "amp", 0.14, "freq", 880.0, "decay", 3.2]]);
score.add([24.5, ["/s_new", "pm_blade_ping", 1015, 0, 0, "amp", 0.10, "freq", 660.0, "decay", 5.5]]);
score.add([27.0, ["/s_new", "pm_blade_ping", 1016, 0, 0, "amp", 0.09, "freq", 1320.0, "decay", 3.5]]);

score.add([30.5, [0]]);

score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);
0.exit;
