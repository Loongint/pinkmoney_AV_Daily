#version 330
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

float sdLine(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

float sdCircle(vec2 p, float r) {
    return length(p) - r;
}

float sdArc(vec2 p, float r, float th0, float th1) {
    float a = atan(p.y, p.x);
    a = mod(a - th0, 6.28318) + th0;
    float clampedA = clamp(a, th0, th1);
    vec2 nearest = r * vec2(cos(clampedA), sin(clampedA));
    return length(p - nearest);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= 1.7778;

    float t = u_time;

    vec3 col = vec3(0.0);

    float voidPulse = 0.028 + 0.012 * sin(t * 0.3);
    float moonArc = sdArc(uv, 0.38, 3.1415 * 1.05, 3.1415 * 1.95);
    float moonGlow = smoothstep(0.005, 0.0, moonArc) * voidPulse * 6.0;
    col += vec3(0.7, 0.75, 0.9) * moonGlow;

    float rimDist = abs(sdCircle(uv, 0.38));
    float rimGlow = smoothstep(0.025, 0.0, rimDist) * 0.018;
    col += vec3(0.3, 0.32, 0.45) * rimGlow;

    float loopT = mod(t * 0.18, 1.0);
    float loopR = 0.62 + 0.04 * sin(t * 0.07);
    float loopAng0 = -1.5708;
    float loopAng1 = loopAng0 + loopT * 6.28318;
    float loopArc = sdArc(uv, loopR, loopAng0, min(loopAng1, loopAng0 + 6.2));
    float loopLine = smoothstep(0.004, 0.0, loopArc);
    float loopFade = smoothstep(0.0, 0.3, loopT) * smoothstep(1.0, 0.85, loopT);
    col += vec3(0.55, 0.18, 0.35) * loopLine * loopFade * 0.9;

    float closingT = clamp((mod(t * 0.18, 1.0) - 0.9) / 0.1, 0.0, 1.0);
    float closingFlash = exp(-closingT * 8.0) * closingT * 3.0;
    col += vec3(0.9, 0.5, 0.6) * closingFlash;

    int nBlades = 3;
    for (int i = 0; i < nBlades; i++) {
        float phase = 6.28318 * float(i) / float(nBlades);
        float bAng = phase + t * 0.04 + sin(t * 0.09 + phase) * 0.3;
        vec2 bDir = vec2(cos(bAng), sin(bAng));
        vec2 bOrigin = bDir * 0.52;
        vec2 bTip = bDir * 0.82;
        float bDist = sdLine(uv, bOrigin, bTip);
        float blade = smoothstep(0.003, 0.0, bDist);
        float bladePulse = 0.5 + 0.5 * sin(t * 1.2 + phase);
        col += vec3(0.6, 0.68, 0.8) * blade * bladePulse * 0.25;
    }

    float scanY = mod(uv.y + t * 0.08, 2.0) - 1.0;
    float scanLine = smoothstep(0.004, 0.0, abs(scanY)) * 0.04;
    col += vec3(0.4, 0.45, 0.6) * scanLine;

    float vignette = 1.0 - smoothstep(0.5, 1.3, length(uv * vec2(0.6, 0.9)));
    col *= vignette;

    float grain = fract(sin(dot(v_uv + t * 0.001, vec2(127.1, 311.7))) * 43758.5453);
    col += (grain - 0.5) * 0.012;

    float breathe = 0.92 + 0.08 * sin(t * 0.25);
    col *= breathe;

    col = pow(clamp(col, 0.0, 1.0), vec3(0.88));

    fragColor = vec4(col, 1.0);
}
