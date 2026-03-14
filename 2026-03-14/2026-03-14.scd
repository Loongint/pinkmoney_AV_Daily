var score = Score.new;

score.add([0.0, ["/d_recv", SynthDef(\pm_pi_resonance, {
    arg out = 0, gate = 1, amp = 0.4;
    var freqs, sigs, env, lfo, noise, sub;
    lfo = SinOsc.kr(0.1, 0);
    freqs = [55.0, 55.0 * 3.14159, 55.0 * 3.14159 * 2, 440.0 * (3.14159 / 3.0)];
    sigs = freqs.collect({ |f, i|
        var phase_mod = SinOsc.ar(f * 0.5, 0, 0.3 + (i * 0.1));
        SinOsc.ar(f + phase_mod * f * 0.02, 0, 0.15 / (i + 1))
    });
    sub = SinOsc.ar(27.5, 0, 0.3) * (0.6 + lfo * 0.4);
    noise = PinkNoise.ar(0.03) * LFPulse.kr(3.14159 * 0.5, 0, 0.15);
    env = EnvGen.kr(Env.adsr(8.0, 4.0, 0.7, 6.0), gate, doneAction: 2);
    Out.ar(out, Pan2.ar(Mix.new(sigs) + sub + noise, SinOsc.kr(0.07, 0, 0.6)) * env * amp);
}).asBytes]]);

score.add([0.0, ["/s_new", \pm_pi_resonance, 1001, 0, 0, "amp", 0.5]]);

score.add([2.0, ["/d_recv", SynthDef(\pm_pi_texture, {
    arg out = 0, gate = 1, amp = 0.25;
    var sigs, env, mod, freqBase;
    freqBase = 220.0;
    mod = SinOsc.ar(freqBase * 0.00314, 0, freqBase * 0.3);
    sigs = [1.0, 1.618, 2.718, 3.14159, 4.0, 5.0].collect({ |ratio, i|
        var f = freqBase * ratio + mod;
        Saw.ar(f, 0.06 / (i + 1)) * SinOsc.kr(0.031415 * (i + 1), i * 0.5)
    });
    env = EnvGen.kr(Env.adsr(12.0, 3.0, 0.6, 8.0), gate, doneAction: 2);
    Out.ar(out, Pan2.ar(Mix.new(sigs) * env * amp, SinOsc.kr(0.05, 1.5, 0.5)));
}).asBytes]]);

score.add([2.0, ["/s_new", \pm_pi_texture, 1002, 0, 0, "amp", 0.3]]);

score.add([4.0, ["/d_recv", SynthDef(\pm_pi_pulse, {
    arg out = 0, gate = 1, amp = 0.2;
    var trig, freq, sig, env, decay_env;
    freq = 110.0 * 3.14159;
    trig = Impulse.kr(3.14159 * 0.3);
    decay_env = EnvGen.kr(Env.perc(0.01, 0.8), trig);
    sig = SinOsc.ar(freq * (1.0 + decay_env * 0.5), 0, decay_env);
    sig = sig + (SinOsc.ar(freq * 2.0, 0, decay_env * 0.4));
    env = EnvGen.kr(Env.adsr(4.0, 2.0, 0.8, 5.0), gate, doneAction: 2);
    Out.ar(out, Pan2.ar(sig * env * amp, LFNoise1.kr(0.2)));
}).asBytes]]);

score.add([4.0, ["/s_new", \pm_pi_pulse, 1003, 0, 0, "amp", 0.25]]);

score.add([24.0, ["/n_set", 1001, "gate", 0]]);
score.add([24.0, ["/n_set", 1002, "gate", 0]]);
score.add([24.0, ["/n_set", 1003, "gate", 0]]);

score.writeOSCFile("/tmp/pm_score.osc", 0, 30.5);
