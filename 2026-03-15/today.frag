#version 330

uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

// --- Utilities ---
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
        mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
        u.y
    );
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 6; i++) {
        v += a * noise(p);
        p = p * 2.0 + vec2(1.7, 9.2);
        a *= 0.5;
    }
    return v;
}

// --- Water membrane at the threshold ---
// Ides of March: the blade about to fall, the water already formed
// Pisces season end: dissolution, the last breath before fire

void main() {
    vec2 uv = v_uv;
    // Center
    vec2 st = uv * 2.0 - 1.0;
    float aspect = 1.0; // assume square, renderer sets this
    
    float t = u_time;
    
    // --- Phase 1 (0-10s): Water breathing, slow pulse ---
    // --- Phase 2 (10-20s): The blade descends, ripples accelerate ---
    // --- Phase 3 (20-30s): Dissolution, consciousness scatters ---
    
    float phase = t / 30.0; // 0..1 over 30 seconds
    
    // Breathing frequency accelerates toward end
    float breathFreq = 0.4 + phase * 3.0;
    float breathAmp  = 0.08 + phase * 0.15;
    
    // FBM-based water surface
    vec2 waterUV = uv * 3.5 + vec2(t * 0.07, t * 0.04);
    float water = fbm(waterUV + fbm(waterUV + fbm(waterUV)));
    
    // Ripple from center — the point of contact
    float dist = length(st);
    float rippleSpeed = 1.2 + phase * 4.0;
    float ripple = sin(dist * 18.0 - t * rippleSpeed) * exp(-dist * 2.5);
    ripple *= (0.3 + phase * 0.7); // intensifies
    
    // Blade slit: a vertical cut that appears at t=12
    float bladeTime = smoothstep(12.0, 16.0, t);
    float bladeSlit  = exp(-abs(st.x) * 80.0 * (1.0 - bladeTime * 0.9)) * bladeTime;
    float bladeGlow  = exp(-abs(st.x) * 12.0) * bladeTime;
    
    // Dissolution: particles scatter
    float scatter = 0.0;
    for (int i = 0; i < 8; i++) {
        float fi = float(i);
        vec2 seed = vec2(fi * 0.731, fi * 0.419);
        float angle = hash(seed) * 6.2832 + t * (0.3 + hash(seed + 1.0) * 0.5);
        float radius = hash(seed + 2.0) * 0.6 * phase;
        vec2 pos = vec2(cos(angle), sin(angle)) * radius;
        float d = length(st - pos);
        scatter += exp(-d * 30.0) * smoothstep(18.0, 30.0, t) * hash(seed + 3.0);
    }
    
    // --- Color palette ---
    // Deep indigo-water → pink-magenta blood → white dissolution
    
    // Base water color: deep teal-indigo
    vec3 waterDeep   = vec3(0.04, 0.06, 0.18);
    vec3 waterShallow = vec3(0.12, 0.22, 0.45);
    vec3 waterColor  = mix(waterDeep, waterShallow, water + ripple * 0.3);
    
    // Surface shimmer — moonlight (waning gibbous)
    float shimmer = pow(water, 2.0) * 0.6 + ripple * 0.4;
    waterColor += vec3(0.6, 0.7, 1.0) * shimmer * 0.25;
    
    // Pink/magenta blade glow — Ides blood
    vec3 bladeColor = vec3(1.0, 0.15, 0.45);
    waterColor += bladeColor * bladeSlit * 1.5;
    waterColor += bladeColor * bladeGlow * 0.4;
    
    // White scatter — consciousness dispersing
    waterColor += vec3(1.0, 0.85, 0.95) * scatter * 2.0;
    
    // Breathing vignette
    float vignette = 1.0 - smoothstep(0.4, 1.2, dist);
    float breathPulse = 1.0 + sin(t * breathFreq * 3.14159) * breathAmp;
    vignette = pow(vignette * breathPulse, 1.4);
    waterColor *= vignette;
    
    // Subtle pink tint as dissolution completes
    float pinkDrift = smoothstep(22.0, 30.0, t);
    waterColor = mix(waterColor, vec3(0.9, 0.3, 0.6) * waterColor, pinkDrift * 0.5);
    
    // HDR-ish tone mapping
    waterColor = waterColor / (waterColor + 0.8);
    waterColor = pow(waterColor, vec3(0.85)); // gamma
    
    fragColor = vec4(waterColor, 1.0);
}
