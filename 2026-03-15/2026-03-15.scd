var score = Score.new;

score.add([0.0, ["/d_recv", SynthDef(\pm_ides_water, {
    arg out = 0, gate = 1, amp = 0.45;
    var sig, env, lfo, mod, reverb;
    lfo = SinOsc.kr(0.12, 0);
    mod = SinOsc.ar(0.7, 0, 8.0);
    sig = Mix.new([
        SinOsc.ar(55.0 + mod, 0, 0.2),
        SinOsc.ar(82.5 + mod * 0.5, 0, 0.12),
        SinOsc.ar(110.0, SinOsc.ar(0.31, 0, 0.5), 0.08),
        Saw.ar(27.5, 0.04) * LPF.ar(PinkNoise.ar(1.0), 400)
    ]);
    reverb = FreeVerb.ar(sig, 0.85, 0.92, 0.3);
    env = EnvGen.kr(Env.adsr(6.0, 3.0, 0.75, 8.0), gate, doneAction: 2);
    Out.ar(out, Pan2.ar(reverb * env * amp, lfo * 0.4));
}).asBytes]]);

score.add([0.0, ["/s_new", \pm_ides_water, 1001, 0, 0, "amp", 0.5]]);

score.add([0.5, ["/d_recv", SynthDef(\pm_ides_ripple, {
    arg out = 0, gate = 1, amp = 0.3;
    var trig, env, sig, freq;
    trig = Impulse.kr(LFNoise1.kr(0.3, 0.6, 1.1));
    freq = TRand.kr(180, 520, trig);
    env = EnvGen.kr(Env.perc(0.005, 1.8, 1.0, -4.0), trig);
    sig = SinOsc.ar(freq * (1.0 + env * 0.15), 0, env * 0.5);
    sig = sig + SinOsc.ar(freq * 2.01, 0, env * 0.2);
    sig = FreeVerb.ar(sig, 0.7, 0.88, 0.25);
    Out.ar(out, Pan2.ar(sig * amp, LFNoise1.kr(0.5)));
}).asBytes]]);

score.add([0.5, ["/s_new", \pm_ides_ripple, 1002, 0, 0, "amp", 0.35]]);

score.add([8.0, ["/d_recv", SynthDef(\pm_ides_crack, {
    arg out = 0, gate = 1, amp = 0.22;
    var sig, env, burst, metal;
    env = EnvGen.kr(Env.adsr(10.0, 2.0, 0.6, 6.0), gate, doneAction: 2);
    metal = Mix.new([
        Klank.ar(`[[440, 661, 1100, 1760], nil, [2.0, 1.5, 1.0, 0.5]], Impulse.ar(0.18, 0, 0.3)),
        Klank.ar(`[[330, 550, 880], nil, [1.8, 1.2, 0.8]], Impulse.ar(0.23, 0.3, 0.25))
    ]);
    sig = HPF.ar(metal, 200);
    sig = FreeVerb.ar(sig, 0.6, 0.7, 0.4);
    Out.ar(out, Pan2.ar(sig * env * amp, SinOsc.kr(0.09, 0, 0.7)));
}).asBytes]]);

score.add([8.0, ["/s_new", \pm_ides_crack, 1003, 0, 0, "amp", 0.28]]);

score.add([20.0, ["/d_recv", SynthDef(\pm_ides_ignite, {
    arg out = 0, gate = 1, amp = 0.35;
    var sig, env, carrier, mod;
    env = EnvGen.kr(Env.adsr(4.0, 2.0, 0.8, 4.0), gate, doneAction: 2);
    mod = SinOsc.ar(87.5, 0, 220.0);
    carrier = SinOsc.ar(220.0 + mod, 0, 0.4);
    carrier = carrier + SinOsc.ar(440.0 + mod * 0.5, 0, 0.2);
    carrier = carrier + SinOsc.ar(880.0 + mod * 0.25, 0, 0.1);
    sig = carrier * env;
    sig = FreeVerb.ar(sig, 0.75, 0.85, 0.35);
    Out.ar(out, Pan2.ar(sig * amp, SinOsc.kr(0.15, 0, 0.5)));
}).asBytes]]);

score.add([20.0, ["/s_new", \pm_ides_ignite, 1004, 0, 0, "amp", 0.4]]);

score.add([24.0, ["/n_set", 1001, "gate", 0]]);
score.add([24.0, ["/n_set", 1002, "gate", 0]]);
score.add([26.0, ["/n_set", 1003, "gate", 0]]);
score.add([27.0, ["/n_set", 1004, "gate", 0]]);

score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);

0.exit;
