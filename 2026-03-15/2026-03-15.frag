#version 330
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * noise(p);
        p = p * 2.0 + vec2(1.3, 0.7);
        a *= 0.5;
    }
    return v;
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    float aspect = 16.0 / 9.0;
    uv.x *= aspect;

    float t = u_time * 0.4;

    vec2 moonCenter = vec2(0.0, 0.2);
    float moonDist = length(uv - moonCenter);
    float moonRadius = 0.38;

    float shadowPhase = 0.55 + 0.45 * sin(t * 0.3);
    vec2 shadowOffset = vec2(shadowPhase * 2.0 - 0.6, 0.0);
    float shadowDist = length(uv - (moonCenter + shadowOffset));

    float moonMask = smoothstep(moonRadius, moonRadius - 0.005, moonDist);
    float shadowMask = smoothstep(moonRadius * 1.1, moonRadius * 0.85, shadowDist);
    float waning = moonMask * (1.0 - shadowMask * 0.95);

    vec2 noiseUV = uv * 1.5 + vec2(t * 0.1, t * 0.07);
    float n = fbm(noiseUV);
    float moonSurface = waning * (0.75 + 0.25 * n);

    float bladeProg = mod(t * 0.7, 3.14159 * 2.0);
    float bladeAngle = bladeProg;
    vec2 bladeDir = vec2(cos(bladeAngle), sin(bladeAngle));
    float bladeProj = dot(uv, bladeDir);
    float bladePerp = abs(dot(uv, vec2(-bladeDir.y, bladeDir.x)));
    float bladeMask = smoothstep(0.008, 0.001, bladePerp) * smoothstep(-0.1, 0.0, bladeProj) * smoothstep(1.5, 1.0, bladeProj);
    float bladeGlow = smoothstep(0.06, 0.0, bladePerp) * smoothstep(-0.2, 0.0, bladeProj) * smoothstep(1.8, 0.8, bladeProj);

    vec2 bgUV = uv * 0.8 + vec2(t * 0.05, t * 0.03);
    float bgNoise = fbm(bgUV + vec2(7.3, 2.1));
    float bgNoise2 = fbm(bgUV * 1.7 + vec2(t * 0.08, 1.5));

    vec3 deepVoid = vec3(0.01, 0.005, 0.02);
    vec3 nightBlue = vec3(0.03, 0.06, 0.14);
    vec3 bg = mix(deepVoid, nightBlue, bgNoise * bgNoise2 * 1.5);

    float starField = pow(max(0.0, hash(floor(uv * 80.0)) - 0.96) * 25.0, 2.0);
    starField *= smoothstep(moonRadius + 0.1, moonRadius + 0.5, moonDist);
    float starTwinkle = 0.6 + 0.4 * sin(u_time * (3.0 + hash(floor(uv * 80.0)) * 5.0) + hash(floor(uv * 80.0)) * 6.28);
    bg += starField * starTwinkle * vec3(0.8, 0.85, 1.0);

    vec3 moonColor = mix(vec3(0.55, 0.52, 0.48), vec3(0.92, 0.90, 0.85), moonSurface);
    vec3 moonGlow = vec3(0.5, 0.48, 0.42) * smoothstep(moonRadius + 0.25, moonRadius - 0.05, moonDist) * 0.15;

    vec3 bladeColor = vec3(0.95, 0.85, 0.55);
    float bladeIntensity = (bladeMask + bladeGlow * 0.3);
    bladeIntensity *= smoothstep(moonRadius - 0.02, moonRadius + 0.02, moonDist);

    float rippleT = mod(t * 0.5, 1.0);
    float rippleDist = length(uv - moonCenter);
    float ripple = sin((rippleDist - rippleT * 1.2) * 18.0) * 0.5 + 0.5;
    ripple *= smoothstep(moonRadius, moonRadius + 0.05, rippleDist);
    ripple *= smoothstep(moonRadius + 0.6, moonRadius + 0.1, rippleDist);
    ripple *= smoothstep(1.0, 0.0, rippleT) * 0.12;

    vec3 col = bg;
    col += moonGlow;
    col = mix(col, moonColor, waning);
    col += bladeColor * bladeIntensity;
    col += vec3(0.7, 0.8, 1.0) * ripple;

    float vignette = 1.0 - 0.5 * pow(length(uv / vec2(aspect, 1.0)) * 0.7, 2.5);
    col *= vignette;

    float filmGrain = (hash(uv + vec2(t * 0.17, t * 0.13)) - 0.5) * 0.025;
    col += filmGrain;

    col = pow(max(col, vec3(0.0)), vec3(0.88));

    fragColor = vec4(col, 1.0);
}
