#version 330
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noise(p);
        p = p * 2.1 + vec2(1.7, 9.2);
        a *= 0.5;
    }
    return v;
}

float crack(vec2 uv, float t) {
    float phase = smoothstep(8.0, 22.0, t);
    float n = fbm(uv * 3.0 + t * 0.08);
    float line = abs(uv.x + (n - 0.5) * 1.2 * phase);
    return smoothstep(0.012, 0.0, line) * phase;
}

vec3 waterField(vec2 uv, float t) {
    float slow = t * 0.4;
    float n1 = fbm(uv * 2.0 + vec2(slow * 0.3, slow * 0.2));
    float n2 = fbm(uv * 4.0 - vec2(slow * 0.15, slow * 0.35) + n1 * 0.5);
    float wave = sin(uv.x * 6.0 + n1 * 4.0 + t * 0.7) * 0.5 + 0.5;
    wave *= sin(uv.y * 5.0 + n2 * 3.0 + t * 0.5) * 0.5 + 0.5;
    float r = 0.05 + n2 * 0.18 + wave * 0.07;
    float g = 0.06 + n1 * 0.12 + wave * 0.05;
    float b = 0.18 + n2 * 0.35 + wave * 0.18;
    return vec3(r, g, b);
}

vec3 roseLiturgy(vec2 uv, float t) {
    float phase = smoothstep(18.0, 28.0, t);
    float burst = exp(-length(uv) * (2.5 - phase * 1.5));
    float rose_r = 0.72 * burst * phase;
    float rose_g = 0.18 * burst * phase;
    float rose_b = 0.42 * burst * phase;
    return vec3(rose_r, rose_g, rose_b);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= 1920.0 / 1080.0;

    float t = u_time;

    float ignition = smoothstep(26.0, 30.0, t);
    float breath = sin(t * 0.8) * 0.5 + 0.5;

    vec3 water = waterField(uv, t);

    float cr = crack(uv, t);
    float cr2 = crack(vec2(-uv.y * 0.7 + 0.3, uv.x * 0.9 - 0.2), t * 0.9);
    float cr3 = crack(uv * 1.4 + vec2(0.5, -0.3), t * 1.1);
    vec3 crackLight = vec3(0.9, 0.85, 0.6) * (cr + cr2 * 0.6 + cr3 * 0.4);

    vec3 liturgy = roseLiturgy(uv, t);

    float ripple = sin(length(uv) * 12.0 - t * 2.5) * 0.5 + 0.5;
    ripple *= exp(-length(uv) * 1.2);
    vec3 rippleCol = vec3(0.1, 0.3, 0.6) * ripple * (1.0 - smoothstep(12.0, 20.0, t) * 0.7);

    vec3 col = water + rippleCol + crackLight + liturgy;

    float igniteFlare = smoothstep(28.0, 30.0, t) * exp(-length(uv) * 1.8);
    col += vec3(1.0, 0.6, 0.2) * igniteFlare * 2.5;

    float vignette = 1.0 - smoothstep(0.5, 1.5, length(uv));
    col *= vignette;

    float fog = fbm(uv * 1.5 + t * 0.05) * 0.15 * (1.0 - ignition);
    col += fog;

    col = pow(clamp(col, 0.0, 1.0), vec3(0.85));

    fragColor = vec4(col, 1.0);
}
